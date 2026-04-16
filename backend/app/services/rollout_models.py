from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from time import time
from typing import Any


class RolloutStatus(str, Enum):
    PLANNED = "Geplant"
    CLONE_CREATING = "Klon wird erstellt"
    BOOTING = "Klon bootet"
    WAITING_REGISTRATION = "Wartet auf Registrierung"
    ROLLOUT_RUNNING = "Rollout laeuft"
    SYSPREP = "Sysprep"
    SYSPREP_FINISHED = "Sysprep abgeschlossen"
    DELETED = "Geloescht"
    ERROR = "Fehler"


@dataclass
class RolloutJob:
    job_id: str
    hostname: str
    template: str
    cluster: str
    network: str
    created_by: str = ""
    bootstrap_name: str = ""
    status: RolloutStatus = RolloutStatus.PLANNED
    progress: int = 0
    client_mac: str = ""
    machine_uuid: str = ""
    client_stage: str = ""
    client_message: str = ""
    created_at: float = field(default_factory=time)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        created_at_iso = datetime.fromtimestamp(self.created_at, tz=timezone.utc).isoformat()
        return {
            "job_id": self.job_id,
            "hostname": self.hostname,
            "template": self.template,
            "cluster": self.cluster,
            "network": self.network,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "created_at_iso": created_at_iso,
            "bootstrap_name": self.bootstrap_name,
            "status": self.status.value,
            "progress": self.progress,
            "client_mac": self.client_mac,
            "machine_uuid": self.machine_uuid,
            "client_stage": self.client_stage,
            "client_message": self.client_message,
            "tags": list(self.tags),
        }

    def to_api(self) -> dict[str, Any]:
        return {
            "jobId": self.job_id,
            "hostname": self.hostname,
            "template": self.template,
            "cluster": self.cluster,
            "network": self.network,
            "createdBy": self.created_by,
            "createdAt": datetime.fromtimestamp(self.created_at, tz=timezone.utc).isoformat(),
            "bootstrapName": self.bootstrap_name,
            "status": self.status.value,
            "progress": self.progress,
            "clientMac": self.client_mac,
            "machineUuid": self.machine_uuid,
            "clientStage": self.client_stage,
            "clientMessage": self.client_message,
            "tags": list(self.tags),
        }

    @staticmethod
    def _parse_status(value: str) -> RolloutStatus:
        raw = str(value or "").strip()
        if not raw:
            return RolloutStatus.PLANNED
        try:
            return RolloutStatus(raw)
        except ValueError:
            normalized = raw.casefold()
            aliases = {
                "geplant": RolloutStatus.PLANNED,
                "klon wird erstellt": RolloutStatus.CLONE_CREATING,
                "klon bootet": RolloutStatus.BOOTING,
                "wartet auf registrierung": RolloutStatus.WAITING_REGISTRATION,
                "rollout laeuft": RolloutStatus.ROLLOUT_RUNNING,
                "rollout läuft": RolloutStatus.ROLLOUT_RUNNING,
                "sysprep": RolloutStatus.SYSPREP,
                "sysprep abgeschlossen": RolloutStatus.SYSPREP_FINISHED,
                "geloescht": RolloutStatus.DELETED,
                "gelöscht": RolloutStatus.DELETED,
                "fehler": RolloutStatus.ERROR,
            }
            return aliases.get(normalized, RolloutStatus.PLANNED)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RolloutJob":
        return cls(
            job_id=str(payload.get("job_id", "")).strip(),
            hostname=str(payload.get("hostname", "")).strip(),
            template=str(payload.get("template", "")).strip(),
            cluster=str(payload.get("cluster", "")).strip(),
            network=str(payload.get("network", "")).strip(),
            created_by=str(payload.get("created_by", "")).strip(),
            bootstrap_name=str(payload.get("bootstrap_name", payload.get("hostname", ""))).strip(),
            status=cls._parse_status(str(payload.get("status", RolloutStatus.PLANNED.value))),
            progress=max(0, min(100, int(payload.get("progress", 0)))),
            client_mac=str(payload.get("client_mac", "")).strip(),
            machine_uuid=str(payload.get("machine_uuid", "")).strip(),
            client_stage=str(payload.get("client_stage", "")).strip(),
            client_message=str(payload.get("client_message", "")).strip(),
            created_at=float(payload.get("created_at", time())),
            tags=[str(tag).strip() for tag in payload.get("tags", []) if str(tag).strip()],
        )
