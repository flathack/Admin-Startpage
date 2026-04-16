from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any

from .nutanix_client import NutanixClient, create_from_config, NutanixApiError
from .rollout_job_store import RolloutJobStore
from .rollout_models import RolloutJob, RolloutStatus


logger = logging.getLogger("admin-startpage.rollout")


class RolloutExecutionService:
    def __init__(
        self,
        *,
        integrations_config_path: Path,
        job_store: RolloutJobStore,
        mock_enabled: bool,
        mock_step_delay_seconds: int,
    ) -> None:
        self._integrations_config_path = integrations_config_path
        self._job_store = job_store
        self._mock_enabled = mock_enabled
        self._mock_step_delay_seconds = max(1, int(mock_step_delay_seconds))
        self._lock = threading.Lock()
        self._running_job_ids: set[str] = set()
        self._integrations = json.loads(integrations_config_path.read_text(encoding="utf-8"))

    def is_job_running(self, job_id: str) -> bool:
        with self._lock:
            return job_id in self._running_job_ids

    def start_job(self, job: RolloutJob, *, username: str, password: str) -> dict[str, Any]:
        with self._lock:
            if job.job_id in self._running_job_ids:
                return {"started": False, "message": f"{job.job_id}: Job laeuft bereits."}
            self._running_job_ids.add(job.job_id)

        job.client_stage = "Worker initialisiert"
        job.client_message = "Rollout-Start wurde angefordert."
        job.update_status(RolloutStatus.CLONE_CREATING, max(job.progress, 1))
        job.client_updated_at = time.time()
        self._job_store.save_job(job)

        worker = threading.Thread(
            target=self._run_job,
            args=(job.job_id, username, password),
            name=f"startpage-rollout-{job.job_id}",
            daemon=True,
        )
        worker.start()
        return {"started": True, "message": f"{job.job_id}: Rollout-Worker gestartet."}

    def _run_job(self, job_id: str, username: str, password: str) -> None:
        try:
            job = self._load_job(job_id)
            nutanix_definition = self._find_system("nutanix")
            use_mock = self._mock_enabled or bool(nutanix_definition.get("mock", False))
            if use_mock:
                logger.info(f"Running mock job for {job_id}")
                self._run_mock_job(job)
                return
            logger.info(f"Running live Nutanix job for {job_id}")
            self._run_live_job(job, username=username, password=password)
        except Exception as exc:
            logger.error(f"Job {job_id} failed with exception: {exc}")
        finally:
            with self._lock:
                self._running_job_ids.discard(job_id)

    def _run_mock_job(self, job: RolloutJob) -> None:
        steps = [
            (RolloutStatus.CLONE_CREATING, 15, "Klon wird auf Nutanix erstellt."),
            (RolloutStatus.CLONE_CREATING, 28, "Klon ist in Nutanix sichtbar."),
            (RolloutStatus.CLONE_CREATING, 35, "Netzwerkzuweisung abgeschlossen."),
            (RolloutStatus.BOOTING, 40, "VM wird gestartet."),
            (RolloutStatus.BOOTING, 45, "Power-Status ist ON."),
            (RolloutStatus.ROLLOUT_RUNNING, 55, "WinPE-Phase gestartet. Warte auf ASSIGN/ACK."),
        ]
        for status, progress, message in steps:
            time.sleep(self._mock_step_delay_seconds)
            job = self._load_job(job.job_id)
            job.update_status(status, progress)
            job.client_stage = status.value
            job.client_message = message
            job.client_updated_at = time.time()
            self._job_store.save_job(job)

    def _run_live_job(self, job: RolloutJob, *, username: str, password: str) -> None:
        """Execute actual Nutanix VM provisioning."""
        try:
            nutanix_config = self._find_system("nutanix")
            logger.info(f"Starting live Nutanix rollout for job {job.job_id}")
            
            client = create_from_config(nutanix_config, username, password)
            
            # Get cluster and template info
            clusters = client.list_clusters()
            if not clusters:
                raise NutanixApiError("No clusters available")
            cluster = clusters[0]
            cluster_uuid = cluster.get("uuid")
            logger.info(f"Using cluster: {cluster.get('name')} ({cluster_uuid})")
            
            # List templates (images)
            templates = client.list_vm_templates(cluster_uuid)
            template_uuid = None
            for t in templates:
                if job.template.lower() in t.get("name", "").lower():
                    template_uuid = t.get("uuid")
                    break
            
            if not template_uuid:
                # Try first available template
                if templates:
                    template_uuid = templates[0].get("uuid")
                    logger.info(f"Using first available template: {templates[0].get('name')}")
                else:
                    raise NutanixApiError(f"No templates found matching: {job.template}")
            
            # Create VM from template
            job.update_status(RolloutStatus.CLONE_CREATING, 15)
            job.client_stage = "CLONE_CREATING"
            job.client_message = "Creating VM clone on Nutanix cluster..."
            self._job_store.save_job(job)
            
            result = client.create_vm_from_template(
                vm_name=job.hostname,
                template_uuid=template_uuid,
                cluster_uuid=cluster_uuid,
                vlan=job.network,
            )
            
            vm_uuid = result.get("uuid")
            logger.info(f"VM created with UUID: {vm_uuid}")
            
            job.update_status(RolloutStatus.CLONE_CREATING, 35)
            job.client_stage = "CLONE_CREATING"
            job.client_message = "VM clone created, starting VM..."
            self._job_store.save_job(job)
            
            # Power on VM
            client.power_on_vm(vm_uuid)
            logger.info(f"VM {job.hostname} powered on")
            
            job.update_status(RolloutStatus.BOOTING, 50)
            job.client_stage = "BOOTING"
            job.client_message = "VM is booting, waiting for WinPE..."
            self._job_store.save_job(job)
            
            # Wait briefly and check status
            time.sleep(5)
            power_state = client.get_vm_power_state(vm_uuid)
            logger.info(f"VM power state: {power_state}")
            
            # Mark as rollout running - waiting for ASSIGN/ACK
            job.update_status(RolloutStatus.ROLLOUT_RUNNING, 60)
            job.client_stage = "ROLLOUT_RUNNING"
            job.client_message = "VM booted, waiting for WinPE registration and ASSIGN/ACK..."
            job.client_updated_at = time.time()
            self._job_store.save_job(job)
            logger.info(f"Live Nutanix rollout completed for job {job.job_id}")
            
        except NutanixApiError as exc:
            logger.error(f"Nutanix API error for job {job.job_id}: {exc}")
            job.update_status(RolloutStatus.ERROR, job.progress)
            job.client_stage = "ERROR"
            job.client_message = f"Nutanix API Error: {exc}"
            job.client_updated_at = time.time()
            self._job_store.save_job(job)
        except Exception as exc:
            logger.error(f"Unexpected error during live rollout for job {job.job_id}: {exc}")
            job.update_status(RolloutStatus.ERROR, job.progress)
            job.client_stage = "ERROR"
            job.client_message = f"Rollout Error: {exc}"
            job.client_updated_at = time.time()
            self._job_store.save_job(job)

    def _load_job(self, job_id: str) -> RolloutJob:
        for job in self._job_store.load_jobs():
            if job.job_id == job_id:
                return job
        raise KeyError(job_id)

    def _find_system(self, system_id: str) -> dict[str, Any]:
        for definition in self._integrations.get("systems", []):
            if str(definition.get("id", "")).strip() == system_id:
                return definition
        raise KeyError(system_id)
