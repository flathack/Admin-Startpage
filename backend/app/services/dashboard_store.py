from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_DASHBOARD: dict[str, Any] = {
    "headline": "Meine Admin Startseite",
    "widgets": [
        {
            "id": "wiki",
            "title": "Wiki",
            "url": "https://wiki.example.local",
            "category": "Dokumentation",
            "description": "Schneller Zugriff auf Runbooks und Wissensbasis.",
        },
        {
            "id": "prism",
            "title": "Nutanix Prism",
            "url": "https://nutanix.local:9440",
            "category": "Virtualisierung",
            "description": "Cluster, Images und VM-Verwaltung.",
        },
        {
            "id": "endpoint",
            "title": "Endpoint Central",
            "url": "https://endpoint.local",
            "category": "Client Management",
            "description": "Agenten, Inventar und Patch-Status.",
        },
    ],
}


class DashboardStore:
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._data_dir.mkdir(parents=True, exist_ok=True)

    def load(self, username: str) -> dict[str, Any]:
        path = self._path_for_user(username)
        if not path.exists():
            dashboard = deepcopy(DEFAULT_DASHBOARD)
            dashboard["headline"] = f"Startseite von {username}"
            self.save(username, dashboard)
            return dashboard

        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return deepcopy(DEFAULT_DASHBOARD)

    def save(self, username: str, dashboard: dict[str, Any]) -> None:
        sanitized = {
            "headline": str(dashboard.get("headline", "Meine Admin Startseite")),
            "widgets": [self._sanitize_widget(item) for item in dashboard.get("widgets", []) if isinstance(item, dict)],
        }
        self._path_for_user(username).write_text(
            json.dumps(sanitized, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _path_for_user(self, username: str) -> Path:
        safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", username.strip() or "unknown")
        return self._data_dir / f"{safe_name}.json"

    @staticmethod
    def _sanitize_widget(widget: dict[str, Any]) -> dict[str, str]:
        return {
            "id": str(widget.get("id") or widget.get("title") or "widget").strip() or "widget",
            "title": str(widget.get("title", "Neues Widget")).strip() or "Neues Widget",
            "url": str(widget.get("url", "#")).strip() or "#",
            "category": str(widget.get("category", "Allgemein")).strip() or "Allgemein",
            "description": str(widget.get("description", "")).strip(),
        }
