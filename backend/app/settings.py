from __future__ import annotations

import os
from dataclasses import dataclass


def _read_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _read_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        return int(raw_value)
    except ValueError:
        return default


def _read_csv(name: str, default: str) -> tuple[str, ...]:
    raw_value = os.getenv(name, default)
    return tuple(part.strip() for part in raw_value.split(",") if part.strip())


@dataclass(frozen=True)
class AppSettings:
    ldap_server: str
    ldap_base_dn: str
    ldap_domain_suffix: str
    mock_auth_enabled: bool
    mock_groups: tuple[str, ...]
    mock_integrations_enabled: bool
    connector_enabled: bool
    connector_url: str
    connector_timeout_seconds: int
    session_ttl_minutes: int
    allowed_origins: tuple[str, ...]
    rollout_tasks_dir: str
    rollout_name_map_dir: str
    rollout_control_dir: str
    rollout_status_dir: str

    @classmethod
    def from_environment(cls) -> "AppSettings":
        return cls(
            ldap_server=os.getenv("STARTPAGE_LDAP_SERVER", "").strip(),
            ldap_base_dn=os.getenv("STARTPAGE_LDAP_BASE_DN", "").strip(),
            ldap_domain_suffix=os.getenv("STARTPAGE_LDAP_DOMAIN_SUFFIX", "").strip(),
            mock_auth_enabled=_read_bool("STARTPAGE_ENABLE_MOCK_AUTH", True),
            mock_groups=_read_csv(
                "STARTPAGE_MOCK_GROUPS",
                "Startpage-Users,Startpage-Dashboard-Editors,Startpage-Platform-Admins,Startpage-Citrix-Admins",
            ),
            mock_integrations_enabled=_read_bool("STARTPAGE_ENABLE_MOCK_INTEGRATIONS", True),
            connector_enabled=_read_bool("STARTPAGE_CONNECTOR_ENABLED", False),
            connector_url=os.getenv("STARTPAGE_CONNECTOR_URL", "http://localhost:8090").strip() or "http://localhost:8090",
            connector_timeout_seconds=max(1, _read_int("STARTPAGE_CONNECTOR_TIMEOUT_SECONDS", 6)),
            session_ttl_minutes=max(15, _read_int("STARTPAGE_SESSION_TTL_MINUTES", 480)),
            allowed_origins=_read_csv("STARTPAGE_ALLOWED_ORIGINS", "*"),
            rollout_tasks_dir=os.getenv("STARTPAGE_ROLLOUT_TASKS_DIR", "").strip(),
            rollout_name_map_dir=os.getenv("STARTPAGE_ROLLOUT_NAME_MAP_DIR", "").strip(),
            rollout_control_dir=os.getenv("STARTPAGE_ROLLOUT_CONTROL_DIR", "").strip(),
            rollout_status_dir=os.getenv("STARTPAGE_ROLLOUT_STATUS_DIR", "").strip(),
        )

    def runtime_warnings(self) -> list[str]:
        warnings: list[str] = []
        if not self.mock_auth_enabled:
            if not self.ldap_server:
                warnings.append("LDAP-Server ist nicht gesetzt, obwohl Mock-Auth deaktiviert ist.")
            if not self.ldap_base_dn:
                warnings.append("LDAP-Base-DN ist nicht gesetzt, obwohl Mock-Auth deaktiviert ist.")
            if not self.ldap_domain_suffix:
                warnings.append("LDAP-Domain-Suffix ist nicht gesetzt, obwohl Mock-Auth deaktiviert ist.")
        if self.connector_enabled and not self.connector_url:
            warnings.append("Connector ist aktiviert, aber STARTPAGE_CONNECTOR_URL fehlt.")
        if not self.mock_integrations_enabled and not self.connector_enabled:
            warnings.append("Live-Integrationen ohne Connector lassen Citrix- und RSAT-Pfade unvollstaendig.")
        if any((self.rollout_name_map_dir, self.rollout_control_dir, self.rollout_status_dir)) and not all(
            (self.rollout_name_map_dir, self.rollout_control_dir, self.rollout_status_dir)
        ):
            warnings.append("Rollout-Runtime-Pfade sind nur teilweise gesetzt; NAME-MAP, CONTROL und STATUS sollten gemeinsam konfiguriert werden.")
        return warnings
