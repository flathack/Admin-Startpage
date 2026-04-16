"""
Audit Logging Service for Admin Startpage.

Tracks all write operations with:
- Timestamp
- User identity
- Action type
- Resource affected
- Success/failure status
- IP address (if available)
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


logger = logging.getLogger("admin-startpage.audit")


class AuditEventType:
    """Audit event type constants."""
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    LOGIN_FAILED = "LOGIN_FAILED"
    SESSION_REFRESH = "SESSION_REFRESH"
    DASHBOARD_UPDATE = "DASHBOARD_UPDATE"
    ROLLOUT_CREATE = "ROLLOUT_CREATE"
    ROLLOUT_START = "ROLLOUT_START"
    ROLLOUT_STOP = "ROLLOUT_STOP"
    ROLLOUT_DELETE = "ROLLOUT_DELETE"
    ROLLOUT_REROLLOUT = "ROLLOUT_REROLLOUT"
    ROLLOUT_CONTROL = "ROLLOUT_CONTROL"
    ROLLOUT_SYNC = "ROLLOUT_SYNC"
    AD_QUERY = "AD_QUERY"
    CITRIX_ACTION = "CITRIX_ACTION"
    INTEGRATION_ACCESS = "INTEGRATION_ACCESS"


class AuditService:
    """Service for writing audit logs."""
    
    def __init__(self, log_dir: Path | None = None, enabled: bool = True) -> None:
        self._enabled = enabled
        self._log_dir = log_dir
        if self._enabled and self._log_dir:
            self._log_dir.mkdir(parents=True, exist_ok=True)
    
    def is_enabled(self) -> bool:
        return self._enabled
    
    def log_event(
        self,
        event_type: str,
        username: str,
        *,
        success: bool = True,
        resource: str = "",
        details: dict[str, Any] | None = None,
        ip_address: str = "",
    ) -> None:
        """Log an audit event."""
        if not self._enabled:
            return
        
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "username": username,
            "success": success,
            "resource": resource,
            "ip_address": ip_address,
            "details": details or {},
        }
        
        # Log to console/file
        log_message = (
            f"AUDIT: {event_type} | User: {username} | "
            f"Success: {success} | Resource: {resource}"
        )
        
        if success:
            logger.info(log_message)
        else:
            logger.warning(log_message)
        
        # Write to audit file
        if self._log_dir:
            self._write_to_file(event)
    
    def _write_to_file(self, event: dict[str, Any]) -> None:
        """Write audit event to daily log file."""
        if not self._log_dir:
            return
        
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = self._log_dir / f"audit-{date_str}.log"
        
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.error(f"Failed to write audit log: {exc}")
    
    def log_login(self, username: str, success: bool, ip_address: str = "") -> None:
        """Log login attempt."""
        self.log_event(
            AuditEventType.LOGIN if success else AuditEventType.LOGIN_FAILED,
            username,
            success=success,
            resource="auth",
            ip_address=ip_address,
        )
    
    def log_logout(self, username: str) -> None:
        """Log logout."""
        self.log_event(AuditEventType.LOGOUT, username, resource="auth")
    
    def log_rollout_action(
        self,
        username: str,
        action: str,
        job_id: str,
        success: bool,
    ) -> None:
        """Log rollout-related action."""
        event_type_map = {
            "create": AuditEventType.ROLLOUT_CREATE,
            "start": AuditEventType.ROLLOUT_START,
            "stop": AuditEventType.ROLLOUT_STOP,
            "delete": AuditEventType.ROLLOUT_DELETE,
            "rerollout": AuditEventType.ROLLOUT_REROLLOUT,
            "control": AuditEventType.ROLLOUT_CONTROL,
            "sync": AuditEventType.ROLLOUT_SYNC,
        }
        event_type = event_type_map.get(action.lower(), AuditEventType.ROLLOUT_CREATE)
        
        self.log_event(
            event_type,
            username,
            success=success,
            resource=f"rollout:{job_id}",
            details={"action": action, "job_id": job_id},
        )
    
    def log_dashboard_update(self, username: str) -> None:
        """Log dashboard update."""
        self.log_event(
            AuditEventType.DASHBOARD_UPDATE,
            username,
            success=True,
            resource="dashboard",
        )
    
    def log_integration_access(
        self,
        username: str,
        system: str,
    ) -> None:
        """Log integration access."""
        self.log_event(
            AuditEventType.INTEGRATION_ACCESS,
            username,
            success=True,
            resource=f"integration:{system}",
        )


def create_audit_service() -> AuditService:
    """Create audit service from environment settings."""
    enabled = os.getenv("STARTPAGE_AUDIT_LOG_ENABLED", "true").lower() == "true"
    log_dir = os.getenv("STARTPAGE_AUDIT_LOG_DIR", "").strip()
    
    if log_dir:
        return AuditService(log_dir=Path(log_dir), enabled=enabled)
    
    return AuditService(enabled=enabled)