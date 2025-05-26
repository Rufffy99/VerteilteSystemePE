# WORKFLOW.md

## 🔄 Systemworkflow: Task-Verarbeitung von A bis Z

Dieses Dokument beschreibt den vollständigen Ablauf eines Tasks im System – vom Eingang über die Verarbeitung bis zur Ergebnislieferung. Der Fokus liegt auf dem Zusammenspiel der Komponenten und den Datenflüssen.

---

## 🧭 Ablaufübersicht

```plaintext
[1] Client → Dispatcher (HTTP)
[2] Dispatcher → Nameservice (HTTP)
[3] Dispatcher → Worker (UDP)
[4] Worker → Dispatcher (UDP)
[5] Dispatcher → Client (HTTP)
```

---

## 🧾 Schritt-für-Schritt

### 1. Client sendet Aufgabe

- Der Benutzer gibt eine Aufgabe über das CLI-Frontend ein.
- Beispiel: „Reversiere den String `hello world`“.
- Der Client verpackt den Task in ein JSON und sendet ihn per HTTP an den Dispatcher.

```json
POST /task
{
  "type": "reverse",
  "payload": "hello world"
}
```

---

### 2. Dispatcher kontaktiert Nameservice

- Der Dispatcher ruft `/lookup/reverse` auf.
- Der Nameservice durchsucht die Registry (`registry.json`) nach einem registrierten Worker dieses Typs.
- Rückgabe: IP und Port (z. B. `worker-reverse:6000`).

---

### 3. Dispatcher sendet Task an Worker

- Der Task wird über ein UDP-Paket an den `worker-reverse` geschickt.
- Inhalt: serialisierter Task inklusive `id`, `type`, `payload`.

---

### 4. Worker verarbeitet und antwortet

- Der Worker empfängt die Nachricht, erkennt seinen Typ (`reverse`) und verarbeitet die Payload.
- Das Ergebnis (`"dlrow olleh"`) wird über ein UDP-Paket an den Absender (Dispatcher) zurückgesendet.

---

### 5. Dispatcher sendet Antwort an Client

- Der Dispatcher erhält die Antwort und mappt sie zur ursprünglichen Anfrage.
- Antwort per HTTP zurück an den Client:

```json
{
  "id": "task-001",
  "result": "dlrow olleh"
}
```

---

## 🧩 Sonderfälle

### 🔁 Keine Antwort vom Worker

- Dispatcher wartet mit Timeout.
- Bei keiner Antwort: Retry oder Fehler an Client.

### 🧍 Kein Worker registriert

- Dispatcher erhält 404 vom Nameservice.
- Antwort an Client: Fehler `"No worker available for type <x>"`.

---

## 🧠 Interne Datenflüsse

- `task_id` wird im Dispatcher generiert.
- Logging erfolgt in jedem Schritt in `/logs/`.
- UDP-Kommunikation ist zustandslos – Antworten müssen anhand von `task_id` zugeordnet werden.

---

## 🔍 Beobachtbarkeit

- Der Monitoring-Service zeigt:
  - Aktive Container
  - Registrierte Worker
  - Fehler oder Inaktivität
- Zugriff via Web-Oberfläche (Port 8080)

---

## 🧪 Beispiel (Summe)

```json
POST /task
{
  "type": "sum",
  "payload": "1,2,3"
}
```

Antwort:

```json
{
  "id": "task-xyz",
  "result": 6
}
```

---

## 🧵 Zusammenfassung des Workflows

| Schritt | Quelle     | Ziel         | Protokoll | Inhalt         |
|--------|------------|--------------|-----------|----------------|
| 1      | Client     | Dispatcher   | HTTP      | Task Request   |
| 2      | Dispatcher | Nameservice  | HTTP      | Worker-Lookup  |
| 3      | Dispatcher | Worker       | UDP       | Task           |
| 4      | Worker     | Dispatcher   | UDP       | Ergebnis       |
| 5      | Dispatcher | Client       | HTTP      | Response       |
