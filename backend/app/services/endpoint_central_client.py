"""
Endpoint Central (ManageEngine) API Client for live operations.

Provides methods for:
- Listing devices, computers, servers
- Agent status
- Patch management
- Device actions
"""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import Any

import requests


logger = logging.getLogger("admin-startpage.endpoint")


class EndpointCentralApiError(Exception):
    """Exception raised for Endpoint Central API errors."""
    pass


class EndpointCentralClient:
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        *,
        verify_tls: bool = True,
        session: requests.Session | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._verify_tls = verify_tls
        self._session = session or requests.Session()
        self._session.verify = verify_tls
        self._auth = base64.b64encode(f"{username}:{password}".encode()).decode()
        self._session.headers["Authorization"] = f"Basic {self._auth}"
    
    def _make_request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Make authenticated request to Endpoint Central API."""
        url = f"{self._base_url}{path}"
        response = self._session.request(method, url, **kwargs)
        if response.status_code >= 400:
            raise EndpointCentralApiError(f"API request failed: {response.status_code} - {response.text}")
        return response
    
    def list_computers(self, page: int = 1, page_limit: int = 100) -> dict[str, Any]:
        """List all computers/devices."""
        path = f"/api/1.4/som/computers?page={page}&pagelimit={page_limit}"
        response = self._make_request("GET", path)
        return response.json()
    
    def get_computer(self, computer_id: str) -> dict[str, Any]:
        """Get specific computer details."""
        path = f"/api/1.4/som/computers/{computer_id}"
        response = self._make_request("GET", path)
        return response.json()
    
    def list_device_groups(self) -> list[dict[str, Any]]:
        """List all device groups."""
        path = "/api/1.4/som/groups"
        response = self._make_request("GET", path)
        return response.json()
    
    def get_agent_status(self, computer_id: str) -> dict[str, Any]:
        """Get agent status for a computer."""
        path = f"/api/1.4/som/computers/{computer_id}/agentStatus"
        response = self._make_request("GET", path)
        return response.json()
    
    def list_patches(self, computer_id: str | None = None) -> list[dict[str, Any]]:
        """List available patches."""
        if computer_id:
            path = f"/api/1.4/som/computers/{computer_id}/patches"
        else:
            path = "/api/1.4/patch/patches"
        response = self._make_request("GET", path)
        return response.json()
    
    def get_patch_status(self, computer_id: str) -> dict[str, Any]:
        """Get patch status for a computer."""
        path = f"/api/1.4/som/computers/{computer_id}/patchStatus"
        response = self._make_request("GET", path)
        return response.json()
    
    def invoke_action(self, computer_id: str, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Invoke an action on a computer (e.g., scan, restart)."""
        path = f"/api/1.4/som/computers/{computer_id}/actions"
        payload = {"action": action, **(params or {})}
        response = self._make_request("POST", path, json=payload)
        return response.json()
    
    def get_inventory(self, computer_id: str) -> dict[str, Any]:
        """Get software inventory for a computer."""
        path = f"/api/1.4/som/computers/{computer_id}/software"
        response = self._make_request("GET", path)
        return response.json()
    
    def get_summary(self) -> dict[str, Any]:
        """Get overall Endpoint Central summary."""
        path = "/api/1.4/som/summary"
        response = self._make_request("GET", path)
        return response.json()


def create_from_config(
    config: dict[str, Any],
    username: str,
    password: str,
) -> EndpointCentralClient:
    """Create EndpointCentralClient from integration config and credentials."""
    base_url = str(config.get("base_url", "")).strip()
    verify_tls = bool(config.get("verify_tls", True))
    
    if not base_url:
        raise EndpointCentralApiError("Endpoint Central base_url not configured")
    
    return EndpointCentralClient(
        base_url=base_url,
        username=username,
        password=password,
        verify_tls=verify_tls,
    )