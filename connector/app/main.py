from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field


class SessionContextRequest(BaseModel):
    username: str = Field(min_length=1)
    display_name: str = ""
    email: str = ""
    ad_groups: list[str] = Field(default_factory=list)


app = FastAPI(title="Startpage Windows Connector", version="0.1.0")


@app.get("/health")
def health() -> dict[str, Any]:
    mock_mode = os.getenv("STARTPAGE_CONNECTOR_MOCK", "true").lower() == "true"
    return {
        "status": "ok",
        "mode": "mock" if mock_mode else "live",
        "message": "Windows Connector bereit.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "capabilities": [
            "ad-rsat-session-context",
            "citrix-onprem-summary",
        ],
    }


@app.get("/api/capabilities")
def capabilities() -> dict[str, Any]:
    return health()


@app.post("/api/ad/session-context")
def ad_session_context(payload: SessionContextRequest) -> dict[str, Any]:
    return {
        "source": "connector",
        "username": payload.username,
        "displayName": payload.display_name,
        "email": payload.email,
        "groupCount": len(payload.ad_groups),
        "topGroups": payload.ad_groups[:8],
        "rsatReady": True,
        "message": "Mock-Connector liefert AD-Session-Kontext. Spaeter RSAT-gestuetzte Details.",
    }


@app.get("/api/citrix/summary")
def citrix_summary() -> dict[str, Any]:
    return {
        "source": "connector",
        "status": "ok",
        "message": "Mock-Connector liefert Citrix-On-Prem-Zusammenfassung.",
        "items": [
            {"label": "DDC", "value": os.getenv("STARTPAGE_CITRIX_ADMIN_ADDRESS", "ddc01.local")},
            {"label": "Maschinen online", "value": "24"},
            {"label": "Maintenance an", "value": "2"},
            {"label": "Offene Sessions", "value": "11"}
        ],
        "meta": {
            "connectorMode": "mock",
            "adminAddress": os.getenv("STARTPAGE_CITRIX_ADMIN_ADDRESS", "ddc01.local")
        },
    }
