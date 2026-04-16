from __future__ import annotations

import re
from collections import Counter
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
        self._job_store.save_job(job)
        return job

    def _next_job_id(self) -> str:
        max_value = 0
        for job in self.list_jobs():
            match = re.match(r"^JOB-(\d+)$", job.job_id)
            if match:
                max_value = max(max_value, int(match.group(1)))
        return f"JOB-{max_value + 1:04d}"