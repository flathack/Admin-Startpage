from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from .rollout_models import RolloutJob


class RolloutJobStore:
    def __init__(self, tasks_dir: Path) -> None:
        self._tasks_dir = tasks_dir

    @property
    def tasks_dir(self) -> Path:
        return self._tasks_dir

    def ensure_directory(self) -> None:
        self._tasks_dir.mkdir(parents=True, exist_ok=True)

    def load_jobs(self) -> list[RolloutJob]:
        self.ensure_directory()
        jobs: list[RolloutJob] = []
        for file_path in sorted(self._tasks_dir.glob("*.json")):
            try:
                payload = json.loads(file_path.read_text(encoding="utf-8"))
                jobs.append(RolloutJob.from_dict(payload))
            except Exception:
                continue
        return jobs

    def save_job(self, job: RolloutJob) -> None:
        self.ensure_directory()
        target = self._tasks_dir / f"{job.job_id}.json"
        temp = self._tasks_dir / f".{job.job_id}.{uuid.uuid4().hex}.tmp"
        temp.write_text(json.dumps(job.to_dict(), ensure_ascii=True, indent=2), encoding="utf-8")
        os.replace(temp, target)

    def delete_job(self, job_id: str) -> None:
        self.ensure_directory()
        target = self._tasks_dir / f"{job_id}.json"
        if target.exists():
            target.unlink()
