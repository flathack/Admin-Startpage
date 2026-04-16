from __future__ import annotations

import re
from collections import Counter
from copy import deepcopy
from time import time
from typing import Any

from .rollout_job_store import RolloutJobStore
from .rollout_models import RolloutJob, RolloutStatus


class RolloutService:
    def __init__(self, job_store: RolloutJobStore) -> None:
        self._job_store = job_store

    def list_jobs(self) -> list[RolloutJob]:
        return sorted(self._job_store.load_jobs(), key=lambda item: item.created_at, reverse=True)

    def summary(self) -> dict[str, Any]:
        jobs = self.list_jobs()
        status_counter = Counter(job.status.value for job in jobs)
        return {
            "jobCount": len(jobs),
            "plannedCount": status_counter.get(RolloutStatus.PLANNED.value, 0),
            "runningCount": sum(
                status_counter.get(value, 0)
                for value in (
                    RolloutStatus.CLONE_CREATING.value,
                    RolloutStatus.BOOTING.value,
                    RolloutStatus.WAITING_REGISTRATION.value,
                    RolloutStatus.ROLLOUT_RUNNING.value,
                    RolloutStatus.SYSPREP.value,
                )
            ),
            "errorCount": status_counter.get(RolloutStatus.ERROR.value, 0),
            "finishedCount": status_counter.get(RolloutStatus.SYSPREP_FINISHED.value, 0),
            "tasksDirectory": str(self._job_store.tasks_dir),
        }

    def get_job(self, job_id: str) -> RolloutJob:
        for job in self.list_jobs():
            if job.job_id == job_id:
                return job
        raise KeyError(job_id)

    def create_job(
        self,
        *,
        hostname: str,
        template: str,
        cluster: str,
        network: str,
        created_by: str,
        tags: list[str] | None = None,
    ) -> RolloutJob:
        normalized_hostname = hostname.strip().upper()
        if not normalized_hostname:
            raise ValueError("Hostname ist erforderlich.")
        if any(job.hostname.upper() == normalized_hostname for job in self.list_jobs()):
            raise ValueError(f"Fuer Hostname {normalized_hostname} existiert bereits ein Rollout-Job.")

        job = RolloutJob(
            job_id=self._next_job_id(),
            hostname=normalized_hostname,
            template=template.strip(),
            cluster=cluster.strip(),
            network=network.strip(),
            created_by=created_by.strip(),
            bootstrap_name=normalized_hostname,
            status=RolloutStatus.PLANNED,
            progress=0,
            client_stage="Geplant",
            client_message="Job angelegt, noch nicht gestartet.",
            tags=[tag for tag in (tags or []) if tag],
        )
        self._job_store.save_job(job)
        return job

    def restart_job(self, job_id: str) -> RolloutJob:
        job = self.get_job(job_id)
        job.status = RolloutStatus.PLANNED
        job.progress = 0
        job.client_stage = "Neustart vorbereitet"
        job.client_message = "Job wurde zur erneuten Ausfuehrung zurueckgesetzt."
        job.client_updated_at = time()
        self._job_store.save_job(job)
        return job

    def record_control_action(self, job_id: str, action: str) -> RolloutJob:
        job = self.get_job(job_id)
        normalized_action = action.strip().upper()
        if normalized_action == "ASSIGN":
            job.set_name_requested()
            job.client_stage = "Assign gesendet"
            job.client_message = "Warte auf ACK vom WinPE-Client"
            job.update_status(RolloutStatus.WAITING_REGISTRATION, max(job.progress, 5))
        elif normalized_action == "RESUME":
            job.client_stage = "Resume gesendet"
            job.client_message = "Warte auf ACK vom WinPE-Client"
            job.update_status(RolloutStatus.ROLLOUT_RUNNING, max(job.progress, 55))
        else:
            job.client_stage = f"Control {normalized_action}"
            job.client_message = f"Steuerkommando {normalized_action} gesendet"
        job.client_updated_at = time()
        self._job_store.save_job(job)
        return job

    def sync_job_from_runtime(self, job_id: str, snapshot: dict[str, Any]) -> dict[str, Any]:
        job = self.get_job(job_id)
        before = deepcopy(job.to_dict())

        runtime = snapshot.get("runtime", snapshot)
        status_payload = runtime.get("status") or {}
        ack_payload = runtime.get("ack") or {}

        runtime_mac = str(runtime.get("clientMac", "")).strip()
        if runtime_mac and runtime_mac != job.client_mac:
            job.client_mac = runtime_mac

        runtime_machine_uuid = str(status_payload.get("MACHINE_UUID") or ack_payload.get("MACHINE_UUID") or "").strip()
        if runtime_machine_uuid and runtime_machine_uuid != job.machine_uuid:
            job.machine_uuid = runtime_machine_uuid

        if ack_payload.get("_mtime"):
            job.client_updated_at = float(ack_payload["_mtime"])

        if ack_payload:
            ack_action = str(ack_payload.get("ACTION", "ACK")).strip().upper() or "ACK"
            job.client_stage = f"ACK {ack_action}"
            job.client_message = "Client hat Steuerkommando bestaetigt"
            if ack_action == "ASSIGN":
                job.update_status(RolloutStatus.WAITING_REGISTRATION, max(job.progress, 10))
            elif ack_action == "RESUME":
                job.update_status(RolloutStatus.ROLLOUT_RUNNING, max(job.progress, 55))

        if status_payload:
            stage = str(status_payload.get("STAGE", "")).strip()
            state = str(status_payload.get("STATE", "")).strip().upper()
            message = str(status_payload.get("MESSAGE", "")).strip()
            progress_raw = str(status_payload.get("PROGRESS", "")).strip()
            serial_number = str(status_payload.get("SERIAL_NUMBER", "")).strip()

            if status_payload.get("_mtime"):
                job.client_updated_at = float(status_payload["_mtime"])

            if stage:
                job.client_stage = stage
            elif state:
                job.client_stage = state
            if message:
                job.client_message = message
            if serial_number and serial_number != job.serial_number:
                job.set_registration(serial_number)

            if progress_raw:
                try:
                    job.progress = max(0, min(100, int(progress_raw)))
                except ValueError:
                    pass

            next_status = self._status_from_runtime(state, job.progress)
            job.update_status(next_status, job.progress)

        changed = before != job.to_dict()
        if changed:
            self._job_store.save_job(job)

        return {"job": job, "changed": changed}

    def sync_all_jobs_from_runtime(self, snapshots: dict[str, dict[str, Any]]) -> dict[str, Any]:
        changed_jobs: list[str] = []
        for job in self.list_jobs():
            snapshot = snapshots.get(job.job_id)
            if not snapshot:
                continue
            result = self.sync_job_from_runtime(job.job_id, snapshot)
            if result["changed"]:
                changed_jobs.append(job.job_id)
        return {"changedJobs": changed_jobs, "changedCount": len(changed_jobs)}

    @staticmethod
    def _status_from_runtime(state: str, progress: int) -> RolloutStatus:
        normalized_state = state.strip().upper()
        if normalized_state in {"REGISTERED", "REGISTRATION", "ASSIGNED"}:
            return RolloutStatus.WAITING_REGISTRATION
        if normalized_state in {"DONE", "FINISHED"}:
            return RolloutStatus.SYSPREP_FINISHED
        if normalized_state in {"ERROR", "FAILED", "FAIL"}:
            return RolloutStatus.ERROR
        if normalized_state in {"WAITING", "REGISTERED", "REGISTRATION", "WAITING_REGISTRATION"}:
            return RolloutStatus.WAITING_REGISTRATION
        if progress >= 80:
            return RolloutStatus.SYSPREP
        if progress >= 55 or normalized_state in {"RUNNING", "ROLLOUT", "ROLLOUT_RUNNING"}:
            return RolloutStatus.ROLLOUT_RUNNING
        if progress >= 40 or normalized_state in {"BOOT", "BOOTING", "POWERED_ON"}:
            return RolloutStatus.BOOTING
        if progress > 0 or normalized_state in {"CLONE", "CREATING", "CLONE_CREATING"}:
            return RolloutStatus.CLONE_CREATING
        return RolloutStatus.PLANNED

    def _next_job_id(self) -> str:
        max_value = 0
        for job in self.list_jobs():
            match = re.match(r"^JOB-(\d+)$", job.job_id)
            if match:
                max_value = max(max_value, int(match.group(1)))
        return f"JOB-{max_value + 1:04d}"