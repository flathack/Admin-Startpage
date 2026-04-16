from __future__ import annotations

import os
from dataclasses import dataclass

import ldap3
from ldap3.utils.conv import escape_filter_chars


class AuthenticationError(Exception):
    """Raised when AD authentication fails."""


@dataclass(frozen=True)
class ADIdentity:
    username: str
    distinguished_name: str
    display_name: str
    email: str
    ad_groups: frozenset[str]


class ADAuthService:
    def __init__(
        self,
        *,
        ldap_server: str,
        base_dn: str,
        domain_suffix: str,
        enable_mock_auth: bool,
        mock_groups: tuple[str, ...],
    ) -> None:
        self._ldap_server = ldap_server
        self._base_dn = base_dn
        self._domain_suffix = domain_suffix
        self._enable_mock_auth = enable_mock_auth
        self._mock_groups = tuple(group for group in mock_groups if group)

    @classmethod
    def from_environment(cls) -> "ADAuthService":
        mock_groups = tuple(
            part.strip()
            for part in os.getenv(
                "STARTPAGE_MOCK_GROUPS",
                "Startpage-Users,Startpage-Dashboard-Editors,Startpage-Platform-Admins,Startpage-Citrix-Admins",
            ).split(",")
            if part.strip()
        )
        return cls(
            ldap_server=os.getenv("STARTPAGE_LDAP_SERVER", ""),
            base_dn=os.getenv("STARTPAGE_LDAP_BASE_DN", ""),
            domain_suffix=os.getenv("STARTPAGE_LDAP_DOMAIN_SUFFIX", ""),
            enable_mock_auth=os.getenv("STARTPAGE_ENABLE_MOCK_AUTH", "true").lower() == "true",
            mock_groups=mock_groups,
        )

    def authenticate(self, username: str, password: str) -> ADIdentity:
        username = username.strip()
        if not username or not password:
            raise AuthenticationError("Benutzername und Passwort sind erforderlich.")

        if self._enable_mock_auth:
            local_name = username.split("@")[0].split("\\")[-1]
            return ADIdentity(
                username=local_name,
                distinguished_name=f"CN={local_name},OU=Users,{self._base_dn or 'DC=local,DC=test'}",
                display_name=local_name,
                email=f"{local_name}@example.local",
                ad_groups=frozenset(self._mock_groups),
            )

        if not self._ldap_server or not self._base_dn or not self._domain_suffix:
            raise AuthenticationError("LDAP-Konfiguration ist unvollstaendig.")

        upn = self._build_upn(username)
        try:
            server = ldap3.Server(self._normalize_ldap_server(self._ldap_server), use_ssl=True, get_info=ldap3.NONE)
            connection = ldap3.Connection(
                server,
                user=upn,
                password=password,
                authentication=ldap3.SIMPLE,
                raise_exceptions=True,
                read_only=True,
            )
            connection.bind()
        except ldap3.core.exceptions.LDAPBindError as exc:
            raise AuthenticationError("Benutzername oder Passwort ungueltig.") from exc
        except Exception as exc:
            raise AuthenticationError(f"LDAP-Fehler: {exc}") from exc

        sam_name = username.split("@")[0].split("\\")[-1]
        safe_filter = f"(sAMAccountName={escape_filter_chars(sam_name)})"
        connection.search(
            self._base_dn,
            safe_filter,
            attributes=["sAMAccountName", "distinguishedName", "displayName", "mail", "memberOf"],
        )
        if not connection.entries:
            connection.unbind()
            raise AuthenticationError("Benutzer im AD nicht gefunden.")

        entry = connection.entries[0]
        groups = self._resolve_groups(entry.memberOf.values if hasattr(entry.memberOf, "values") else [])
        display_name = str(entry.displayName) if hasattr(entry, "displayName") and entry.displayName else sam_name
        email = str(entry.mail) if hasattr(entry, "mail") and entry.mail else ""
        dn = str(entry.distinguishedName)
        resolved_username = str(entry.sAMAccountName)
        connection.unbind()

        return ADIdentity(
            username=resolved_username,
            distinguished_name=dn,
            display_name=display_name,
            email=email,
            ad_groups=frozenset(groups),
        )

    def _build_upn(self, username: str) -> str:
        if "@" in username or "\\" in username:
            return username
        return f"{username}@{self._domain_suffix}"

    @staticmethod
    def _normalize_ldap_server(value: str) -> str:
        normalized = value.strip()
        for prefix in ("ldaps://", "ldap://"):
            if normalized.lower().startswith(prefix):
                normalized = normalized[len(prefix):]
                break
        return normalized.rstrip("/")

    @staticmethod
    def _resolve_groups(member_of: list[str]) -> set[str]:
        groups: set[str] = set()
        for dn in member_of:
            parts = str(dn).split(",")
            if parts and parts[0].upper().startswith("CN="):
                groups.add(parts[0][3:])
        return groups
