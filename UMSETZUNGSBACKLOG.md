# Umsetzungs-Backlog Admin Startpage

## Zweck

Dieses Backlog zerlegt den Umsetzungsplan in konkrete Arbeitspakete und Tickets. Ziel ist die vollstaendig fertige Web-App gemaess [UMSETZUNGSPLAN.md](UMSETZUNGSPLAN.md).

Jedes Ticket ist so formuliert, dass es als umsetzbare Einheit fuer Entwicklung, Test und Abnahme genutzt werden kann.

## Zielzustand

Das Backlog ist erst dann vollstaendig abgearbeitet, wenn:

- alle Hauptmodule fachlich nutzbar sind
- alle benoetigten Live-Integrationen ohne Mock lauffaehig sind
- Rollout, AD, DNS, DHCP, Citrix, Endpoint und vSphere im Zielumfang umgesetzt sind
- Logging, Audit, Deployment und Betriebsdokumentation produktionsreif sind
- fuer die vorgesehenen Prozesse kein Rueckgriff auf Rollout-Monitor mehr noetig ist

## Prioritaetslogik

- `P1`: blockiert die Fertigstellung der Web-App direkt
- `P2`: wichtig fuer fachliche Vollstaendigkeit
- `P3`: wichtig fuer Betriebsreife, Bedienbarkeit und Abschluss

## Statuslogik

- `offen`
- `in Arbeit`
- `blockiert`
- `abnahmebereit`
- `abgeschlossen`

## Phase 1: Plattform und Grundsystem

### SP-001 Live-Konfiguration vereinheitlichen

- Prioritaet: `P1`
- Status: `offen`
- Ziel: alle benoetigten Umgebungsvariablen, Defaults und Produktivwerte eindeutig strukturieren
- Aufgaben:
- `.env`, `.env.example` und `.env.production.example` konsolidieren
- Live- und Mock-Einstellungen klar trennen
- Konfiguration fuer Nutanix, vSphere, Endpoint, LDAP, Connector und Rollout-Runtime sauber dokumentieren
- Abnahme:
- ein neues System kann ohne Codeaenderung nur ueber Konfiguration gestartet werden
- Health liefert bei fehlenden Werten nachvollziehbare Hinweise

### SP-002 Session- und Login-Haertung abschliessen

- Prioritaet: `P1`
- Status: `offen`
- Ziel: stabiler produktiver AD-Login mit sauberem Session-Verhalten
- Aufgaben:
- LDAP-Fehlerfaelle vereinheitlichen
- Session-TTL und Logout-Verhalten pruefbar machen
- erneute Authentifizierung fuer kritische Aktionen vorbereiten
- Session-Handling im Frontend gegen abgelaufene Tokens absichern
- Abnahme:
- Login, Logout, Session-Ablauf und Fehlerfall sind reproduzierbar testbar

### SP-003 Rollen und Berechtigungen finalisieren

- Prioritaet: `P1`
- Status: `offen`
- Ziel: endgueltiges Berechtigungsmodell fuer die fertige Web-App
- Aufgaben:
- Gruppenmapping mit Produktivgruppen verifizieren
- Modul- und Aktionsrechte pro Bereich final festlegen
- serverseitige Pruefungen fuer alle schreibenden Aktionen vervollstaendigen
- Abnahme:
- jede schreibende Route ist serverseitig abgesichert
- Rollenmodell ist dokumentiert und fachlich abgestimmt

### SP-004 Basis-Health und Betriebsdiagnostik schliessen

- Prioritaet: `P2`
- Status: `offen`
- Ziel: technische Probleme schnell sichtbar machen
- Aufgaben:
- Health um Live-Konfiguration, Connector, Runtime-Shares und Audit erweitern
- Diagnoseinformationen fuer Admins im Frontend sichtbarer machen
- Abnahme:
- zentrale Betriebsfehler lassen sich ohne Codeanalyse erkennen

## Phase 2: Rollout Live auf Nutanix

### SP-101 Nutanix-Client fuer produktive Rollout-Operationen haerten

- Prioritaet: `P1`
- Status: `offen`
- Ziel: belastbarer Live-Client fuer VM-Erstellung, Statusabfrage und Power-Steuerung
- Aufgaben:
- vorhandene API-Aufrufe gegen echte Prism-Antworten haerten
- Template-, Cluster- und Netzwerkauflösung robust machen
- Fehlerbehandlung und Timeouts verbessern
- Abnahme:
- reale Nutanix-Operationen laufen mit nachvollziehbaren Statusrueckgaben

### SP-102 Rollout-Worker live-faehig machen

- Prioritaet: `P1`
- Status: `offen`
- Ziel: Rollout-Start ohne Mock-Orchestrierung
- Aufgaben:
- Live-Nutanix-Pfad im Worker finalisieren
- Fortschritt und Stages aus echten Live-Schritten ableiten
- Jobstatus sauber speichern und aktualisieren
- Abnahme:
- ein Live-Rollout fuehrt mindestens bis zur erfolgreichen VM-Bereitstellung und Boot-Sequenz

### SP-103 Rollout-Parameter fachlich vervollstaendigen

- Prioritaet: `P1`
- Status: `offen`
- Ziel: Rollout-Jobs enthalten alle benoetigten Live-Parameter
- Aufgaben:
- Template-, Cluster-, Netzwerk-, Namens- und Zusatzparameter final definieren
- Frontend-Formular fuer reale Rollout-Jobs vervollstaendigen
- Abnahme:
- alle fuer den Live-Start benoetigten Eingaben koennen im Web gepflegt werden

### SP-104 Live-Rollout End-to-End testen

- Prioritaet: `P1`
- Status: `offen`
- Ziel: erster belastbarer Live-Durchstich
- Aufgaben:
- Live-Start in Testumgebung ausfuehren
- Ergebnis, Fehlerpfade und Statusmapping validieren
- Abnahme:
- dokumentierter End-to-End-Testfall vorhanden und erfolgreich nachvollziehbar

## Phase 3: Continue, Resume, ACK und Registrierung

### SP-201 Runtime-Statusmodell abschliessen

- Prioritaet: `P1`
- Status: `offen`
- Ziel: eindeutige Statuslogik fuer laufende Rollouts
- Aufgaben:
- Runtime-Dateien, ACK, Registrierung und Statuswerte final auf Jobstatus mappen
- Konfliktfaelle modellieren
- Abnahme:
- alle benoetigten Zwischenzustaende sind fachlich sauber unterschieden

### SP-202 Continue- und Resume-Workflow vollenden

- Prioritaet: `P1`
- Status: `offen`
- Ziel: unterbrochene Rollouts im Web fortsetzen koennen
- Aufgaben:
- Continue-/Resume-Entscheidungen aus Rollout-Monitor uebernehmen
- Web-Aktionen und API-Routen vervollstaendigen
- Abnahme:
- unterbrochene Jobs koennen im Zielprozess vollstaendig ueber die Web-App fortgesetzt werden

### SP-203 ACK- und Registrierungspfad haerten

- Prioritaet: `P1`
- Status: `offen`
- Ziel: Maschinenzuordnung und Registrierung robust abwickeln
- Aufgaben:
- ACK-Auswertung fuer UUID, Seriennummer, Name Request und Registrierung finalisieren
- Fehler- und Doppelzuordnungsfaelle behandeln
- Abnahme:
- Registrierungsprozess ist nachvollziehbar, robust und ohne manuelle Nacharbeit nutzbar

## Phase 4: Rollout-Lifecycle komplettieren

### SP-301 Delete-Workflow portieren

- Prioritaet: `P1`
- Status: `offen`
- Ziel: vollstaendiger Delete-Prozess im Web
- Aufgaben:
- Reihenfolge TXT, AD, Endpoint, Nutanix fachlich umsetzen
- Zwischenstaende und Wiederanlauf modellieren
- Abnahme:
- Delete ist fuer freigegebene Rollen vollstaendig ueber die Web-App ausfuehrbar

### SP-302 ReRollout-Workflow portieren

- Prioritaet: `P1`
- Status: `offen`
- Ziel: erneuter Rollout ohne Altwerkzeug
- Aufgaben:
- ReRollout-Statusmodell und API-Aktionen umsetzen
- benoetigte Vorbedingungen im UI sichtbar machen
- Abnahme:
- ReRollout ist end-to-end im Web verfuegbar

### SP-303 Risikobehaftete Aktionen absichern

- Prioritaet: `P1`
- Status: `offen`
- Ziel: sichere Bedienung destruktiver Aktionen
- Aufgaben:
- Bestätigungsdialoge, Rechtepruefung und Audit fuer Delete/ReRollout schliessen
- Abnahme:
- destruktive Aktionen sind nachvollziehbar, abgesichert und auditierbar

## Phase 5: Active Directory, DNS und DHCP

### SP-401 AD Users & Computers fachlich umsetzen

- Prioritaet: `P1`
- Status: `offen`
- Ziel: nutzbare AD-Verwaltung im Web
- Aufgaben:
- Suche, Detailansicht und benoetigte Verwaltungsaktionen implementieren
- Connector-/Backend-Schnittstellen fuer AD-Befehle vervollstaendigen
- Abnahme:
- zentrale AD-Arbeitsablaeufe sind im Web nutzbar

### SP-402 AD-Auswertungen umsetzen

- Prioritaet: `P2`
- Status: `offen`
- Ziel: benoetigte Reports und administrative Uebersichten liefern
- Aufgaben:
- Reports aus Bestand uebernehmen oder neu abbilden
- Export- oder Detailansichten definieren
- Abnahme:
- benoetigte Auswertungen sind im Web verfuegbar

### SP-403 DNS-Modul umsetzen

- Prioritaet: `P1`
- Status: `offen`
- Ziel: DNS-Lesen und definierte Schreiboperationen im Web
- Aufgaben:
- DNS-Suchen, Detailansichten und benoetigte Admin-Aktionen ueber Connector/Backend abbilden
- Abnahme:
- benoetigte DNS-Prozesse sind produktiv nutzbar

### SP-404 DHCP-Modul umsetzen

- Prioritaet: `P1`
- Status: `offen`
- Ziel: DHCP-Lesen und definierte Schreiboperationen im Web
- Aufgaben:
- Scopes, Leases und benoetigte Verwaltungsaktionen abbilden
- Abnahme:
- benoetigte DHCP-Prozesse sind produktiv nutzbar

## Phase 6: Citrix On-Prem produktiv anbinden

### SP-501 Connector fuer echte Citrix-Daten erweitern

- Prioritaet: `P1`
- Status: `offen`
- Ziel: Citrix nicht mehr als Connector-Mock betreiben
- Aufgaben:
- echte Endpunkte fuer Summary, Machines, Delivery Groups und Sessions implementieren
- PowerShell- oder API-Zugriffe gegen Zielumgebung absichern
- Abnahme:
- Citrix-Daten kommen live aus der Zielumgebung

### SP-502 Citrix-Aktionen im Web schliessen

- Prioritaet: `P1`
- Status: `offen`
- Ziel: benoetigte Citrix-Operationen direkt im Web
- Aufgaben:
- Maintenance, Zuweisung, Trennung und weitere abgestimmte Aktionen umsetzen
- Rechtepruefung und Fehlerbehandlung finalisieren
- Abnahme:
- abgestimmte Citrix-Aktionen sind live nutzbar

### SP-503 Citrix-UI fachlich vervollstaendigen

- Prioritaet: `P2`
- Status: `offen`
- Ziel: operativ nutzbare Citrix-Oberflaeche
- Aufgaben:
- Tabellen, Filter, Statusanzeigen und Aktionsdialoge vervollstaendigen
- Abnahme:
- Citrix-Modul ist fuer Tagesgeschaeft nutzbar

## Phase 7: Endpoint Central und vSphere fachlich abschliessen

### SP-601 Endpoint Central produktiv anbinden

- Prioritaet: `P2`
- Status: `offen`
- Ziel: echte Endpoint-Daten und benoetigte Aktionen im Web
- Aufgaben:
- Authentifizierungsstrategie finalisieren
- benoetigte Listen, Statusabfragen und Aktionen umsetzen
- Abnahme:
- definierte Endpoint-Prozesse sind live verfuegbar

### SP-602 vSphere-Modul fachlich vervollstaendigen

- Prioritaet: `P2`
- Status: `offen`
- Ziel: vSphere nicht nur lesend, sondern im abgestimmten Zielumfang nutzbar machen
- Aufgaben:
- Verbindungslogik haerten
- benoetigte VM- oder Infrastrukturaktionen definieren und umsetzen
- Abnahme:
- definierte vSphere-Prozesse sind produktiv nutzbar

### SP-603 Restintegrationen und Zenworks-Bedarf klaeren

- Prioritaet: `P3`
- Status: `offen`
- Ziel: keine ungeklaerten Integrationsluecken am Projektende
- Aufgaben:
- Zenworks oder aehnliche Restbedarfe fachlich entscheiden
- offene Integrationsluecken schliessen oder bewusst ausschliessen
- Abnahme:
- offener Scope ist fachlich geklaert und dokumentiert

## Phase 8: Frontend, Audit, Logging und Betriebsreife

### SP-701 Frontend-Produktivisierung abschliessen

- Prioritaet: `P2`
- Status: `offen`
- Ziel: vollstaendig nutzbare Oberflaeche fuer alle Module
- Aufgaben:
- Lade-, Fehler- und Leerlaufzustaende vereinheitlichen
- Formulare, Validierung und Dialoge absichern
- Bedienbarkeit fuer Admin-Tagesgeschaeft verbessern
- Abnahme:
- UI ist stabil, konsistent und ohne Demo-Charakter nutzbar

### SP-702 Audit-Logging vervollstaendigen

- Prioritaet: `P2`
- Status: `offen`
- Ziel: nachvollziehbare Protokollierung aller relevanten Aktionen
- Aufgaben:
- Audit fuer Login, Rollout, AD, Citrix, Delete und ReRollout vervollstaendigen
- Abnahme:
- alle kritischen Aktionen sind revisionsfaehig protokolliert

### SP-703 Strukturierte Logs und Diagnoseansichten umsetzen

- Prioritaet: `P2`
- Status: `offen`
- Ziel: Stoerungen schnell analysierbar machen
- Aufgaben:
- strukturierte Logs fuer Backend, Integrationen und Connector einfuehren
- einfache Diagnoseansichten oder Exportpfade bereitstellen
- Abnahme:
- Betriebsprobleme lassen sich zielgerichtet nachvollziehen

### SP-704 Deployment und Betriebsdokumentation finalisieren

- Prioritaet: `P2`
- Status: `offen`
- Ziel: interner Dauerbetrieb ohne Projektwissen im Kopf einzelner Personen
- Aufgaben:
- Deployment-Doku, Konfigurationsdoku und Betriebscheckliste finalisieren
- Backup-/Restore-Konzept fuer Jobs und Konfigurationsdaten dokumentieren
- Abnahme:
- Installation, Update und Betrieb sind dokumentiert und nachvollziehbar

### SP-705 Test- und Release-Checkliste einfuehren

- Prioritaet: `P3`
- Status: `offen`
- Ziel: reproduzierbare Freigabe vor Abschluss
- Aufgaben:
- Testfaelle pro Modul und Kernprozess zusammenstellen
- Abschluss-Checkliste fuer die fertige Web-App anlegen
- Abnahme:
- es gibt eine verbindliche Freigaberoutine fuer die Gesamtanwendung

## Empfohlene Umsetzungsreihenfolge

1. `SP-001` bis `SP-004`
2. `SP-101` bis `SP-104`
3. `SP-201` bis `SP-203`
4. `SP-301` bis `SP-303`
5. `SP-401` bis `SP-404`
6. `SP-501` bis `SP-503`
7. `SP-601` bis `SP-603`
8. `SP-701` bis `SP-705`

## Minimaler kritischer Pfad bis fachlich fertig

Folgende Tickets blockieren die fachlich fertige Web-App direkt:

- `SP-001`
- `SP-002`
- `SP-003`
- `SP-101`
- `SP-102`
- `SP-103`
- `SP-201`
- `SP-202`
- `SP-203`
- `SP-301`
- `SP-302`
- `SP-303`
- `SP-401`
- `SP-403`
- `SP-404`
- `SP-501`
- `SP-502`

## Abschlussbedingung

Das Backlog gilt erst dann als abgeschlossen, wenn:

- alle `P1`-Tickets abgeschlossen sind
- alle fachlich benoetigten `P2`-Tickets abgeschlossen sind
- kein Modul im Zielprozess mehr auf Mock oder Altwerkzeug angewiesen ist
- die Web-App gemaess Umsetzungsplan als vollstaendig fertig abgenommen werden kann