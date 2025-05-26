# INTERFACES.md

## 🎯 Übersicht der Schnittstellen

Dieses Dokument beschreibt die internen und externen Schnittstellen der Systemkomponenten. Dabei werden die Interaktionen zwischen den Modulen sowie deren Protokolle, Endpunkte und Formate definiert.

---

## 🌐 Externe Schnittstellen

### 1. Client → Dispatcher

- **Art:** HTTP REST
- **Methode:** POST
- **Endpoint:** `http://dispatcher:4000/task`
- **Beschreibung:** Der Client sendet eine Aufgabe zur Verarbeitung.
- **Request Body (JSON):**
  ```json
  {
    "type": "reverse",
    "payload": "OpenAI"
  }
  ```
- **Response Body (JSON):**
  ```json
  {
    "id": "task-abc123",
    "result": "IAnepO"
  }
  ```

---

## 🔁 Interne Schnittstellen

### 2. Dispatcher → Nameservice

- **Art:** HTTP GET
- **Endpoint:** `http://nameservice:5001/lookup/<task_type>`
- **Beschreibung:** Abfrage, welcher Worker für einen Task-Typ registriert ist.
- **Response:**
  ```json
  {
    "host": "worker-reverse",
    "port": 6000
  }
  ```

---

### 3. Dispatcher → Worker

- **Art:** UDP Socket
- **Adresse:** IP + Port 6000
- **Beschreibung:** Serialisierte Nachricht mit dem Task wird via UDP verschickt.
- **Payload:**
  ```json
  {
    "id": "task-001",
    "type": "sum",
    "payload": "1,2,3"
  }
  ```

---

### 4. Worker → Dispatcher (Antwort)

- **Art:** UDP Socket
- **Adresse:** Rückkanal der Absenderadresse
- **Beschreibung:** Worker sendet Ergebnis zurück
- **Payload:**
  ```json
  {
    "id": "task-001",
    "result": 6
  }
  ```

---

### 5. Monitoring → Docker Engine

- **Art:** Unix Socket (`/var/run/docker.sock`)
- **Beschreibung:** Containerstatus via Docker-API
- **Funktion:** Visualisierung & Health Checks
- **Beispiele:**
  - Status: `GET /containers/json`
  - Logs: `GET /containers/<id>/logs`

---

## 📂 Gemeinsame Datenstrukturen

### Task

```json
{
  "id": "task-uuid",
  "type": "worker_type",
  "payload": "<string>"
}
```

### Result

```json
{
  "id": "task-uuid",
  "result": "<computed_value>"
}
```

---

## 🛡 Fehlerfälle & Verhalten

- **Ungültiger Task-Typ:** Dispatcher gibt 400-Fehler an Client
- **Kein Worker registriert:** Dispatcher gibt 404 zurück
- **UDP-Zeitüberschreitung:** Dispatcher wartet mit Timeout und gibt 504 zurück

---

## 🔧 Konfigurierbare Parameter

- Worker-Typen und Aktivierungsstatus: `workers.json`
- UDP-Timeouts und Retries: im Dispatcher-Skript konfiguriert
- Portzuweisungen: `docker-compose.yml`

---

## 🔄 Zusammenfassung

| Von            | An              | Protokoll | Format | Beschreibung                      |
|----------------|------------------|-----------|--------|-----------------------------------|
| Client         | Dispatcher       | HTTP      | JSON   | Sendet neue Aufgaben              |
| Dispatcher     | Nameservice      | HTTP      | JSON   | Sucht zuständigen Worker          |
| Dispatcher     | Worker           | UDP       | JSON   | Leitet Task zur Verarbeitung      |
| Worker         | Dispatcher       | UDP       | JSON   | Rückgabe des Ergebnisses          |
| Monitoring     | Docker API       | Socket    | JSON   | Holt Status & Logs der Container  |
