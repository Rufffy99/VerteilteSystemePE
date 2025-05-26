# COMMUNICATION.md

## 📡 Kommunikationsübersicht

Das System basiert auf einer hybriden Kommunikationsarchitektur:
- **HTTP** wird für Client-Dispatcher-Interaktion verwendet.
- **UDP** wird für die interne Kommunikation zwischen Dispatcher und Workern genutzt.
- **Monitoring** verwendet die Docker-Engine-API zur Statusüberwachung.

---

## 🔗 Kommunikationswege

### 1. Client → Dispatcher
- **Protokoll:** HTTP
- **Methode:** POST
- **Zweck:** Senden von Aufgaben (Tasks)
- **Datenformat:** JSON
- **Port:** 4000
- **Beispiel:**
  ```json
  {
    "type": "reverse",
    "payload": "OpenAI"
  }
  ```

---

### 2. Dispatcher → Nameservice
- **Protokoll:** HTTP
- **Zweck:** Abruf registrierter Worker für bestimmten Task-Typ
- **Port:** 5001
- **Antwort:** IP/Port eines passenden Workers

---

### 3. Dispatcher → Worker
- **Protokoll:** UDP
- **Zweck:** Versand der Aufgabe zur Bearbeitung
- **Mechanismus:**
  - Der Dispatcher verschickt ein UDP-Paket mit dem serialisierten Task.
  - Der Worker horcht auf Port 6000.
- **Port (intern):** 6000 (fest für alle Worker, extern durch Compose gemappt)
- **Datenformat:** JSON, serialisiert

---

### 4. Worker → Dispatcher (Antwort)
- **Protokoll:** UDP
- **Zweck:** Rückgabe des Ergebnisses
- **Mechanismus:**
  - Der Worker sendet das Resultat zurück an die Absenderadresse.
  - Die Rückmeldung enthält Ergebnis + Metadaten.

---

### 5. Monitoring → Docker
- **Protokoll:** Docker Engine API (Unix Socket)
- **Datei:** `/var/run/docker.sock`
- **Zweck:** Container-Status, Health Checks, Log-Auswertung

---

## 🔐 Sicherheitsaspekte

- UDP ist verbindungslos: keine garantierte Zustellung → einfache Retry-Logik nötig
- JSON-Nachrichten enthalten keine sensitiven Daten
- Interne Kommunikation erfolgt im privaten Docker-Netzwerk (`tasknet`)
- Kein externer Zugriff auf UDP-Ports durch Docker Compose

---

## 🧪 Beispiel-Kommunikationsablauf

```plaintext
Client --> Dispatcher (HTTP POST)
Dispatcher --> Nameservice (HTTP GET)
Dispatcher --> Worker (UDP SEND)
Worker --> Dispatcher (UDP REPLY)
Dispatcher --> Client (HTTP Response)
```

---

## 📦 Nachrichtenstruktur (UDP)

```json
{
  "id": "task-123",
  "type": "sum",
  "payload": "1,2,3,4"
}
```

Antwort:
```json
{
  "id": "task-123",
  "result": 10
}
```

---

## 🧰 Tools & Formate

- **Serialisierung:** JSON über UDP (Text-basiert)
- **Fehlerbehandlung:** Worker-Timeout + Logging im Dispatcher
- **Broadcasts:** nicht verwendet – direkte Punkt-zu-Punkt-Kommunikation

---

## 🔁 Wiederholungen & Fehlerbehandlung

- UDP verliert ggf. Pakete – Dispatcher implementiert Timeouts & Wiederholungen
- Keine Bestätigung durch Worker → Dispatcher wertet Rückkanal aktiv aus
