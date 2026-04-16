"""
vSphere API Client for live VM operations.

Provides methods for:
- Authentication with vCenter
- Listing VMs, datastores, networks
- Power operations
- VM management
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests


logger = logging.getLogger("admin-startpage.vsphere")


class VSphereApiError(Exception):
    """Exception raised for vSphere API errors."""
    pass


class VSphereClient:
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
        self._session_id: str | None = None
    
    def authenticate(self) -> str:
        """Authenticate with vCenter and get session ID."""
        auth_response = self._session.post(
            f"{self._base_url}/api/session",
            auth=(self._username, self._password),
        )
        if auth_response.status_code != 201:
            raise VSphereApiError(f"Authentication failed: {auth_response.status_code} - {auth_response.text}")
        
        self._session_id = auth_response.text.strip().strip('"')
        self._session.headers["vmware-api-session-id"] = self._session_id
        logger.info(f"Authenticated with vCenter: {self._base_url}")
        return self._session_id
    
    def logout(self) -> None:
        """Logout from vCenter."""
        if self._session_id:
            try:
                self._session.delete(f"{self._base_url}/api/session")
            except Exception:
                pass
            self._session_id = None
    
    def list_vms(self, max_results: int = 50) -> list[dict[str, Any]]:
        """List all VMs."""
        if not self._session_id:
            self.authenticate()
        
        response = self._session.get(
            f"{self._base_url}/api/vcenter/vm",
            params={"maxResults": max_results},
        )
        if response.status_code != 200:
            raise VSphereApiError(f"Failed to list VMs: {response.status_code}")
        
        return response.json()
    
    def get_vm(self, vm_id: str) -> dict[str, Any]:
        """Get specific VM details."""
        if not self._session_id:
            self.authenticate()
        
        response = self._session.get(f"{self._base_url}/api/vcenter/vm/{vm_id}")
        if response.status_code != 200:
            raise VSphereApiError(f"Failed to get VM: {response.status_code}")
        
        return response.json()
    
    def power_on_vm(self, vm_id: str) -> dict[str, Any]:
        """Power on a VM."""
        if not self._session_id:
            self.authenticate()
        
        response = self._session.post(
            f"{self._base_url}/api/vcenter/vm/{vm_id}/power/start",
        )
        if response.status_code not in (200, 201):
            raise VSphereApiError(f"Failed to power on VM: {response.status_code}")
        
        return response.json()
    
    def power_off_vm(self, vm_id: str) -> dict[str, Any]:
        """Power off a VM."""
        if not self._session_id:
            self.authenticate()
        
        response = self._session.post(
            f"{self._base_url}/api/vcenter/vm/{vm_id}/power/stop",
        )
        if response.status_code not in (200, 201):
            raise VSphereApiError(f"Failed to power off VM: {response.status_code}")
        
        return response.json()
    
    def list_datastores(self) -> list[dict[str, Any]]:
        """List all datastores."""
        if not self._session_id:
            self.authenticate()
        
        response = self._session.get(f"{self._base_url}/api/vcenter/datastore")
        if response.status_code != 200:
            raise VSphereApiError(f"Failed to list datastores: {response.status_code}")
        
        return response.json()
    
    def list_networks(self) -> list[dict[str, Any]]:
        """List all networks."""
        if not self._session_id:
            self.authenticate()
        
        response = self._session.get(f"{self._base_url}/api/vcenter/network")
        if response.status_code != 200:
            raise VSphereApiError(f"Failed to list networks: {response.status_code}")
        
        return response.json()
    
    def list_clusters(self) -> list[dict[str, Any]]:
        """List all clusters."""
        if not self._session_id:
            self.authenticate()
        
        response = self._session.get(f"{self._base_url}/api/vcenter/cluster")
        if response.status_code != 200:
            raise VSphereApiError(f"Failed to list clusters: {response.status_code}")
        
        return response.json()
    
    def list_hosts(self) -> list[dict[str, Any]]:
        """List all hosts."""
        if not self._session_id:
            self.authenticate()
        
        response = self._session.get(f"{self._base_url}/api/vcenter/host")
        if response.status_code != 200:
            raise VSphereApiError(f"Failed to list hosts: {response.status_code}")
        
        return response.json()


def create_from_config(
    config: dict[str, Any],
    username: str,
    password: str,
) -> VSphereClient:
    """Create VSphereClient from integration config and credentials."""
    base_url = str(config.get("base_url", "")).strip()
    verify_tls = bool(config.get("verify_tls", True))
    
    if not base_url:
        raise VSphereApiError("vSphere base_url not configured")
    
    return VSphereClient(
        base_url=base_url,
        username=username,
        password=password,
        verify_tls=verify_tls,
    )