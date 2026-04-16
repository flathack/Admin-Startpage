from __future__ import annotations

import os
from typing import Any

import requests


class ConnectorClient:
    def __init__(self) -> None:
        self._base_url = os.getenv("STARTPAGE_CONNECTOR_URL", "http://localhost:8090").rstrip("/")
        self._enabled = os.getenv("STARTPAGE_CONNECTOR_ENABLED", "false").lower() == "true"
        self._timeout = int(os.getenv("STARTPAGE_CONNECTOR_TIMEOUT_SECONDS", "6"))

    @property
    def enabled(self) -> bool:
        return self._enabled

    def status(self) -> dict[str, Any]:
        if not self._enabled:
            return {
                "enabled": False,
                "reachable": False,
                "baseUrl": self._base_url,
                "mode": "disabled",
                "message": "Windows Connector ist deaktiviert.",
                "capabilities": [],
            }

        try:
            response = requests.get(f"{self._base_url}/health", timeout=self._timeout)
            response.raise_for_status()
            payload = response.json()
            return {
                "enabled": True,
                "reachable": True,
                "baseUrl": self._base_url,
                "mode": str(payload.get("mode", "unknown")),
                "message": str(payload.get("message", "Connector erreichbar.")),
                "capabilities": list(payload.get("capabilities", [])),
            }
        except Exception as exc:
            return {
                "enabled": True,
                "reachable": False,
                "baseUrl": self._base_url,
                "mode": "unreachable",
                "message": f"Windows Connector nicht erreichbar: {exc}",
                "capabilities": [],
            }

    def ad_session_context(self, identity: dict[str, Any]) -> dict[str, Any] | None:
        if not self._enabled:
            return None
        try:
            response = requests.post(
                f"{self._base_url}/api/ad/session-context",
                json=identity,
                timeout=self._timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

    def citrix_summary(self) -> dict[str, Any] | None:
        if not self._enabled:
            return None
        try:
            response = requests.get(
                f"{self._base_url}/api/citrix/summary",
                timeout=self._timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            return None
