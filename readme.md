# Startpage fuer Admins - Architektur und Umsetzungsplan

## Zielbild
Die Startpage wird als lokale, browserbasierte Multi-User-Anwendung umgesetzt. Die Oberflaeche laeuft im Browser, die eigentliche Logik in einem Docker-basierten Backend. Nach AD-Login sollen pro Benutzer API-Zugriffe auf AD, Nutanix, Endpoint Central, vSphere und Citrix moeglich sein, soweit die jeweilige Berechtigung ueber bestehende AD-Gruppen gegeben ist.

Die Startpage ist damit kein statischer Link-Hub mehr, sondern ein persoenliches Admin-Portal mit rollenbasierter Sicht, persoenlichem Dashboard und zentralem Zugriff auf bestehende Betriebsfunktionen.

## Ausgangslage aus Rollout-Monitor
Das Projekt Rollout-Monitor bringt bereits zentrale Bausteine mit, die fuer die Webanwendung wiederverwendet oder fachlich uebernommen werden koennen:

- AD-Authentifizierung via LDAP in core/auth_service.py
- AD-Gruppen zu Rollen und Rollen zu Permissions in core/permissions.py
- Nutanix-Zugriffe in core/nutanix_client.py
- vSphere-Zugriffe in core/vsphere_client.py
- Endpoint-, Zenworks- und Citrix-Integrationen in core/external_integration_service.py und core/integration_client.py
- Gemeinsame Multi-User-Sitzungslogik fuer Citrix-Workflows in core/citrix_worker_session.py

Die eigentliche Aufgabe ist die saubere Migration von einer lokalen Desktop-App zu einer sicheren Webarchitektur.

## Zielarchitektur
Die Startpage besteht aus vier Schichten:

1. Browser-Frontend pro Benutzer
2. Containerisiertes Web-Backend mit API und Session-Verwaltung
3. Integrationsschicht fuer Nutanix, Endpoint Central und vSphere
4. Windows-Connector fuer AD-RSAT- und Citrix-On-Prem-Funktionen

## Warum diese Aufteilung noetig ist
- LDAP-basierter AD-Login ist containerfaehig
- Nutanix-, Endpoint-Central- und vSphere-REST-Aufrufe sind grundsaetzlich containerfaehig
- Viele tiefe AD-Funktionen im bestehenden Projekt nutzen PowerShell mit ActiveDirectory-Modul
- Citrix-On-Prem nutzt teils OData, teils Remote-PowerShell-Fallbacks gegen Delivery Controller

Ein reiner Linux-Container ist deshalb fuer die komplette Fachlogik nicht ausreichend. Die robuste Zielarchitektur ist ein Web-Backend im Container plus Windows-Connector fuer Spezialfaelle.

## Fachliches Zielmodell

### Anmeldung
- Benutzer ruft lokale Startpage im Browser auf
- Login mit AD-Admin-Benutzername und Passwort
- Backend authentifiziert gegen Active Directory via LDAP
- AD-Gruppen werden geladen und in Rollen und Berechtigungen aufgeloest
- Pro Benutzer wird eine Session aufgebaut

### Personalisierte Startpage
- Jeder Benutzer erhaelt eine eigene Startseite
- Persoenliche Widgets, Favoriten, Kategorien und Schnellzugriffe werden pro Benutzer gespeichert
- Sichtbare Module und Aktionen ergeben sich aus AD-Gruppen und Rollen

### Systemzugriffe nach Login
- Backend nutzt Session, Rollen und Berechtigungen zur Freigabe einzelner API-Aktionen
- Wo fachlich sinnvoll, werden Benutzer-Credentials sitzungsbasiert weiterverwendet
- Wo Systeme technische Tokens oder Service-Accounts benoetigen, erfolgt Zugriff ueber dedizierte Backend-Konfiguration

## Authentifizierung und Autorisierung
- AD-Gruppe -> Rolle
- Rolle -> Permission-Set
- Permission-String pro Modul und Aktion, zum Beispiel nutanix.view, vsphere.power_on, citrix.assign_user

Die Berechtigungen werden nicht nur in der Oberflaeche versteckt, sondern auch serverseitig bei jeder Aktion geprueft.

## Zielmodule der Startpage
- Dashboard: persoenliche Startansicht, Favoriten, Hinweise, Statuskarten, Suchfeld
- AD: Basisfunktionen wie Benutzer- und Computer-Suche, spaeter Reports und Verwaltungsfunktionen
- Nutanix: Cluster-, VM- und Image-nahe Informationen
- Endpoint Central: Geraete- und Patch-Status
- vSphere: VM-Uebersicht und Betriebsstatus
- Citrix: Maschinen-, Benutzer- und Session-bezogene Informationen

## Technische Zielarchitektur

### Frontend
- Browserbasierte Oberflaeche
- Persoenliches Dashboard pro Benutzer
- Such- und Kachelkonzept
- Rechteabhaengige Anzeige von Modulen und Aktionen

### Backend
- Python-Web-API im Docker-Container
- Session-Handling, Rollenaufloesung, Benutzerkonfiguration, Audit-Logging
- Adapter-Schicht fuer externe Systeme

### Windows Connector
- Eigener Dienst mit API-Vertrag fuer AD-RSAT und Citrix-On-Prem
- Kann lokal auf Windows oder spaeter als separater Connector-Dienst betrieben werden
- Wird vom Web-Backend ueber HTTP angesprochen

### Datenhaltung
- Benutzerprofile und Dashboard-Konfiguration pro Benutzer
- Rollen- und Mapping-Konfiguration als JSON
- Spaeter optional SQLite oder PostgreSQL fuer zentrale Ablage

## Sicherheitsprinzipien
- Keine Speicherung von Passwoertern im Frontend
- Serverseitige Permission-Pruefung fuer jede schreibende Aktion
- Auditierbarkeit von administrativen Eingriffen
- Trennung zwischen Login-Identitaet, Rollenaufloesung und Systemaktionen
- Keine implizite Freigabe nur wegen sichtbarer UI-Elemente

## Multi-User-Anforderungen
- Mehrere Benutzer greifen parallel auf dieselbe Startpage-Instanz zu
- Jeder Benutzer hat eine eigene Konfiguration und eigene Favoriten
- Berechtigungen werden aus bestehenden AD-Gruppen aufgeloest
- Gleichzeitige Sessions duerfen sich nicht gegenseitig beeinflussen

## Aktueller Umsetzungsstand
Vorhanden sind bereits:

- Docker-Compose-Setup fuer das Web-Backend
- FastAPI-Backend mit Health-Endpoint, Login und per-User-Dashboard-Speicherung
- Rollen- und Gruppenaufloesung ueber JSON-Konfiguration nach Vorbild Rollout-Monitor
- Browser-Frontend mit Login, persoenlicher Startseite, Modulfreigaben und Widget-Pflege
- Integrations-Uebersicht fuer AD, Nutanix, Endpoint Central, vSphere und Citrix
- Mock- und Live-Modus fuer Integrationen
- Connector-Client im Backend sowie ein eigener Connector-Prototyp mit API-Vertrag

## Projektstruktur
```text
Startpage/
  backend/
    app/
      config/
      services/
      static/
  connector/
    app/
  data/
  docker-compose.yml
  readme.md
```

## Start des Prototyps

### Per Docker
Im Projektordner Startpage:

```powershell
docker compose up --build
```

Danach ist die Anwendung unter http://localhost:8080 erreichbar.

### Optional mit Connector-Profil
Wenn der Connector als separater Mock-Dienst mitlaufen soll:

```powershell
docker compose --profile connector up --build
```

Dann laeuft zusaetzlich der Connector auf http://localhost:8090.

### Lokale Entwicklung ohne Docker
Web-Backend im Ordner Startpage\backend:

```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

Connector im Ordner Startpage\connector:

```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8090
```

## Entwicklungsmodus
Aktuell ist Mock-Authentifizierung standardmaessig aktiv, solange keine produktive LDAP-Konfiguration gesetzt wird. Zusaetzlich sind Integrationen standardmaessig im Mock-Modus aktiv. Damit kann die Weboberflaeche lokal sofort entwickelt werden.

Fuer den Produktivbetrieb muessen spaeter mindestens Folgendes gesetzt oder sauber konfiguriert werden:

- STARTPAGE_ENABLE_MOCK_AUTH=false
- STARTPAGE_ENABLE_MOCK_INTEGRATIONS=false
- STARTPAGE_CONNECTOR_ENABLED=true
- STARTPAGE_CONNECTOR_URL
- STARTPAGE_LDAP_SERVER
- STARTPAGE_LDAP_BASE_DN
- STARTPAGE_LDAP_DOMAIN_SUFFIX

## Naechste technische Schritte
- Nutanix-, vSphere- und Endpoint-Integrationen von Mock auf Live-Konfiguration umstellen
- Backend-Endpunkte fuer echte Read-Only-Abfragen haerten und um Timeout-/Fehlerbehandlung erweitern
- Windows Connector fuer Citrix On-Prem und AD-RSAT-Funktionen schrittweise mit echter PowerShell-/RSAT-Logik hinterlegen
- Erste schreibende Aktionen nur fuer klar definierte Permissions freischalten

## Fazit
Die Startpage wird als persoenliches, browserbasiertes Admin-Portal mit Docker-Backend gebaut. Die Logik aus dem Rollout-Monitor wird schrittweise in eine Webarchitektur ueberfuehrt. Containerfaehige Integrationen laufen direkt im Backend, AD-RSAT- und Citrix-nahe Spezialfunktionen ueber einen separaten Windows-Connector.
