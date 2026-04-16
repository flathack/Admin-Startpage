from __future__ import annotations

import glob
import os
import re
from pathlib import Path
from time import time
from typing import Any

from .rollout_job_store import RolloutJobStore
from .rollout_models import RolloutJob


class RolloutRuntimeService:
    def __init__(
        self,
        *,
        name_map_dir: Path | None,
        control_dir: Path | None,
        status_dir: Path | None,
        job_store: RolloutJobStore,
    ) -> None:
        self._name_map_dir = name_map_dir
        self._control_dir = control_dir
        self._status_dir = status_dir
        self._job_store = job_store

    def is_configured(self) -> bool:
        return all((self._name_map_dir, self._control_dir, self._status_dir))

    def health(self) -> dict[str, Any]:
        return {
            "configured": self.is_configured(),
            "nameMapDir": self._dir_state(self._name_map_dir),
            "controlDir": self._dir_state(self._control_dir),
            "statusDir": self._dir_state(self._status_dir),
        }

    def snapshot_for_job(self, job: RolloutJob) -> dict[str, Any]:
        mapping_payload = self._find_mapping_payload(job)
        if mapping_payload:
            mapped_mac = mapping_payload.get("MAC", "").strip()
            if mapped_mac and mapped_mac != job.client_mac:
                job.client_mac = mapped_mac
                self._job_store.save_job(job)

        return {
            "jobId": job.job_id,
            "configured": self.is_configured(),
            "clientMac": job.client_mac,
            "mapping": mapping_payload,
            "status": self._latest_payload(self.status_candidates_for_job(job)),
            "ack": self._latest_payload(self.ack_candidates_for_job(job)),
            "statusCandidates": self.status_candidates_for_job(job),
            "ackCandidates": self.ack_candidates_for_job(job),
        }

    def write_control_message(self, *, job: RolloutJob, action: str) -> dict[str, Any]:
        if not self._control_dir:
            return {"ok": False, "message": "CONTROL-Verzeichnis ist nicht konfiguriert.", "writtenFiles": []}
        if not job.client_mac.strip():
            return {"ok": False, "message": "Kein gueltiger Zielschluessel vorhanden. MAC fehlt.", "writtenFiles": []}

        self._control_dir.mkdir(parents=True, exist_ok=True)
        path = self.control_file_path("MAC", job.client_mac)
        if path is None:
            return {"ok": False, "message": "Control-Dateipfad konnte nicht erzeugt werden.", "writtenFiles": []}

        payload = (
            f"ACTION={action.strip().upper()}\n"
            f"JOB_ID={job.job_id}\n"
            f"MAC={job.client_mac}\n"
            f"HOSTNAME={job.hostname}\n"
            f"BOOTSTRAP={job.bootstrap_name}\n"
            f"TIMESTAMP={int(time())}\n"
        )
        temp_path = path.with_suffix(path.suffix + ".tmp")
        try:
            temp_path.write_text(payload, encoding="utf-8")
            os.replace(temp_path, path)
        except OSError as exc:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            return {"ok": False, "message": f"Control-Datei konnte nicht geschrieben werden: {exc}", "writtenFiles": []}

        return {"ok": True, "message": f"Control-Signal '{action.strip().upper()}' geschrieben.", "writtenFiles": [str(path)]}

    def status_candidates_for_job(self, job: RolloutJob) -> list[str]:
        if not self._status_dir or not job.client_mac.strip():
            return []
        path = self.status_file_path("MAC", job.client_mac)
        return [str(path)] if path is not None else []

    def ack_candidates_for_job(self, job: RolloutJob) -> list[str]:
        if not self._control_dir or not job.client_mac.strip():
            return []
        path = self.control_file_path("ACK_MAC", job.client_mac)
        return [str(path)] if path is not None else []

    @staticmethod
    def normalize_mapping_key(value: str) -> str:
        normalized = value.strip().upper()
        return re.sub(r"[^A-Z0-9_.-]", "_", normalized)

    def control_file_path(self, prefix: str, value: str) -> Path | None:
        if not self._control_dir:
            return None
        return self._control_dir / f"{prefix}_{self.normalize_mapping_key(value)}.txt"

    def status_file_path(self, prefix: str, value: str) -> Path | None:
        if not self._status_dir:
            return None
        return self._status_dir / f"{prefix}_{self.normalize_mapping_key(value)}.txt"

    def _find_mapping_payload(self, job: RolloutJob) -> dict[str, Any] | None:
        if not self._name_map_dir:
            return None
        pattern = str(self._name_map_dir / "MAC_*.txt")
        for path_str in glob.glob(pattern):
            path = Path(path_str)
            if not path.is_file():
                continue
            payload = self._read_key_value_file(path)
            if payload.get("HOSTNAME", "").strip().upper() == job.hostname.upper():
                payload["_path"] = str(path)
                return payload
        return None

    def _latest_payload(self, candidates: list[str]) -> dict[str, Any] | None:
        newest_path: Path | None = None
        newest_mtime = -1.0
        for candidate in candidates:
            path = Path(candidate)
            if not path.exists() or not path.is_file():
                continue
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            if mtime > newest_mtime:
                newest_mtime = mtime
                newest_path = path
        if newest_path is None:
            return None
        payload = self._read_key_value_file(newest_path)
        payload["_path"] = str(newest_path)
        payload["_mtime"] = newest_mtime
        return payload

    @staticmethod
    def _read_text_file_best_effort(path: Path) -> str:
        try:
            raw = path.read_bytes()[:65536]
        except OSError:
            return ""
        for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "cp1252", "latin-1"):
            try:
                return raw.decode(encoding).replace("\x00", "")
            except UnicodeDecodeError:
                continue
        return ""

    def _read_key_value_file(self, path: Path) -> dict[str, str]:
        payload: dict[str, str] = {}
        content = self._read_text_file_best_effort(path)
        for line in content.splitlines():
            text = line.strip()
            if not text or "=" not in text:
                continue
            key, value = text.split("=", 1)
            payload[key.strip().upper()] = value.strip()
        return payload

    @staticmethod
    def _dir_state(path: Path | None) -> dict[str, Any]:
        if path is None:
            return {"configured": False, "path": "", "exists": False}
        return {"configured": True, "path": str(path), "exists": path.exists()}
