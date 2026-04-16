"""
Active Directory Service for querying AD data via LDAP.

Provides methods for:
- Listing users, computers, groups, OUs
- Searching AD objects
- Reading DNS and DHCP information (via LDAP or Connector)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import ldap3
from ldap3 import SUBTREE


logger = logging.getLogger("admin-startpage.ad")


class ADServiceError(Exception):
    """Exception raised for AD service errors."""
    pass


@dataclass
class ADUser:
    """Represents an Active Directory user."""
    username: str
    display_name: str
    email: str
    distinguished_name: str
    enabled: bool = True
    description: str = ""


@dataclass
class ADComputer:
    """Represents an Active Directory computer."""
    name: str
    distinguished_name: str
    enabled: bool = True
    operating_system: str = ""
    description: str = ""


@dataclass
class ADGroup:
    """Represents an Active Directory group."""
    name: str
    distinguished_name: str
    description: str = ""
    members_count: int = 0


@dataclass
class ADOU:
    """Represents an Active Directory organizational unit."""
    name: str
    distinguished_name: str


class ADService:
    """Service for querying Active Directory via LDAP."""
    
    def __init__(
        self,
        ldap_server: str,
        base_dn: str,
        bind_user: str | None = None,
        bind_password: str | None = None,
    ) -> None:
        self._ldap_server = ldap_server
        self._base_dn = base_dn
        self._bind_user = bind_user
        self._bind_password = bind_password
        self._connection: ldap3.Connection | None = None
    
    def connect(self) -> bool:
        """Establish LDAP connection."""
        try:
            server = ldap3.Server(self._ldap_server, use_ssl=True, get_info=ldap3.NONE)
            
            if self._bind_user and self._bind_password:
                self._connection = ldap3.Connection(server, user=self._bind_user, password=self._bind_password)
            else:
                # Anonymous bind (read-only)
                self._connection = ldap3.Connection(server)
            
            if not self._connection.bind():
                logger.error(f"Failed to bind to LDAP: {self._connection.last_error}")
                return False
            
            logger.info(f"Connected to LDAP server: {self._ldap_server}")
            return True
        except Exception as exc:
            logger.error(f"LDAP connection error: {exc}")
            raise ADServiceError(f"Failed to connect to LDAP: {exc}")
    
    def disconnect(self) -> None:
        """Close LDAP connection."""
        if self._connection:
            self._connection.unbind()
            self._connection = None
    
    def search_users(
        self,
        search_base: str | None = None,
        search_filter: str = "(objectClass=user)",
        limit: int = 100,
    ) -> list[ADUser]:
        """Search for AD users."""
        if not self._connection:
            raise ADServiceError("Not connected to LDAP")
        
        base = search_base or self._base_dn
        try:
            self._connection.search(
                search_base=base,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=["cn", "sAMAccountName", "mail", "displayName", "distinguishedName", "userAccountControl", "description"],
                size_limit=limit,
            )
            
            users = []
            for entry in self._connection.entries:
                try:
                    username = str(entry.sAMAccountName)
                    enabled = not bool(int(entry.userAccountControl) & 2)  # 2 = disabled
                    
                    users.append(ADUser(
                        username=username,
                        display_name=str(entry.displayName or username),
                        email=str(entry.mail or f"{username}@local"),
                        distinguished_name=str(entry.distinguishedName),
                        enabled=enabled,
                        description=str(entry.description or ""),
                    ))
                except Exception as e:
                    logger.warning(f"Failed to parse user entry: {e}")
                    continue
            
            return users
        except Exception as exc:
            logger.error(f"User search failed: {exc}")
            raise ADServiceError(f"User search failed: {exc}")
    
    def search_computers(
        self,
        search_base: str | None = None,
        search_filter: str = "(objectClass=computer)",
        limit: int = 100,
    ) -> list[ADComputer]:
        """Search for AD computers."""
        if not self._connection:
            raise ADServiceError("Not connected to LDAP")
        
        base = search_base or self._base_dn
        try:
            self._connection.search(
                search_base=base,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=["cn", "name", "distinguishedName", "userAccountControl", "operatingSystem", "description"],
                size_limit=limit,
            )
            
            computers = []
            for entry in self._connection.entries:
                try:
                    name = str(entry.name)
                    enabled = not bool(int(entry.userAccountControl) & 2)
                    
                    computers.append(ADComputer(
                        name=name,
                        distinguished_name=str(entry.distinguishedName),
                        enabled=enabled,
                        operating_system=str(entry.operatingSystem or ""),
                        description=str(entry.description or ""),
                    ))
                except Exception as e:
                    logger.warning(f"Failed to parse computer entry: {e}")
                    continue
            
            return computers
        except Exception as exc:
            logger.error(f"Computer search failed: {exc}")
            raise ADServiceError(f"Computer search failed: {exc}")
    
    def search_groups(
        self,
        search_base: str | None = None,
        search_filter: str = "(objectClass=group)",
        limit: int = 100,
    ) -> list[ADGroup]:
        """Search for AD groups."""
        if not self._connection:
            raise ADServiceError("Not connected to LDAP")
        
        base = search_base or self._base_dn
        try:
            self._connection.search(
                search_base=base,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=["cn", "name", "distinguishedName", "description", "member"],
                size_limit=limit,
            )
            
            groups = []
            for entry in self._connection.entries:
                try:
                    name = str(entry.name)
                    members = entry.member if hasattr(entry, 'member') else []
                    members_count = len(members) if members else 0
                    
                    groups.append(ADGroup(
                        name=name,
                        distinguished_name=str(entry.distinguishedName),
                        description=str(entry.description or ""),
                        members_count=members_count,
                    ))
                except Exception as e:
                    logger.warning(f"Failed to parse group entry: {e}")
                    continue
            
            return groups
        except Exception as exc:
            logger.error(f"Group search failed: {exc}")
            raise ADServiceError(f"Group search failed: {exc}")
    
    def get_ous(self, search_base: str | None = None) -> list[ADOU]:
        """Get list of Organizational Units."""
        if not self._connection:
            raise ADServiceError("Not connected to LDAP")
        
        base = search_base or self._base_dn
        try:
            self._connection.search(
                search_base=base,
                search_filter="(objectClass=organizationalUnit)",
                search_scope=SUBTREE,
                attributes=["ou", "name", "distinguishedName"],
                size_limit=50,
            )
            
            ous = []
            for entry in self._connection.entries:
                try:
                    name = str(entry.name)
                    ous.append(ADOU(
                        name=name,
                        distinguished_name=str(entry.distinguishedName),
                    ))
                except Exception:
                    continue
            
            return ous
        except Exception as exc:
            logger.error(f"OU search failed: {exc}")
            raise ADServiceError(f"OU search failed: {exc}")
    
    def get_dns_zones(self) -> list[dict[str, Any]]:
        """Get DNS zones from AD (requires specific LDAP path for DNS zones)."""
        # DNS zones are stored under cn=MicrosoftDNS,cn=System,<base_dn>
        dns_zone_base = f"cn=MicrosoftDNS,cn=System,{self._base_dn}"
        
        if not self._connection:
            raise ADServiceError("Not connected to LDAP")
        
        try:
            self._connection.search(
                search_base=dns_zone_base,
                search_filter="(objectClass=dnsZone)",
                search_scope=SUBTREE,
                attributes=["dc", "dnsRoot", "description"],
                size_limit=20,
            )
            
            zones = []
            for entry in self._connection.entries:
                zones.append({
                    "name": str(entry.dc),
                    "distinguishedName": str(entry.distinguishedName),
                })
            
            return zones
        except Exception as exc:
            logger.warning(f"DNS zone search failed: {exc}")
            return []
    
    def get_dns_records(self, zone: str, record_type: str = "A") -> list[dict[str, Any]]:
        """Get DNS records for a specific zone."""
        if not self._connection:
            raise ADServiceError("Not connected to LDAP")
        
        dns_base = f"dc={zone},cn=MicrosoftDNS,cn=System,{self._base_dn}"
        
        try:
            self._connection.search(
                search_base=dns_base,
                search_filter="(objectClass=dNSZone)",
                search_scope=SUBTREE,
                attributes=["name", "dNSDomainName", "dnsRecord"],
                size_limit=100,
            )
            
            records = []
            for entry in self._connection.entries:
                records.append({
                    "name": str(entry.name),
                    "zone": zone,
                    "type": record_type,
                })
            
            return records
        except Exception as exc:
            logger.warning(f"DNS record search failed: {exc}")
            return []
    
    def get_dhcp_servers(self) -> list[dict[str, Any]]:
        """Get DHCP servers from AD."""
        if not self._connection:
            raise ADServiceError("Not connected to LDAP")
        
        dhcp_base = f"cn=DHCP,{self._base_dn}"
        
        try:
            self._connection.search(
                search_base=dhcp_base,
                search_filter="(objectClass=dhcpServer)",
                search_scope=SUBTREE,
                attributes=["cn", "distinguishedName"],
                size_limit=20,
            )
            
            servers = []
            for entry in self._connection.entries:
                servers.append({
                    "name": str(entry.cn),
                    "distinguishedName": str(entry.distinguishedName),
                })
            
            return servers
        except Exception as exc:
            logger.warning(f"DHCP server search failed: {exc}")
            return []


def create_from_settings(
    ldap_server: str,
    base_dn: str,
    bind_user: str | None = None,
    bind_password: str | None = None,
) -> ADService:
    """Create ADService from settings."""
    return ADService(
        ldap_server=ldap_server,
        base_dn=base_dn,
        bind_user=bind_user,
        bind_password=bind_password,
    )