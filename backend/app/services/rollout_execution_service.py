from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from .rollout_job_store import RolloutJobStore
from .rollout_models import RolloutJob, RolloutStatus


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
                self._run_mock_job(job)
                return
            self._run_live_placeholder(job, username=username, password=password)
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

    def _run_live_placeholder(self, job: RolloutJob, *, username: str, password: str) -> None:
        base_url = str(self._find_system("nutanix").get("base_url", "")).strip()
        verify_tls = bool(self._find_system("nutanix").get("verify_tls", True))
        job = self._load_job(job.job_id)
        job.update_status(RolloutStatus.ERROR, job.progress)
        job.client_stage = "Live-Start noch unvollstaendig"
        job.client_message = (
            "Live-Nutanix-Start ist vorbereitet, aber create_clone/boot-Operationen sind noch nicht vollstaendig portiert. "
            f"Basis: {base_url or 'keine URL'} | TLS: {verify_tls} | User: {username or '-'}"
        )
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
