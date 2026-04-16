# Admin Startpage

Admin Startpage ist ein lokales, browserbasiertes Admin-Portal mit Docker-Backend. Die Anwendung soll bestehende Betriebsfunktionen aus AD, Nutanix, Endpoint Central, vSphere und Citrix in einer gemeinsamen Oberflaeche buendeln und die Sicht pro Benutzer ueber bestehende AD-Gruppen steuern.

Das Projekt ist bewusst nicht nur eine Linkliste. Ziel ist eine persoenliche Startseite mit rollenbasierter Navigation, per-User-Dashboard, zentralem Login und einer klar getrennten Integrationsschicht fuer Systeme, die direkt im Container laufen koennen, sowie Windows-nahe Spezialfaelle.

## Status

Der aktuelle Stand ist ein funktionsfaehiger Prototyp mit:

- FastAPI-Backend im Docker-Setup
- Browser-Frontend mit Portainer-inspirierter Shell und Sidebar-Navigation
- AD-Login-Service mit Mock-Modus fuer lokale Entwicklung
- Rollen- und Permission-Modell auf Basis von AD-Gruppen
- Personalisierter Dashboard-Konfiguration pro Benutzer
- Integrationsansichten fuer AD, Nutanix, Endpoint Central, vSphere und Citrix
- Optionalem Windows-Connector fuer AD-RSAT- und Citrix-On-Prem-nahe Funktionen
- Persistierten Rollout-Jobs im Web-Backend als erster Migrationsstufe aus Rollout-Monitor
- Ersten Runtime-/Share-Pfaden fuer Rollout-Jobs inklusive STATUS-, CONTROL- und NAME-MAP-Anbindung

## Zielbild

Die Startpage wird als Multi-User-Webanwendung fuer Admins aufgebaut:

- Login mit AD-Admin-Account
- Aufloesung von AD-Gruppen in Rollen und Permissions
- Personalisierte Startseite pro Benutzer
- Sichtbare Module nur bei vorhandener Berechtigung
- Serverseitige Rechtepruefung fuer API-Zugriffe und spaetere Schreibaktionen

## Architektur

Die Anwendung besteht aus vier Schichten:

1. Browser-Frontend fuer Navigation, Dashboard und Modulsichten
2. Dockerisiertes Python-Backend mit Session-Handling und API-Endpunkten
3. Integrationsschicht fuer containerfaehige Systeme wie Nutanix, Endpoint Central und vSphere
4. Optionaler Windows-Connector fuer AD-RSAT und Citrix On-Prem

Warum diese Trennung notwendig ist:

- LDAP-Login ist containerfaehig
- Nutanix-, Endpoint- und vSphere-REST-Zugriffe sind containerfaehig
- Tiefe AD-Funktionen im Bestand verwenden PowerShell und ActiveDirectory-Module
- Citrix On-Prem benoetigt je nach Anwendungsfall OData und Windows-nahe PowerShell-Pfade

## Module

Der aktuelle UI-Aufbau ist auf eine kompakte Operations-Sicht ausgelegt:

- Dashboard
- ActiveDirectory
- Nutanix
- Endpoint Central
- Citrix
- Rollout

Im Rollout-Modul koennen bereits erste Jobs persistent im Backend angelegt, gelistet und fuer einen Neustart zurueckgesetzt werden. Zusaetzlich kann die Web-App jetzt Runtime-Dateien aus `NAME-MAP`, `STATUS` und `CONTROL` auslesen, `ASSIGN`- und `RESUME`-Signale pro Job schreiben, ACK-/Registrierungsdaten auswerten und Runtime-Status wieder in den gespeicherten Jobfortschritt zurueckfuehren. Die eigentliche Clone-, WinPE- und Continue-Logik aus Rollout-Monitor folgt in weiteren Schritten.

Innerhalb von ActiveDirectory ist bereits eine Sidebar-Tree-Struktur fuer diese Bereiche vorbereitet:

- AD Users & Computers
- Auswertungen
- DNS
- DHCP

## Sicherheit und Berechtigungen

Die Anwendung folgt einem einfachen, klaren Berechtigungsmodell:

- AD-Gruppe -> Rolle
- Rolle -> Permission-Set
- Permission -> serverseitig gepruefte Aktion

Wichtig dabei:

- Passwoerter werden nicht im Frontend gespeichert
- UI-Sichtbarkeit ersetzt keine serverseitige Pruefung
- Gleichzeitige Benutzer-Sessions muessen strikt getrennt bleiben
- Schreibende Aktionen werden erst nach expliziter Permission-Freigabe aktiviert

## Projektstruktur

```text
Startpage/
  backend/
    app/
      config/
      services/
      static/
    Dockerfile
    requirements.txt
  connector/
    app/
    Dockerfile
    requirements.txt
  data/
  docker-compose.yml
  readme.md
```

## Schnellstart

Vor dem ersten Docker-Start sollte die Konfiguration aus `.env.example` in eine lokale `.env` uebernommen und fuer die Umgebung angepasst werden.

### Docker

Im Projektordner:

```powershell
# optional einmalig
Copy-Item .env.example .env

docker compose up --build
```

Danach ist das Backend samt UI unter `http://localhost:8080` erreichbar.

### Docker mit Connector

Wenn der Connector als separater Dienst mitlaufen soll:

```powershell
docker compose --profile connector up --build
```

Dann ist der Connector unter `http://localhost:8090` verfuegbar.

### Lokale Entwicklung ohne Docker

Backend starten:

```powershell
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

Connector starten:

```powershell
cd connector
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8090
```

## Entwicklungsmodus

Fuer lokale Entwicklung ist der Prototyp absichtlich sofort lauffaehig:

- Mock-Authentifizierung ist standardmaessig aktiv
- Integrationen laufen standardmaessig im Mock-Modus

Fuer produktionsnaehere Tests muessen mindestens diese Variablen gesetzt werden:

- `STARTPAGE_ENABLE_MOCK_AUTH=false`
- `STARTPAGE_ENABLE_MOCK_INTEGRATIONS=false`
- `STARTPAGE_CONNECTOR_ENABLED=true`
- `STARTPAGE_CONNECTOR_URL`
- `STARTPAGE_LDAP_SERVER`
- `STARTPAGE_LDAP_BASE_DN`
- `STARTPAGE_LDAP_DOMAIN_SUFFIX`
- `STARTPAGE_ROLLOUT_TASKS_DIR`
- `STARTPAGE_ROLLOUT_NAME_MAP_DIR`
- `STARTPAGE_ROLLOUT_CONTROL_DIR`
- `STARTPAGE_ROLLOUT_STATUS_DIR`

Das Backend meldet unvollstaendige Runtime-Konfigurationen zusaetzlich ueber den Health-Endpoint, damit Deployments mit deaktiviertem Mock-Modus schneller auffallen.

## Herkunft der Fachlogik

Das Projekt orientiert sich fachlich an Bausteinen aus dem bestehenden Rollout-Monitor. Uebernommen oder als Vorlage verwendet werden vor allem:

- AD-Authentifizierung
- Rollen- und Permission-Aufloesung
- Integrationslogik fuer Nutanix, vSphere und weitere Bestandssysteme
- Citrix-nahe Multi-User- und Connector-Pfade

Das Ziel ist keine 1:1-Portierung der Desktop-Anwendung, sondern eine saubere Ueberfuehrung in eine Webarchitektur.

## Roadmap

Naechste technische Schritte:

- Live-Anbindung fuer Nutanix, vSphere und Endpoint weiter haerten
- Windows-Connector mit echter AD-RSAT- und Citrix-Logik hinterlegen
- AD-Unterbereiche wie Reports, DNS und DHCP fachlich ausbauen
- Erste schreibende Aktionen mit expliziten Permissions freischalten
- Auditierbarkeit und Fehlerbehandlung erweitern

## Hinweis

Aktuell ist das Projekt ein administrativer Prototyp fuer die interne Betriebsunterstuetzung. Die vorhandenen Mock-Modi sind bewusst fuer Entwicklung und UI-Ausbau vorgesehen und nicht fuer produktiven Betrieb gedacht.
