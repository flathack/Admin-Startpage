# Umsetzungsplan Admin Startpage

## Ziel des Dokuments

Dieses Dokument beschreibt die vollstaendige Umsetzungsplanung fuer die Admin Startpage als browserbasierte Web-Anwendung mit Docker-Backend, rollenbasierter Steuerung und vollstaendiger Uebernahme der benoetigten Fachlogik aus Rollout-Monitor und den angeschlossenen Zielsystemen.

Der Plan dient gleichzeitig als:

- Umsetzungsfahrplan fuer die weitere Entwicklung
- Priorisierungshilfe fuer die naechsten Migrationsschritte
- Grundlage fuer Aufwand, Abnahme und technische Entscheidungen

## Projektziel

Die Admin Startpage soll eine zentrale, lokale Betriebsoberflaeche fuer Administratoren bereitstellen. Die Anwendung soll bestehende Betriebsaufgaben aus Active Directory, Nutanix, Endpoint Central, vSphere, Citrix und Rollout in einer einheitlichen Web-Oberflaeche zusammenfassen.

Ziel ist nicht nur eine Navigationsseite, sondern eine fachlich nutzbare Plattform mit:

- AD-basierter Anmeldung
- rollen- und gruppenbasierter Rechtevergabe
- benutzerspezifischer Startseite
- klar getrennten Integrationsschichten
- vollstaendiger Ablösung der relevanten Funktionen aus Rollout-Monitor in der Web-App

## Verbindlicher Endzustand

Nach Abschluss aller Phasen dieses Plans gilt die Web-App als vollstaendig fertig. Das bedeutet konkret:

- alle vorgesehenen Hauptmodule sind fachlich nutzbar, nicht nur sichtbar
- alle benoetigten Live-Integrationen arbeiten ohne Mock-Modus
- alle kritischen Betriebsprozesse koennen vollständig in der Web-App ausgefuehrt werden
- alle schreibenden und destruktiven Aktionen sind serverseitig abgesichert und auditierbar
- der Windows-Connector liefert die benoetigten AD- und Citrix-On-Prem-Funktionen produktiv
- die Anwendung ist fuer den internen Dauerbetrieb dokumentiert, testbar und deploybar

Nicht Ziel dieses Plans ist ein weiterer Zwischenstand oder ein erweiterter Prototyp. Ziel ist die fachlich abgeschlossene Web-Anwendung.

## Ist-Stand

Der aktuelle Stand des Projekts ist ein funktionsfaehiger technischer Prototyp mit belastbarer Grundarchitektur.

Bereits umgesetzt:

- FastAPI-Backend mit Session-Handling
- Frontend als browserbasierte Single-Page-Oberflaeche
- Portainer-inspirierte Shell mit Sidebar und Modulnavigation
- Mock- und LDAP-basierte Authentifizierung
- Rollen- und Permission-Modell auf Basis von AD-Gruppen
- personalisierte Dashboard-Konfiguration pro Benutzer
- Integrationsuebersicht fuer AD, Nutanix, Endpoint Central, vSphere und Citrix
- optionaler Windows-Connector fuer Windows-nahe Speziallogik
- persistente Rollout-Jobs im Web-Backend
- Runtime-Datei-Anbindung fuer STATUS, CONTROL, NAME-MAP und ACK
- Synchronisation von Runtime-Zustaenden in gespeicherte Rollout-Jobs
- ASSIGN- und RESUME-Signale ueber CONTROL-Dateien
- erster aktiver Rollout-Start ueber Background-Worker im Mock-Modus

Noch nicht vollstaendig umgesetzt:

- echte Live-Ausfuehrung von Nutanix-basierten Rollout-Operationen
- vollstaendige Continue-, Resume-, Delete- und ReRollout-Workflows
- fachliche Umsetzung der AD-Unterbereiche DNS, DHCP und Auswertungen
- echte Citrix-On-Prem-Aktionen ueber den Windows-Connector
- vollstaendige Endpoint-/Zenworks-nahe Betriebsfunktionen
- Audit-, Logging- und Betriebsdiagnostik auf Produktionsniveau

Restziel bis Planende:

- saemtliche oben genannten Luecken muessen geschlossen sein
- Mock-Komponenten duerfen im Zielbetrieb keine fachliche Kernfunktion mehr blockieren
- die Web-App muss alle benoetigten Tagesgeschaefte ohne Rueckgriff auf Rollout-Monitor abdecken

## Zielarchitektur

Die Zielarchitektur besteht aus vier Schichten:

1. Frontend
   - Browserbasierte Bedienoberflaeche
   - modulare Navigation
   - rollenabhaengige Sichtbarkeit und Aktionen

2. Web-Backend
   - FastAPI fuer Authentifizierung, Fachlogik und REST-Endpunkte
   - Session-Verwaltung und serverseitige Rechtepruefung
   - zentrale Orchestrierung von Integrationen und Rollout-Prozessen

3. Integrationsschicht
   - containerfaehige REST-Integrationen fuer Nutanix, vSphere und Endpoint Central
   - normierte Service-Schicht je Zielsystem

4. Windows-Connector
   - Windows-spezifische PowerShell-/RSAT-/Citrix-Funktionen
   - gekapselte Spezialoperationen fuer AD und Citrix On-Prem

## Fachliche Zielmodule

Die Anwendung soll folgende Hauptmodule stabil bereitstellen:

- Dashboard
- ActiveDirectory
- Nutanix
- Endpoint Central
- Citrix
- Rollout

Geplante AD-Unterbereiche:

- AD Users & Computers
- Auswertungen
- DNS
- DHCP

## Leitprinzipien fuer die Umsetzung

- Sicherheit vor Komfort: Jede schreibende Aktion wird serverseitig authorisiert.
- Migration vor Komplettneubau: Vorhandene Logik aus Rollout-Monitor wird geordnet uebernommen, nicht neu erfunden.
- Kleine, verifizierbare Ausbauschritte: Jede groessere Funktion wird isoliert umgesetzt und getestet.
- Mock zuerst, live danach: UI- und API-Verhalten werden zuerst stabilisiert, danach wird die Live-Integration aktiviert.
- Windows-nahe Funktionen bleiben bewusst ausserhalb des Linux-Containers gekapselt.

## Umsetzungsstrategie

Die Umsetzung erfolgt in acht aufeinander aufbauenden Arbeitspaketen.

### Phase 1: Plattform haerten

Ziel:
Den bestehenden Prototypen auf einen belastbaren technischen Sockel fuer die weiteren Fachmodule bringen.

Umfang:

- Konfigurationsmodell weiter vereinheitlichen
- Fehlerbilder und Runtime-Warnings konsolidieren
- Session-Verhalten, Logout, Timeouts und Guard-Mechanismen absichern
- CORS-, Connector- und Runtime-Pruefungen weiter schaerfen
- Struktur fuer produktionsnaehes Logging vorbereiten

Ergebnis:

- stabiler technischer Unterbau fuer weitere Migration
- klar erkennbare Betriebs- und Konfigurationsfehler
- belastbare Basis fuer den vollstaendigen Live-Betrieb aller Module

Abnahme:

- Health-Endpoint meldet alle kritischen Fehlkonfigurationen sauber
- Login, Logout und Session-Ablauf sind nachvollziehbar testbar
- Mock- und Live-Modus sind eindeutig trennbar
- produktive Grundkonfiguration kann ohne manuelle Codeanpassungen betrieben werden

### Phase 2: Rollout-Live-Ausfuehrung auf Nutanix portieren

Ziel:
Den vorhandenen Rollout-Worker von einer reinen Mock-Orchestrierung auf echte Nutanix-Operationen erweitern.

Umfang:

- bestehende Nutanix-Logik aus Rollout-Monitor fachlich extrahieren
- Clone-/Provisionierungsablauf in eigene Service-Schicht uebernehmen
- VM-Erstellung, Statuspruefung und Boot-Sequenz abbilden
- Fehler- und Retry-Verhalten definieren
- Fortschrittsstufen aus Live-Operationen auf Web-Jobstatus mappen

Ergebnis:

- Rollout-Jobs koennen nicht nur gestartet, sondern real auf Nutanix angestossen werden
- der Rollout-Start ist nicht mehr von Mock-Schritten abhaengig

Abhaengigkeiten:

- stabile Nutanix-API-Anbindung
- brauchbare Zielparameter pro Rollout-Job
- definierte Statusabbildung zwischen Nutanix und Web-App

Abnahme:

- ein echter Rollout-Start fuehrt vollstaendig durch die Nutanix-seitige Bereitstellung bis zur Uebergabe an den weiteren Rollout-Prozess
- Fehlerfaelle werden im Jobstatus und API-Response nachvollziehbar sichtbar

### Phase 3: Continue-, Resume- und ACK-Workflow vervollstaendigen

Ziel:
Den bereits begonnenen Runtime-/Share-Ansatz auf einen vollstaendigen, robusten Rollout-Fortsetzungsprozess ausbauen.

Umfang:

- Continue- und Resume-Semantik mit Runtime-Dateien vollstaendig modellieren
- ACK-Verarbeitung haerten
- Registrierung, Name Request und Maschinenzuordnung stabilisieren
- Zwischenzustande und Wartezustaende sauber differenzieren
- Konfliktfaelle bei mehrfachen Zuordnungen definieren

Ergebnis:

- Web-App steuert nicht nur den Start, sondern auch die Fortsetzung laufender Rollouts kontrolliert
- Unterbrechungen koennen vollstaendig innerhalb der Web-App behandelt werden

Abnahme:

- Jobs koennen nach Unterbrechung gezielt fortgesetzt werden
- Statuswechsel zwischen Registrierung, Zuweisung, Ausfuehrung und Abschluss sind plausibel
- der vollstaendige Continue-/Resume-Pfad ist fachlich ohne Desktop-App nutzbar

### Phase 4: Delete- und ReRollout-Workflow portieren

Ziel:
Die wichtigsten betrieblichen Folgeoperationen aus Rollout-Monitor in die Web-App uebernehmen.

Umfang:

- Delete-Workflow fuer Jobs und Zielobjekte fachlich definieren
- ReRollout-Workflow modellieren
- Sicherheitspruefungen und Freigabemechanismen fuer destruktive Aktionen ergaenzen
- UI-Dialoge fuer risikobehaftete Aktionen einfuehren
- Audit-Trail fuer diese Aktionen vorbereiten

Ergebnis:

- zentrale Lifecycle-Aktionen fuer Rollout-Jobs stehen im Web zur Verfuegung
- Rollout-Lifecycle ist vollstaendig ueber die Web-App steuerbar

Abnahme:

- Delete und ReRollout sind nur mit passenden Rechten ausfuehrbar
- jede Aktion hinterlaesst nachvollziehbare Status- und Logdaten
- fuer den Rollout-Lifecycle ist kein Rueckgriff auf Rollout-Monitor mehr erforderlich

### Phase 5: ActiveDirectory fachlich ausbauen

Ziel:
Das AD-Modul von einer Struktur-/Navigationsbasis zu einem nutzbaren Admin-Modul weiterentwickeln.

Umfang:

- AD Users & Computers mit Such-, Detail- und benoetigten Verwaltungsfunktionen erweitern
- Auswertungen als benoetigte Reports und administrative Sichten integrieren
- DNS-Funktionen fachlich nutzbar fuer Lesen und definierte Schreiboperationen umsetzen
- DHCP-Funktionen fachlich nutzbar fuer Lesen und definierte Schreiboperationen umsetzen
- Connector-Schnittstellen fuer PowerShell-/RSAT-Aufrufe normieren

Ergebnis:

- das AD-Modul ist vollstaendig als Web-Modul nutzbar

Abhaengigkeiten:

- Windows-Connector muss belastbar angebunden sein
- Rechte- und Rollenmodell fuer AD-Unterfunktionen muss verfeinert werden

Abnahme:

- die benoetigten AD-, DNS- und DHCP-Funktionen sind aus der Web-App produktiv nutzbar
- zentrale AD-Tagesgeschaefte koennen ohne parallele Desktop-App bearbeitet werden

### Phase 6: Citrix-On-Prem ueber Connector vervollstaendigen

Ziel:
Die Citrix-Funktionen nicht nur als Uebersicht, sondern als fachlich nutzbare Operations-Schnittstelle bereitstellen.

Umfang:

- vorhandene Citrix-Logik aus Rollout-Monitor uebernehmen
- Connector-Endpunkte fuer Citrix-Sitzungen, Maschinen oder Bereitstellungsdaten erweitern
- Berechtigungen fuer Citrix-spezifische Aktionen ausbauen
- Fehler- und Timeout-Behandlung fuer Connector-Aufrufe verbessern

Ergebnis:

- Citrix wird als operatives Modul im Web nutzbar
- Citrix-On-Prem ist fuer die benoetigten Betriebsaktionen vollstaendig ueber den Connector angebunden

Abnahme:

- definierte Citrix-Live-Daten werden ueber den Connector korrekt geliefert
- die benoetigten Citrix-Aktionen sind aus der Web-App heraus live ausfuehrbar
- fuer die vorgesehenen Citrix-Prozesse ist kein Mock-Connector mehr erforderlich

### Phase 7: Endpoint Central, vSphere und weitere Betriebsfunktionen schliessen

Ziel:
Die restlichen Systemmodule aus der reinen Uebersicht in fachlich nutzbare Arbeitsmodule ueberfuehren.

Umfang:

- Endpoint-Central-Endpunkte fachlich erweitern
- vSphere-Leselogik absichern und relevante Aktionen definieren
- bestehende Bestandssysteme auf gemeinsame API- und Fehlerkonventionen bringen
- moegliche Zenworks- oder verwandte Restfunktionen einplanen, falls fachlich erforderlich

Ergebnis:

- die Startpage deckt die wesentlichen taeglichen Plattformfunktionen konsistent ab
- alle vorgesehenen Plattformmodule sind fachlich abgeschlossen

Abnahme:

- pro Zielsystem sind alle benoetigten End-to-End-Anwendungsfaelle der Web-App umgesetzt und validiert

### Phase 8: Betriebsreife, Audit und Deployment finalisieren

Ziel:
Die Anwendung fuer einen stabilen internen Dauerbetrieb vorbereiten.

Umfang:

- strukturiertes Logging und Fehlerkorrelation einfuehren
- Auditierbarkeit fuer schreibende Aktionen ausbauen
- Rollen- und Rechtezuordnung fachlich pruefen
- Backup-/Restore-Strategie fuer Konfigurations- und Jobdaten definieren
- Docker-Deployment und Betriebsdokumentation finalisieren
- Tests und Release-Checkliste einfuehren

Ergebnis:

- administrativ betreibbare Web-Anwendung mit nachvollziehbarer Betriebsbasis
- fachlich abgeschlossene und produktionsreife Web-Anwendung

Abnahme:

- definierte Kernablaeufe sind dokumentiert, testbar und deploybar
- der geplante Funktionsumfang ist vollstaendig umgesetzt und abgenommen
- fuer den Zielprozess ist keine Rueckfallnutzung des Altwerkzeugs mehr notwendig

## Arbeitspakete im Detail

### Arbeitspaket A: Authentifizierung und Berechtigungen

Offene Aufgaben:

- LDAP-Fehlerfaelle weiter absichern
- Gruppenmapping fuer Produktivbetrieb verifizieren
- feinere Rechte fuer AD-, Rollout- und Citrix-Aktionen definieren
- Session-Timeout und erneute Authentifizierung fuer kritische Aktionen pruefen

Ergebnis:

- tragfaehiges Sicherheitsmodell fuer produktive Nutzung
- endgueltiges Berechtigungsmodell fuer die fertige Web-App

### Arbeitspaket B: Rollout-Kernprozess

Offene Aufgaben:

- Live-Nutanix-Operationen portieren
- Worker-Zustandsmodell verfeinern
- Delete/ReRollout ergaenzen
- Fehlerwiederaufnahme und manuelle Eingriffe modellieren

Ergebnis:

- Rollout wird zum zentral nutzbaren Web-Modul statt nur zum Statusmonitor
- vollstaendige Rollout-Steuerung im Web ohne Funktionsluecke zum Altwerkzeug

### Arbeitspaket C: Connector-Strategie

Offene Aufgaben:

- AD-RSAT-Aufrufe standardisieren
- Citrix-Endpunkte erweitern
- Fehler-, Timeout- und Erreichbarkeitslogik verbessern
- Connector-Health und Versionierung sichtbarer machen

Ergebnis:

- klare Trennung zwischen Linux-/Containerlogik und Windows-naher Speziallogik
- produktiv nutzbarer Connector fuer alle benoetigten Windows-nahen Funktionen

### Arbeitspaket D: Frontend-Produktivisierung

Offene Aufgaben:

- Modulansichten weiter strukturieren
- Formulare und Aktionsdialoge absichern
- konsistente Lade-, Fehler- und Leerlaufzustaende einbauen
- Bedienbarkeit fuer taegliche Admin-Prozesse verbessern

Ergebnis:

- betriebstaugliche Oberflaeche statt rein technischer Demo
- vollstaendig nutzbare Admin-Oberflaeche fuer alle Zielmodule

### Arbeitspaket E: Monitoring, Logging und Audit

Offene Aufgaben:

- strukturierte Server-Logs
- Connector- und Integrationslogs
- Audit-Trail fuer schreibende Aktionen
- einfache Diagnoseansichten fuer Fehlerfaelle

Ergebnis:

- bessere Nachvollziehbarkeit und geringerer Analyseaufwand im Betrieb
- revisionsfaehige Betriebs- und Aktionsnachverfolgung

## Priorisierung

Prioritaet 1:

- Live-Nutanix-Rollout portieren
- Continue-/Resume-Workflow abschliessen
- Delete/ReRollout umsetzen

Prioritaet 2:

- AD-Unterbereiche fachlich ausbauen
- Citrix-Live-Funktionen ueber Connector liefern

Prioritaet 3:

- Endpoint/vSphere-Fachlogik erweitern
- Audit, Logging und Betriebsreife finalisieren

## Abhaengigkeiten

Technische Abhaengigkeiten:

- stabile API-Zugaenge fuer Nutanix, vSphere und Endpoint Central
- Windows-System fuer Connector-nahe AD- und Citrix-Funktionen
- definierte Dateifreigaben fuer Rollout-STATUS, CONTROL, NAME-MAP und ACK
- belastbare Umgebungsvariablen und Zugangsdaten

Fachliche Abhaengigkeiten:

- klare Definition, welche Rollout-Monitor-Funktionen verbindlich migriert werden muessen
- verbindliche Rollen- und Rechtezuordnung pro Modul und Aktion
- abgestimmte Regeln fuer Delete-, ReRollout- und Freigabeprozesse

## Risiken

- Unterschiedliche Laufzeitumgebungen zwischen Linux-Container und Windows-Admin-Tools
- Fachlogik aus Rollout-Monitor ist teilweise eng an Desktop-/Threading-Muster gebunden
- externe Systeme koennen sich in Verhalten, Antwortzeiten oder Authentifizierung unterscheiden
- schreibende Admin-Aktionen bergen hohes Risiko ohne saubere Rechte- und Auditlogik

Massnahmen:

- kritische Aktionen schrittweise aktivieren
- Live-Integrationen erst nach stabilen Mock- und API-Tests freigeben
- destruktive Funktionen mit zusaetzlichen Schutzmechanismen versehen

## Teststrategie

Die Umsetzung soll pro Phase getestet werden.

Testebenen:

- Service-Tests fuer zentrale Backend-Logik
- API-Tests fuer Auth, Rollout und Integrationen
- Integrationsnahe Tests fuer Runtime-Dateien und Connector-Endpunkte
- manuelle End-to-End-Tests fuer kritische Betriebsablaeufe

Pflichtfaelle fuer die naechsten Schritte:

- Login und Rollenaufloesung
- Rollout-Start und vollstaendige Ausfuehrung im Live-Modus
- Runtime-Sync einschliesslich ACK/Registrierung
- ASSIGN/RESUME/Delete/ReRollout-Aktionen mit Rechtepruefung
- Connector-Ausfall und Fehlerreaktion
- AD-, DNS-, DHCP-, Citrix-, Endpoint- und vSphere-Kernprozesse im Live-Betrieb

## Abnahmekriterien fuer die fertige Web-App

Die Web-App ist erst dann insgesamt fertig, wenn alle folgenden Punkte erfuellt sind:

- AD-Login, Rollenmapping und Session-Handling laufen produktiv stabil
- Dashboard, ActiveDirectory, Nutanix, Endpoint Central, Citrix und Rollout sind fachlich nutzbar
- alle benoetigten Live-Integrationen sind ohne Mock-Komponenten einsatzfaehig
- Rollout inklusive Start, Continue, Resume, Delete und ReRollout ist im Web abgeschlossen nutzbar
- AD-Unterbereiche Users & Computers, Auswertungen, DNS und DHCP sind fachlich umgesetzt
- Citrix-On-Prem-Funktionen laufen ueber den produktiven Windows-Connector
- Logging, Audit, Fehlerdiagnose und Deployment-Dokumentation sind vorhanden
- die benoetigten Betriebsprozesse koennen ohne Rueckgriff auf Rollout-Monitor abgewickelt werden

## Definition of Done

Ein Arbeitspaket gilt erst dann als abgeschlossen, wenn:

- die Funktion serverseitig sauber implementiert ist
- die Rechtepruefung vorhanden ist
- die Funktion im Frontend erreichbar und bedienbar ist
- Fehlerfaelle sichtbar behandelt werden
- der Ablauf dokumentiert oder im README/Plan nachgezogen wurde
- der Schritt validiert und commitbar ist

Das Gesamtprojekt gilt erst dann als abgeschlossen, wenn zusaetzlich:

- alle Phasen dieses Plans vollstaendig umgesetzt sind
- alle Hauptmodule live und ohne Mock-Abhaengigkeit arbeiten
- die Abnahmekriterien fuer die fertige Web-App erfuellt sind
- die Web-App den vorgesehenen Altprozess vollstaendig ersetzt

## Vorschlag fuer die naechste Umsetzungsreihenfolge

1. Live-Nutanix-Ausfuehrung im Rollout-Worker
2. Continue-/Resume-Workflow vollenden
3. Delete- und ReRollout-Workflow portieren
4. AD-Unterbereiche fachlich anbinden
5. Citrix-Live-Funktionen ueber Connector ausbauen
6. Endpoint-/vSphere-Funktionen erweitern
7. Audit, Logging und Betriebsdokumentation finalisieren

## Aufwandsschaetzung

Auf Basis des aktuellen Projektstands ist fuer die fachlich wesentlichen Restarbeiten von grob 9 bis 12 weiteren konzentrierten Umsetzungs-Commits auszugehen.

Eine realistische Verteilung waere:

- 2 bis 3 Commits fuer Live-Rollout auf Nutanix
- 1 bis 2 Commits fuer Continue-/Resume-/Delete-/ReRollout-Haertung
- 2 bis 3 Commits fuer AD- und Citrix-Fachmodule
- 1 bis 2 Commits fuer Endpoint/vSphere-Erweiterungen
- 1 bis 2 Commits fuer Audit, Logging, Deployment und Abschlussarbeiten

Die tatsaechliche Anzahl haengt davon ab, wie viel der Rollout-Monitor-Fachlogik 1:1 uebernommen werden kann und wie stark produktive Sicherheitsanforderungen die schreibenden Aktionen einschraenken.

## Zielaussage

Dieser Plan ist so zu verstehen, dass nach seiner vollstaendigen Umsetzung keine fachlich relevante Restmigration mehr offen ist. Nach Planende soll die Admin Startpage als vollwertige, betriebsreife Web-App einsetzbar sein.

Die operative Zerlegung in konkrete Tickets befindet sich in [UMSETZUNGSBACKLOG.md](UMSETZUNGSBACKLOG.md).

## Empfehlung

Der technisch sinnvollste naechste Schritt bleibt die Portierung der echten Nutanix-Rollout-Ausfuehrung. Sie ist der groesste verbleibende Kernblock auf dem Weg zur vollstaendig fertigen Web-App.