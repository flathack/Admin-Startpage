from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .auth_service import ADIdentity


@dataclass
class UserSession:
    identity: ADIdentity
    roles: frozenset[str] = field(default_factory=frozenset)
    permissions: frozenset[str] = field(default_factory=frozenset)
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    login_time: datetime = field(default_factory=datetime.utcnow)


MODULE_DEFINITIONS: list[dict[str, str]] = [
    {
        "id": "dashboard",
        "title": "Dashboard",
        "description": "Persoenliche Uebersicht, Favoriten und globale Hinweise.",
        "permission": "startpage.dashboard.view",
    },
    {
        "id": "ad",
        "title": "Active Directory",
        "description": "Benutzer, Computer, Gruppen und spaetere Reports.",
        "permission": "ad.view",
    },
    {
        "id": "nutanix",
        "title": "Nutanix",
        "description": "Cluster-, VM- und Infrastrukturzugriffe.",
        "permission": "nutanix.view",
    },
    {
        "id": "endpoint",
        "title": "Endpoint Central",
        "description": "Geraete, Agent-Status und Patch-nahe Informationen.",
        "permission": "endpoint.view",
    },
    {
        "id": "vsphere",
        "title": "vSphere",
        "description": "Virtuelle Maschinen und Betriebszustand.",
        "permission": "vsphere.view",
    },
    {
        "id": "citrix",
        "title": "Citrix On-Prem",
        "description": "Maschinen, Zuweisungen und Wartungsmodus.",
        "permission": "citrix.view",
    },
    {
        "id": "rollout",
        "title": "Rollout",
        "description": "Rollout-nahe Uebersicht fuer Infrastruktur und Folgefunktionen.",
        "permission": "rollout.view",
    },
]


class PermissionService:
    def __init__(self, config_dir: Path) -> None:
        self._config_dir = config_dir
        self._roles_path = config_dir / "roles.json"
        self._mapping_path = config_dir / "group_mapping.json"
        self._roles = self._load_roles()
        self._group_mapping, self._default_role = self._load_group_mapping()

    def build_session(self, identity: ADIdentity) -> UserSession:
        roles = self.resolve_roles(identity.ad_groups)
        permissions = self.resolve_permissions(roles)
        return UserSession(identity=identity, roles=roles, permissions=permissions)

    def resolve_roles(self, ad_groups: frozenset[str]) -> frozenset[str]:
        mapping_lower = {key.lower(): value for key, value in self._group_mapping.items()}
        resolved: set[str] = set()
        for group_name in ad_groups:
            resolved.update(mapping_lower.get(group_name.lower(), []))
        if not resolved:
            resolved.add(self._default_role)
        return frozenset(resolved)

    def resolve_permissions(self, roles: frozenset[str]) -> frozenset[str]:
        permissions: set[str] = set()
        for role_name in roles:
            permissions.update(self._roles.get(role_name, []))
        return frozenset(permissions)

    def visible_modules(self, permissions: frozenset[str]) -> list[dict[str, Any]]:
        visible: list[dict[str, Any]] = []
        for module in MODULE_DEFINITIONS:
            if self.has_permission(permissions, module["permission"]):
                visible.append(module)
        return visible

    @staticmethod
    def has_permission(permissions: frozenset[str], required_permission: str) -> bool:
        if required_permission in permissions:
            return True
        domain, _, action = required_permission.partition(".")
        return bool(action) and f"{domain}.*" in permissions

    def _load_roles(self) -> dict[str, list[str]]:
        data = json.loads(self._roles_path.read_text(encoding="utf-8"))
        roles = data.get("roles", {})
        normalized: dict[str, list[str]] = {}
        for role_name, role_definition in roles.items():
            if isinstance(role_definition, dict):
                normalized[role_name] = list(role_definition.get("permissions", []))
            elif isinstance(role_definition, list):
                normalized[role_name] = list(role_definition)
        return normalized

    def _load_group_mapping(self) -> tuple[dict[str, list[str]], str]:
        data = json.loads(self._mapping_path.read_text(encoding="utf-8"))
        raw_mapping = data.get("group_role_mapping", {})
        mapping: dict[str, list[str]] = {}
        for group_name, roles in raw_mapping.items():
            if isinstance(roles, list):
                mapping[group_name] = roles
            elif isinstance(roles, str):
                mapping[group_name] = [roles]
        default_role = str(data.get("default_role", "viewer"))
        return mapping, default_role
