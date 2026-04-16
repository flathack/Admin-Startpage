from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests

from .connector_client import ConnectorClient
from .permission_service import PermissionService, UserSession


class IntegrationService:
    def __init__(
        self,
        config_path: Path,
        permission_service: PermissionService,
        connector_client: ConnectorClient,
        *,
        mock_enabled: bool | None = None,
    ) -> None:
        self._config_path = config_path
        self._permission_service = permission_service
        self._connector_client = connector_client
        self._config = json.loads(config_path.read_text(encoding="utf-8"))
        self._mock_enabled = (
            mock_enabled
            if mock_enabled is not None
            else os.getenv("STARTPAGE_ENABLE_MOCK_INTEGRATIONS", "true").lower() == "true"
        )

    def overview(self, user_session: UserSession, *, session_password: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for definition in self._config.get("systems", []):
            permission = str(definition.get("permission", "")).strip()
            if permission and not self._permission_service.has_permission(user_session.permissions, permission):
                continue
            item = self._fetch_system(definition, user_session, session_password=session_password, detail=False)
            items.append(item)
        return items

    def details(self, system_id: str, user_session: UserSession, *, session_password: str) -> dict[str, Any]:
        definition = self._find_system(system_id)
        permission = str(definition.get("permission", "")).strip()
        if permission and not self._permission_service.has_permission(user_session.permissions, permission):
            raise PermissionError(f"Keine Berechtigung fuer {system_id}.")
        return self._fetch_system(definition, user_session, session_password=session_password, detail=True)

    def _find_system(self, system_id: str) -> dict[str, Any]:
        for definition in self._config.get("systems", []):
            if str(definition.get("id", "")).strip() == system_id:
                return definition
        raise KeyError(system_id)

    def _fetch_system(
        self,
        definition: dict[str, Any],
        user_session: UserSession,
        *,
        session_password: str,
        detail: bool,
    ) -> dict[str, Any]:
        system_id = str(definition.get("id", "")).strip()
        title = str(definition.get("title", system_id)).strip() or system_id
        if system_id == "ad":
            return self._ad_response(definition, user_session, detail=detail)
        if system_id == "citrix":
            return self._citrix_response(
                definition,
                detail=detail,
                allow_mock=self._mock_enabled or bool(definition.get("mock", False)),
            )
        if self._mock_enabled or bool(definition.get("mock", False)):
            return self._mock_response(definition, detail=detail)

        try:
            if system_id == "nutanix":
                return self._nutanix_response(definition, user_session.identity.username, session_password, detail=detail)
            if system_id == "vsphere":
                return self._vsphere_response(definition, user_session.identity.username, session_password, detail=detail)
            if system_id == "endpoint":
                return self._endpoint_response(definition, user_session.identity.username, session_password, detail=detail)
        except Exception as exc:
            return {
                "id": system_id,
                "title": title,
                "status": "error",
                "source": "live",
                "message": str(exc),
                "items": [],
                "meta": {},
            }

        return {
            "id": system_id,
            "title": title,
            "status": "unknown",
            "source": "live",
            "message": "Kein Handler vorhanden.",
            "items": [],
            "meta": {},
        }

    def _mock_response(self, definition: dict[str, Any], *, detail: bool) -> dict[str, Any]:
        items = list(definition.get("mock_items", []))
        if not detail:
            items = items[:3]
        return {
            "id": str(definition.get("id", "")),
            "title": str(definition.get("title", "")),
            "status": str(definition.get("mock_status", "ok")),
            "source": "mock",
            "message": str(definition.get("mock_message", "Mock-Daten aktiv.")),
            "items": items,
            "meta": dict(definition.get("mock_meta", {})),
        }

    def _ad_response(self, definition: dict[str, Any], user_session: UserSession, *, detail: bool) -> dict[str, Any]:
        connector_payload = self._connector_client.ad_session_context(
            {
                "username": user_session.identity.username,
                "display_name": user_session.identity.display_name,
                "email": user_session.identity.email,
                "ad_groups": sorted(user_session.identity.ad_groups),
            }
        )
        items = [
            {"label": "Display Name", "value": user_session.identity.display_name},
            {"label": "Benutzer", "value": user_session.identity.username},
            {"label": "E-Mail", "value": user_session.identity.email or "-"},
            {"label": "Gruppen", "value": ", ".join(sorted(user_session.identity.ad_groups)) or "-"},
        ]
        meta = {"groupCount": len(user_session.identity.ad_groups)}
        message = "AD-Kontext aus Login-Session geladen."
        if connector_payload:
            meta["connectorRsatReady"] = bool(connector_payload.get("rsatReady", False))
            message = str(connector_payload.get("message", message))
            if detail:
                items.append({"label": "RSAT Ready", "value": str(connector_payload.get("rsatReady", False))})
                items.append({"label": "Connector Quelle", "value": str(connector_payload.get("source", "connector"))})
        if not detail:
            items = items[:2]
        return {
            "id": str(definition.get("id", "ad")),
            "title": str(definition.get("title", "Active Directory")),
            "status": "ok",
            "source": "session",
            "message": message,
            "items": items,
            "meta": meta,
        }

    def _nutanix_response(
        self,
        definition: dict[str, Any],
        username: str,
        password: str,
        *,
        detail: bool,
    ) -> dict[str, Any]:
        base_url = str(definition.get("base_url", "")).rstrip("/")
        if not base_url:
            raise RuntimeError("Nutanix base_url fehlt in integrations.json.")
        verify_tls = bool(definition.get("verify_tls", True))
        session = requests.Session()
        session.auth = (username, password)
        clusters_response = session.post(
            f"{base_url}/api/nutanix/v3/clusters/list",
            json={"kind": "cluster", "length": 50, "offset": 0},
            verify=verify_tls,
            timeout=20,
        )
        clusters_response.raise_for_status()
        clusters = clusters_response.json().get("entities", [])
        vm_response = session.post(
            f"{base_url}/api/nutanix/v3/vms/list",
            json={"kind": "vm", "length": 15 if detail else 5, "offset": 0},
            verify=verify_tls,
            timeout=20,
        )
        vm_response.raise_for_status()
        vm_entities = vm_response.json().get("entities", [])
        items = [
            {
                "label": str(vm.get("status", {}).get("name") or vm.get("spec", {}).get("name") or "Unbekannt"),
                "value": str(vm.get("status", {}).get("resources", {}).get("power_state") or "unknown"),
            }
            for vm in vm_entities
        ]
        return {
            "id": str(definition.get("id", "nutanix")),
            "title": str(definition.get("title", "Nutanix")),
            "status": "ok",
            "source": "live",
            "message": f"{len(clusters)} Cluster und {len(vm_entities)} VM-Eintraege geladen.",
            "items": items,
            "meta": {"clusters": len(clusters), "sampleVmCount": len(vm_entities)},
        }

    def _vsphere_response(
        self,
        definition: dict[str, Any],
        username: str,
        password: str,
        *,
        detail: bool,
    ) -> dict[str, Any]:
        base_url = str(definition.get("base_url", "")).rstrip("/")
        if not base_url:
            raise RuntimeError("vSphere base_url fehlt in integrations.json.")
        verify_tls = bool(definition.get("verify_tls", True))
        session = requests.Session()
        auth_response = session.post(
            f"{base_url}/api/session",
            auth=(username, password),
            verify=verify_tls,
            timeout=20,
        )
        auth_response.raise_for_status()
        session_id = auth_response.text.strip().strip('"')
        session.headers["vmware-api-session-id"] = session_id
        vm_response = session.get(
            f"{base_url}/api/vcenter/vm",
            verify=verify_tls,
            timeout=20,
        )
        vm_response.raise_for_status()
        vm_items = vm_response.json()
        if not isinstance(vm_items, list):
            raise RuntimeError("vSphere Antwortformat unerwartet.")
        preview = vm_items[: 12 if detail else 5]
        items = [
            {
                "label": str(vm.get("name", "Unbekannt")),
                "value": str(vm.get("power_state", "unknown")),
            }
            for vm in preview
        ]
        return {
            "id": str(definition.get("id", "vsphere")),
            "title": str(definition.get("title", "vSphere")),
            "status": "ok",
            "source": "live",
            "message": f"{len(vm_items)} VMs geladen.",
            "items": items,
            "meta": {"vmCount": len(vm_items)},
        }

    def _endpoint_response(
        self,
        definition: dict[str, Any],
        username: str,
        password: str,
        *,
        detail: bool,
    ) -> dict[str, Any]:
        base_url = str(definition.get("base_url", "")).rstrip("/")
        inventory_path = str(definition.get("inventory_path", "")).strip()
        if not base_url or not inventory_path:
            raise RuntimeError("Endpoint Central ist nicht vollstaendig konfiguriert.")
        verify_tls = bool(definition.get("verify_tls", True))
        auth_mode = str(definition.get("auth_mode", "session_basic"))
        headers: dict[str, str] = {}
        kwargs: dict[str, Any] = {"verify": verify_tls, "timeout": 20}
        if auth_mode == "bearer":
            token = os.getenv(str(definition.get("token_env", "")), "").strip()
            if not token:
                raise RuntimeError("Endpoint Bearer-Token fehlt.")
            headers["Authorization"] = f"Bearer {token}"
        else:
            kwargs["auth"] = (username, password)
        response = requests.get(f"{base_url}{inventory_path}", headers=headers, **kwargs)
        response.raise_for_status()
        payload = response.json()
        raw_items = self._extract_endpoint_items(payload)
        preview = raw_items[: 12 if detail else 5]
        items = [
            {
                "label": str(item.get("name") or item.get("display_name") or item.get("device_name") or "Objekt"),
                "value": str(item.get("status") or item.get("agent_status") or item.get("platform_type") or "ok"),
            }
            for item in preview
        ]
        return {
            "id": str(definition.get("id", "endpoint")),
            "title": str(definition.get("title", "Endpoint Central")),
            "status": "ok",
            "source": "live",
            "message": f"{len(raw_items)} Endpoint-Eintraege geladen.",
            "items": items,
            "meta": {"inventoryCount": len(raw_items)},
        }

    def _citrix_response(self, definition: dict[str, Any], *, detail: bool, allow_mock: bool) -> dict[str, Any]:
        connector_payload = self._connector_client.citrix_summary()
        if connector_payload:
            items = list(connector_payload.get("items", []))
            if not detail:
                items = items[:3]
            return {
                "id": str(definition.get("id", "citrix")),
                "title": str(definition.get("title", "Citrix On-Prem")),
                "status": str(connector_payload.get("status", "ok")),
                "source": str(connector_payload.get("source", "connector")),
                "message": str(connector_payload.get("message", "Citrix-Daten ueber Connector geladen.")),
                "items": items,
                "meta": dict(connector_payload.get("meta", {})),
            }
        if allow_mock:
            return self._mock_response(definition, detail=detail)
        admin_address = str(definition.get("admin_address", "")).strip()
        message = "Windows Connector erforderlich fuer Citrix On-Prem Automatisierung."
        if admin_address:
            message = f"Windows Connector fuer Delivery Controller {admin_address} vorgesehen."
        items = []
        if detail:
            items = [
                {"label": "Modus", "value": "Connector erforderlich"},
                {"label": "Admin Address", "value": admin_address or "nicht konfiguriert"},
            ]
        return {
            "id": str(definition.get("id", "citrix")),
            "title": str(definition.get("title", "Citrix On-Prem")),
            "status": "planned",
            "source": "connector",
            "message": message,
            "items": items,
            "meta": {"connectorRequired": True},
        }

    @staticmethod
    def _extract_endpoint_items(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            candidates = [
                payload.get("devices"),
                payload.get("computers"),
                payload.get("data"),
                payload.get("results"),
                payload.get("value"),
            ]
            for candidate in candidates:
                if isinstance(candidate, list):
                    return [item for item in candidate if isinstance(item, dict)]
                if isinstance(candidate, dict):
                    nested_values = list(candidate.values())
                    for nested in nested_values:
                        if isinstance(nested, list):
                            return [item for item in nested if isinstance(item, dict)]
        return []
