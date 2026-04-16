from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_DIR / "data" / "logs" / "app.log") if (PROJECT_DIR / "data" / "logs").exists() else logging.NullHandler(),
    ],
)
logger = logging.getLogger("admin-startpage")

from app.services.ad_service import ADService, ADServiceError, create_from_settings
from app.services.audit_service import AuditService, create_audit_service
from app.services.auth_service import ADAuthService, ADIdentity, AuthenticationError
from app.services.connector_client import ConnectorClient
from app.services.dashboard_store import DashboardStore
from app.services.integration_service import IntegrationService
from app.services.permission_service import PermissionService, UserSession
from app.services.rollout_execution_service import RolloutExecutionService
from app.services.rollout_job_store import RolloutJobStore
from app.services.rollout_runtime_service import RolloutRuntimeService
from app.services.rollout_service import RolloutService
from app.settings import AppSettings


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class DashboardPayload(BaseModel):
    headline: str = "Meine Admin Startseite"
    widgets: list[dict[str, Any]] = Field(default_factory=list)


class RolloutJobCreateRequest(BaseModel):
    hostname: str = Field(min_length=1)
    template: str = Field(min_length=1)
    cluster: str = Field(min_length=1)
    network: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)


class RolloutControlRequest(BaseModel):
    action: str = Field(min_length=1)


class StoredSession(BaseModel):
    token: str
    expires_at: datetime
    session: dict[str, Any]


APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parents[1]
STATIC_DIR = APP_DIR / "static"
CONFIG_DIR = APP_DIR / "config"
DATA_DIR = PROJECT_DIR / "data" / "users"

settings = AppSettings.from_environment()
started_at = datetime.now(timezone.utc)

# Audit logging
audit_service = create_audit_service()

ROLLOUT_TASKS_DIR = Path(settings.rollout_tasks_dir) if settings.rollout_tasks_dir else PROJECT_DIR / "data" / "rollout-jobs"
ROLLOUT_NAME_MAP_DIR = Path(settings.rollout_name_map_dir) if settings.rollout_name_map_dir else None
ROLLOUT_CONTROL_DIR = Path(settings.rollout_control_dir) if settings.rollout_control_dir else None
ROLLOUT_STATUS_DIR = Path(settings.rollout_status_dir) if settings.rollout_status_dir else None

auth_service = ADAuthService(
    ldap_server=settings.ldap_server,
    base_dn=settings.ldap_base_dn,
    domain_suffix=settings.ldap_domain_suffix,
    enable_mock_auth=settings.mock_auth_enabled,
    mock_groups=settings.mock_groups,
)
permission_service = PermissionService(CONFIG_DIR)
dashboard_store = DashboardStore(DATA_DIR)
connector_client = ConnectorClient(
    base_url=settings.connector_url,
    enabled=settings.connector_enabled,
    timeout=settings.connector_timeout_seconds,
)
integration_service = IntegrationService(
    CONFIG_DIR / "integrations.json",
    permission_service,
    connector_client,
    mock_enabled=settings.mock_integrations_enabled,
)
rollout_job_store = RolloutJobStore(ROLLOUT_TASKS_DIR)
rollout_service = RolloutService(rollout_job_store)
rollout_execution_service = RolloutExecutionService(
    integrations_config_path=CONFIG_DIR / "integrations.json",
    job_store=rollout_job_store,
    mock_enabled=settings.mock_integrations_enabled,
    mock_step_delay_seconds=settings.rollout_mock_step_delay_seconds,
)
rollout_runtime_service = RolloutRuntimeService(
    name_map_dir=ROLLOUT_NAME_MAP_DIR,
    control_dir=ROLLOUT_CONTROL_DIR,
    status_dir=ROLLOUT_STATUS_DIR,
    job_store=rollout_job_store,
)
session_ttl = settings.session_ttl_minutes
sessions: dict[str, StoredSession] = {}

app = FastAPI(title="Admin Startpage", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


def _prune_expired_sessions() -> None:
    now = datetime.now(timezone.utc)
    expired = [token for token, payload in sessions.items() if payload.expires_at <= now]
    for token in expired:
        sessions.pop(token, None)
        logger.info(f"Session expired and removed: {token[:8]}...")


def _get_session(session_token: str | None) -> StoredSession:
    _prune_expired_sessions()
    if not session_token:
        logger.warning("Session token missing in request")
        raise HTTPException(status_code=401, detail="Session-Token fehlt.")
    payload = sessions.get(session_token)
    if payload is None:
        logger.warning(f"Invalid or expired session token: {session_token[:8] if session_token else 'None'}...")
        raise HTTPException(status_code=401, detail="Session ungueltig oder abgelaufen.")
    return payload


def _delete_session(session_token: str | None) -> None:
    if not session_token:
        return
    sessions.pop(session_token, None)


def _session_response(user_session: UserSession) -> dict[str, Any]:
    return {
        "username": user_session.identity.username,
        "displayName": user_session.identity.display_name,
        "email": user_session.identity.email,
        "distinguishedName": user_session.identity.distinguished_name,
        "adGroups": sorted(user_session.identity.ad_groups),
        "roles": sorted(user_session.roles),
        "permissions": sorted(user_session.permissions),
        "modules": permission_service.visible_modules(user_session.permissions),
    }


def _build_user_session(stored_session: StoredSession) -> UserSession:
    identity_data = stored_session.session["identity"]
    identity = ADIdentity(
        username=str(identity_data["username"]),
        distinguished_name=str(identity_data["distinguished_name"]),
        display_name=str(identity_data["display_name"]),
        email=str(identity_data["email"]),
        ad_groups=frozenset(identity_data.get("ad_groups", [])),
    )
    return UserSession(
        identity=identity,
        roles=frozenset(stored_session.session["roles"]),
        permissions=frozenset(stored_session.session["permissions"]),
        session_id=stored_session.session["session_id"],
        login_time=datetime.fromisoformat(stored_session.session["login_time"]),
    )


def _require_permission(user_session: UserSession, permission: str) -> None:
    if not permission_service.has_permission(user_session.permissions, permission):
        raise HTTPException(status_code=403, detail=f"Berechtigung fehlt: {permission}")


@app.get("/api/health")
def health() -> dict[str, Any]:
    connector_status = connector_client.status()
    warnings = settings.runtime_warnings()
    return {
        "status": "ok" if not warnings else "degraded",
        "mockAuth": settings.mock_auth_enabled,
        "mockIntegrations": settings.mock_integrations_enabled,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "startedAt": started_at.isoformat(),
        "activeSessions": len(sessions),
        "allowedOrigins": list(settings.allowed_origins),
        "warnings": warnings,
        "connectorMode": "windows-connector-required-for-rsat-and-citrix-automation",
        "connector": connector_status,
    }


@app.post("/api/auth/login")
def login(payload: LoginRequest) -> dict[str, Any]:
    logger.info(f"Login attempt for user: {payload.username}")
    try:
        identity = auth_service.authenticate(payload.username, payload.password)
    except AuthenticationError as exc:
        logger.warning(f"Login failed for {payload.username}: {exc}")
        audit_service.log_login(payload.username, success=False)
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user_session = permission_service.build_session(identity)
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=session_ttl)
    sessions[token] = StoredSession(
        token=token,
        expires_at=expires_at,
        session={
            "identity": {
                "username": user_session.identity.username,
                "distinguished_name": user_session.identity.distinguished_name,
                "display_name": user_session.identity.display_name,
                "email": user_session.identity.email,
                "ad_groups": sorted(user_session.identity.ad_groups),
            },
            "roles": list(user_session.roles),
            "permissions": list(user_session.permissions),
            "session_id": user_session.session_id,
            "login_time": user_session.login_time.isoformat(),
            "auth_password": payload.password,
        },
    )
    logger.info(f"User {payload.username} logged in successfully, session: {token[:8]}...")
    
    # Audit logging
    audit_service.log_login(user_session.identity.username, success=True)

    return {
        "sessionToken": token,
        "expiresAt": expires_at.isoformat(),
        "user": _session_response(user_session),
        "dashboard": dashboard_store.load(user_session.identity.username),
    }


@app.post("/api/auth/logout")
def logout(x_session_token: str | None = Header(default=None)) -> dict[str, bool]:
    username = "unknown"
    if x_session_token:
        stored = sessions.get(x_session_token)
        if stored:
            username = stored.session.get("identity", {}).get("username", "unknown")
            logger.info(f"User {username} logging out, session: {x_session_token[:8]}...")
            audit_service.log_logout(username)
    _delete_session(x_session_token)
    return {"loggedOut": True}


@app.post("/api/auth/refresh")
def refresh_session(x_session_token: str | None = Header(default=None)) -> dict[str, Any]:
    """Refresh session TTL for active sessions."""
    stored_session = _get_session(x_session_token)
    # Extend session
    stored_session.expires_at = datetime.now(timezone.utc) + timedelta(minutes=session_ttl)
    username = stored_session.session.get("identity", {}).get("username", "unknown")
    logger.info(f"Session refreshed for user {username}")
    return {
        "refreshed": True,
        "expiresAt": stored_session.expires_at.isoformat(),
        "expiresInSeconds": session_ttl * 60,
    }


@app.get("/api/me")
def current_user(x_session_token: str | None = Header(default=None)) -> dict[str, Any]:
    stored_session = _get_session(x_session_token)
    user_session = _build_user_session(stored_session)
    dashboard = dashboard_store.load(user_session.identity.username)
    expires_in_seconds = max(
        0,
        int((stored_session.expires_at - datetime.now(timezone.utc)).total_seconds()),
    )
    return {
        "user": _session_response(user_session),
        "dashboard": dashboard,
        "expiresAt": stored_session.expires_at.isoformat(),
        "expiresInSeconds": expires_in_seconds,
    }


@app.put("/api/me/dashboard")
def update_dashboard(
    payload: DashboardPayload,
    x_session_token: str | None = Header(default=None),
) -> dict[str, Any]:
    stored_session = _get_session(x_session_token)
    username = str(stored_session.session["identity"]["username"])
    dashboard_store.save(username, payload.model_dump())
    return {"saved": True, "dashboard": dashboard_store.load(username)}


@app.get("/api/integrations/overview")
def integrations_overview(x_session_token: str | None = Header(default=None)) -> dict[str, Any]:
    stored_session = _get_session(x_session_token)
    user_session = _build_user_session(stored_session)
    items = integration_service.overview(
        user_session,
        session_password=str(stored_session.session.get("auth_password", "")),
    )
    return {"systems": items}


@app.get("/api/integrations/{system_id}")
def integration_detail(system_id: str, x_session_token: str | None = Header(default=None)) -> dict[str, Any]:
    stored_session = _get_session(x_session_token)
    user_session = _build_user_session(stored_session)
    permission_map = {
        "ad": "ad.view",
        "nutanix": "nutanix.view",
        "endpoint": "endpoint.view",
        "vsphere": "vsphere.view",
        "citrix": "citrix.view",
        "rollout": "rollout.view",
    }
    required_permission = permission_map.get(system_id)
    if required_permission:
        _require_permission(user_session, required_permission)
    try:
        system = integration_service.details(
            system_id,
            user_session,
            session_password=str(stored_session.session.get("auth_password", "")),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unbekanntes System: {system_id}") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return system


@app.get("/api/connector/status")
def connector_status() -> dict[str, Any]:
    return connector_client.status()


@app.get("/api/rollout/jobs")
def rollout_jobs(x_session_token: str | None = Header(default=None)) -> dict[str, Any]:
    stored_session = _get_session(x_session_token)
    user_session = _build_user_session(stored_session)
    _require_permission(user_session, "rollout.view")
    jobs = [job.to_api() for job in rollout_service.list_jobs()]
    return {"jobs": jobs, "summary": rollout_service.summary(), "runtime": rollout_runtime_service.health()}


@app.post("/api/rollout/jobs")
def create_rollout_job(payload: RolloutJobCreateRequest, x_session_token: str | None = Header(default=None)) -> dict[str, Any]:
    stored_session = _get_session(x_session_token)
    user_session = _build_user_session(stored_session)
    _require_permission(user_session, "rollout.create")
    try:
        job = rollout_service.create_job(
            hostname=payload.hostname,
            template=payload.template,
            cluster=payload.cluster,
            network=payload.network,
            created_by=user_session.identity.username,
            tags=[tag.strip() for tag in payload.tags if tag.strip()],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"job": job.to_api(), "summary": rollout_service.summary()}


@app.post("/api/rollout/jobs/{job_id}/start")
def start_rollout_job(job_id: str, x_session_token: str | None = Header(default=None)) -> dict[str, Any]:
    stored_session = _get_session(x_session_token)
    user_session = _build_user_session(stored_session)
    _require_permission(user_session, "rollout.manage")
    try:
        job = rollout_service.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unbekannter Rollout-Job: {job_id}") from exc
    result = rollout_execution_service.start_job(
        job,
        username=user_session.identity.username,
        password=str(stored_session.session.get("auth_password", "")),
    )
    if not result["started"]:
        raise HTTPException(status_code=409, detail=result["message"])
    return {**result, "job": rollout_service.get_job(job_id).to_api(), "summary": rollout_service.summary()}


@app.get("/api/rollout/jobs/{job_id}")
def rollout_job_detail(job_id: str, x_session_token: str | None = Header(default=None)) -> dict[str, Any]:
    stored_session = _get_session(x_session_token)
    user_session = _build_user_session(stored_session)
    _require_permission(user_session, "rollout.view")
    try:
        job = rollout_service.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unbekannter Rollout-Job: {job_id}") from exc
    return {"job": job.to_api()}


@app.get("/api/rollout/runtime/health")
def rollout_runtime_health(x_session_token: str | None = Header(default=None)) -> dict[str, Any]:
    stored_session = _get_session(x_session_token)
    user_session = _build_user_session(stored_session)
    _require_permission(user_session, "rollout.view")
    return rollout_runtime_service.health()


@app.get("/api/rollout/jobs/{job_id}/runtime")
def rollout_job_runtime(job_id: str, x_session_token: str | None = Header(default=None)) -> dict[str, Any]:
    stored_session = _get_session(x_session_token)
    user_session = _build_user_session(stored_session)
    _require_permission(user_session, "rollout.view")
    try:
        job = rollout_service.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unbekannter Rollout-Job: {job_id}") from exc
    return {"runtime": rollout_runtime_service.snapshot_for_job(job)}


@app.post("/api/rollout/jobs/{job_id}/sync")
def rollout_job_sync(job_id: str, x_session_token: str | None = Header(default=None)) -> dict[str, Any]:
    stored_session = _get_session(x_session_token)
    user_session = _build_user_session(stored_session)
    _require_permission(user_session, "rollout.manage")
    try:
        job = rollout_service.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unbekannter Rollout-Job: {job_id}") from exc
    snapshot = rollout_runtime_service.snapshot_for_job(job)
    result = rollout_service.sync_job_from_runtime(job_id, snapshot)
    return {"job": result["job"].to_api(), "changed": result["changed"], "summary": rollout_service.summary()}


@app.post("/api/rollout/jobs/sync")
def rollout_jobs_sync(x_session_token: str | None = Header(default=None)) -> dict[str, Any]:
    stored_session = _get_session(x_session_token)
    user_session = _build_user_session(stored_session)
    _require_permission(user_session, "rollout.manage")
    snapshots: dict[str, dict[str, Any]] = {}
    for job in rollout_service.list_jobs():
        snapshots[job.job_id] = rollout_runtime_service.snapshot_for_job(job)
    sync_result = rollout_service.sync_all_jobs_from_runtime(snapshots)
    jobs = [job.to_api() for job in rollout_service.list_jobs()]
    return {"jobs": jobs, "summary": rollout_service.summary(), "sync": sync_result}


@app.post("/api/rollout/jobs/{job_id}/control")
def rollout_job_control(
    job_id: str,
    payload: RolloutControlRequest,
    x_session_token: str | None = Header(default=None),
) -> dict[str, Any]:
    stored_session = _get_session(x_session_token)
    user_session = _build_user_session(stored_session)
    _require_permission(user_session, "rollout.manage")
    try:
        job = rollout_service.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unbekannter Rollout-Job: {job_id}") from exc
    result = rollout_runtime_service.write_control_message(job=job, action=payload.action)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["message"])
    updated_job = rollout_service.record_control_action(job_id, payload.action)
    return {**result, "job": updated_job.to_api(), "summary": rollout_service.summary()}


@app.post("/api/rollout/jobs/{job_id}/restart")
def restart_rollout_job(job_id: str, x_session_token: str | None = Header(default=None)) -> dict[str, Any]:
    stored_session = _get_session(x_session_token)
    user_session = _build_user_session(stored_session)
    _require_permission(user_session, "rollout.manage")
    try:
        job = rollout_service.restart_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unbekannter Rollout-Job: {job_id}") from exc
    return {"job": job.to_api(), "summary": rollout_service.summary()}


@app.delete("/api/rollout/jobs/{job_id}")
def delete_rollout_job(
    job_id: str,
    hard_delete: bool = False,
    x_session_token: str | None = Header(default=None),
) -> dict[str, Any]:
    """Delete a rollout job. Use hard_delete=true for permanent removal."""
    stored_session = _get_session(x_session_token)
    user_session = _build_user_session(stored_session)
    _require_permission(user_session, "rollout.manage")
    try:
        result = rollout_service.delete_job(job_id, hard_delete=hard_delete)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unbekannter Rollout-Job: {job_id}") from exc
    return {**result, "summary": rollout_service.summary()}


@app.post("/api/rollout/jobs/{job_id}/rerollout")
def rerollout_rollout_job(job_id: str, x_session_token: str | None = Header(default=None)) -> dict[str, Any]:
    """Create a new rollout job based on an existing job (Re-Rollout)."""
    stored_session = _get_session(x_session_token)
    user_session = _build_user_session(stored_session)
    _require_permission(user_session, "rollout.create")
    try:
        new_job = rollout_service.rerollout_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unbekannter Rollout-Job: {job_id}") from exc
    return {"job": new_job.to_api(), "originalJobId": job_id, "summary": rollout_service.summary()}


# Active Directory endpoints
def _get_ad_service() -> ADService | None:
    """Create AD service instance if LDAP is configured."""
    if settings.mock_auth_enabled:
        return None  # No real AD in mock mode
    if not all([settings.ldap_server, settings.ldap_base_dn]):
        return None
    return create_from_settings(
        ldap_server=settings.ldap_server,
        base_dn=settings.ldap_base_dn,
    )


@app.get("/api/ad/users")
def ad_users(
    search: str = "",
    limit: int = 50,
    x_session_token: str | None = Header(default=None),
) -> dict[str, Any]:
    """Search AD users."""
    stored_session = _get_session(x_session_token)
    user_session = _build_user_session(stored_session)
    _require_permission(user_session, "ad.view")
    
    ad_service = _get_ad_service()
    if ad_service is None:
        return {"users": [], "mode": "mock", "message": "AD in Mock-Modus"}
    
    try:
        ad_service.connect()
        filter_str = f"(&(objectClass=user)(sAMAccountName=*{search}*))" if search else "(objectClass=user)"
        users = ad_service.search_users(search_filter=filter_str, limit=limit)
        ad_service.disconnect()
        return {"users": [u.__dict__ for u in users], "mode": "live", "count": len(users)}
    except ADServiceError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/ad/computers")
def ad_computers(
    search: str = "",
    limit: int = 50,
    x_session_token: str | None = Header(default=None),
) -> dict[str, Any]:
    """Search AD computers."""
    stored_session = _get_session(x_session_token)
    user_session = _build_user_session(stored_session)
    _require_permission(user_session, "ad.view")
    
    ad_service = _get_ad_service()
    if ad_service is None:
        return {"computers": [], "mode": "mock", "message": "AD in Mock-Modus"}
    
    try:
        ad_service.connect()
        filter_str = f"(&(objectClass=computer)(name=*{search}*))" if search else "(objectClass=computer)"
        computers = ad_service.search_computers(search_filter=filter_str, limit=limit)
        ad_service.disconnect()
        return {"computers": [c.__dict__ for c in computers], "mode": "live", "count": len(computers)}
    except ADServiceError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/ad/groups")
def ad_groups(
    search: str = "",
    limit: int = 50,
    x_session_token: str | None = Header(default=None),
) -> dict[str, Any]:
    """Search AD groups."""
    stored_session = _get_session(x_session_token)
    user_session = _build_user_session(stored_session)
    _require_permission(user_session, "ad.view")
    
    ad_service = _get_ad_service()
    if ad_service is None:
        return {"groups": [], "mode": "mock", "message": "AD in Mock-Modus"}
    
    try:
        ad_service.connect()
        filter_str = f"(&(objectClass=group)(cn=*{search}*))" if search else "(objectClass=group)"
        groups = ad_service.search_groups(search_filter=filter_str, limit=limit)
        ad_service.disconnect()
        return {"groups": [g.__dict__ for g in groups], "mode": "live", "count": len(groups)}
    except ADServiceError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/ad/ous")
def ad_ous(x_session_token: str | None = Header(default=None)) -> dict[str, Any]:
    """Get Organizational Units from AD."""
    stored_session = _get_session(x_session_token)
    user_session = _build_user_session(stored_session)
    _require_permission(user_session, "ad.view")
    
    ad_service = _get_ad_service()
    if ad_service is None:
        return {"ous": [], "mode": "mock"}
    
    try:
        ad_service.connect()
        ous = ad_service.get_ous()
        ad_service.disconnect()
        return {"ous": [o.__dict__ for o in ous], "mode": "live", "count": len(ous)}
    except ADServiceError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# Citrix On-Prem endpoints (via Connector)
@app.get("/api/citrix/summary")
def citrix_summary(x_session_token: str | None = Header(default=None)) -> dict[str, Any]:
    """Get Citrix farm summary via Windows Connector."""
    stored_session = _get_session(x_session_token)
    user_session = _build_user_session(stored_session)
    _require_permission(user_session, "citrix.view")
    
    result = connector_client.citrix_summary()
    if result is None:
        return {
            "machines": [],
            "mode": "mock",
            "message": "Citrix via Connector nicht verfuegbar. Verwende Mock-Daten.",
            "connectorEnabled": connector_client.enabled,
        }
    return result


@app.get("/api/citrix/machines")
def citrix_machines(x_session_token: str | None = Header(default=None)) -> dict[str, Any]:
    """Get Citrix machines via Windows Connector."""
    stored_session = _get_session(x_session_token)
    user_session = _build_user_session(stored_session)
    _require_permission(user_session, "citrix.view")
    
    result = connector_client.citrix_machines()
    if result is None:
        return {"machines": [], "mode": "mock"}
    return result


@app.get("/api/citrix/delivery-groups")
def citrix_delivery_groups(x_session_token: str | None = Header(default=None)) -> dict[str, Any]:
    """Get Citrix Delivery Groups via Windows Connector."""
    stored_session = _get_session(x_session_token)
    user_session = _build_user_session(stored_session)
    _require_permission(user_session, "citrix.view")
    
    result = connector_client.citrix_delivery_groups()
    if result is None:
        return {"deliveryGroups": [], "mode": "mock"}
    return result


@app.post("/api/citrix/machines/{machine_name}/maintenance")
def citrix_set_maintenance(
    machine_name: str,
    enabled: bool,
    x_session_token: str | None = Header(default=None),
) -> dict[str, Any]:
    """Enable/disable maintenance mode for a Citrix machine."""
    stored_session = _get_session(x_session_token)
    user_session = _build_user_session(stored_session)
    _require_permission(user_session, "citrix.manage")
    
    result = connector_client.citrix_set_maintenance(machine_name, enabled)
    if result is None:
        raise HTTPException(status_code=503, detail="Citrix Connector nicht verfuegbar")
    return result


@app.get("/")
def root() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
