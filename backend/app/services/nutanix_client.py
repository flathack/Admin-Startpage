"""
Nutanix API Client for live VM operations.

Provides methods for:
- VM cloning and provisioning
- VM power operations
- Network configuration
- VM status retrieval
"""
from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


logger = logging.getLogger("admin-startpage.nutanix")


@dataclass
class NutanixCredentials:
    username: str
    password: str
    base_url: str
    verify_tls: bool = True


class NutanixApiError(Exception):
    """Exception raised for Nutanix API errors."""
    pass


class NutanixClient:
    def __init__(
        self,
        credentials: NutanixCredentials,
        *,
        session: requests.Session | None = None,
    ) -> None:
        self._credentials = credentials
        self._session = session or requests.Session()
        self._session.verify = credentials.verify_tls
        self._auth = (credentials.username, credentials.password)
        self._base_url = credentials.base_url.rstrip("/")

    def authenticate(self) -> str:
        """Authenticate and get session token."""
        auth_payload = {
            "username": self._credentials.username,
            "password": self._credentials.password,
        }
        response = self._session.post(
            f"{self._base_url}/api/nutanix/v3/authenticate",
            json=auth_payload,
            headers={"Content-Type": "application/json"},
        )
        if response.status_code != 200:
            raise NutanixApiError(f"Authentication failed: {response.status_code} - {response.text}")
        data = response.json()
        token = data.get("access_token")
        if not token:
            raise NutanixApiError("No access token in authentication response")
        self._session.headers.update({"Authorization": f"Basic {base64.b64encode(f'{self._credentials.username}:{self._credentials.password}'.encode()).decode()}"})
        return token

    def list_clusters(self) -> list[dict[str, Any]]:
        """List available clusters."""
        response = self._session.get(f"{self._base_url}/api/nutanix/v3/clusters")
        if response.status_code != 200:
            raise NutanixApiError(f"Failed to list clusters: {response.status_code}")
        return response.json().get("entities", [])

    def get_cluster(self, cluster_uuid: str) -> dict[str, Any]:
        """Get cluster details by UUID."""
        response = self._session.get(f"{self._base_url}/api/nutanix/v3/clusters/{cluster_uuid}")
        if response.status_code != 200:
            raise NutanixApiError(f"Failed to get cluster: {response.status_code}")
        return response.json()

    def list_vm_templates(self, cluster_uuid: str) -> list[dict[str, Any]]:
        """List VM templates (images) in a cluster."""
        response = self._session.get(
            f"{self._base_url}/api/nutanix/v3/vms",
            params={"kind": "image", "cluster_uuid": cluster_uuid},
        )
        if response.status_code != 200:
            raise NutanixApiError(f"Failed to list templates: {response.status_code}")
        return response.json().get("entities", [])

    def create_vm_from_template(
        self,
        *,
        vm_name: str,
        template_uuid: str,
        cluster_uuid: str,
        vlan: str,
        num_vcpus: int = 2,
        num_cores: int = 2,
        memory_gb: int = 4,
    ) -> dict[str, Any]:
        """
        Create a VM by cloning from a template (image).
        
        This performs:
        1. Clone image to disk
        2. Create VM with cloned disk
        3. Configure network
        """
        vm_spec = {
            "name": vm_name,
            "resources": {
                "num_vcpus": num_vcpus,
                "num_cores_per_vcpu": num_cores,
                "memory_size_mib": memory_gb * 1024,
                "disk_list": [
                    {
                        "data_source_reference": {
                            "kind": "image",
                            "uuid": template_uuid,
                        },
                        "device_type": "DISK",
                    }
                ],
                "nic_list": [
                    {
                        "network_reference": {
                            "kind": "subnet",
                            "name": vlan,
                        },
                    }
                ],
            },
            "cluster_reference": {
                "kind": "cluster",
                "uuid": cluster_uuid,
            },
        }
        
        response = self._session.post(
            f"{self._base_url}/api/nutanix/v3/vms",
            json=vm_spec,
            headers={"Content-Type": "application/json"},
        )
        
        if response.status_code not in (200, 201, 202):
            raise NutanixApiError(f"Failed to create VM: {response.status_code} - {response.text}")
        
        return response.json()

    def get_vm(self, vm_uuid: str) -> dict[str, Any]:
        """Get VM details by UUID."""
        response = self._session.get(f"{self._base_url}/api/nutanix/v3/vms/{vm_uuid}")
        if response.status_code != 200:
            raise NutanixApiError(f"Failed to get VM: {response.status_code}")
        return response.json()

    def list_vms(self, cluster_uuid: str | None = None) -> list[dict[str, Any]]:
        """List VMs, optionally filtered by cluster."""
        params: dict[str, str] = {"kind": "vm"}
        if cluster_uuid:
            params["cluster_uuid"] = cluster_uuid
        response = self._session.get(f"{self._base_url}/api/nutanix/v3/vms", params=params)
        if response.status_code != 200:
            raise NutanixApiError(f"Failed to list VMs: {response.status_code}")
        return response.json().get("entities", [])

    def power_on_vm(self, vm_uuid: str) -> dict[str, Any]:
        """Power on a VM."""
        action_payload = {"action": "ON"}
        response = self._session.post(
            f"{self._base_url}/api/nutanix/v3/vms/{vm_uuid}/power_state_transition",
            json=action_payload,
            headers={"Content-Type": "application/json"},
        )
        if response.status_code not in (200, 201, 202):
            raise NutanixApiError(f"Failed to power on VM: {response.status_code} - {response.text}")
        return response.json()

    def power_off_vm(self, vm_uuid: str) -> dict[str, Any]:
        """Power off a VM."""
        action_payload = {"action": "OFF"}
        response = self._session.post(
            f"{self._base_url}/api/nutanix/v3/vms/{vm_uuid}/power_state_transition",
            json=action_payload,
            headers={"Content-Type": "application/json"},
        )
        if response.status_code not in (200, 201, 202):
            raise NutanixApiError(f"Failed to power off VM: {response.status_code} - {response.text}")
        return response.json()

    def delete_vm(self, vm_uuid: str) -> dict[str, Any]:
        """Delete a VM."""
        response = self._session.delete(f"{self._base_url}/api/nutanix/v3/vms/{vm_uuid}")
        if response.status_code not in (200, 204):
            raise NutanixApiError(f"Failed to delete VM: {response.status_code} - {response.text}")
        return {"deleted": True, "vm_uuid": vm_uuid}

    def get_vm_power_state(self, vm_uuid: str) -> str:
        """Get VM power state."""
        vm = self.get_vm(vm_uuid)
        return vm.get("spec", {}).get("resources", {}).get("power_state", "UNKNOWN")


def create_from_config(
    config: dict[str, Any],
    username: str,
    password: str,
) -> NutanixClient:
    """Create NutanixClient from integration config and credentials."""
    base_url = str(config.get("base_url", "")).strip()
    verify_tls = bool(config.get("verify_tls", True))
    
    if not base_url:
        raise NutanixApiError("Nutanix base_url not configured")
    
    credentials = NutanixCredentials(
        username=username,
        password=password,
        base_url=base_url,
        verify_tls=verify_tls,
    )
    return NutanixClient(credentials)