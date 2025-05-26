# ARCHITECTURE.md

## 🔄 Übersicht

Dieses System ist eine modulare verteilte Architektur zur Aufgabenverarbeitung, bestehend aus mehreren spezialisierten Services, die containerisiert und orchestriert via Docker Compose betrieben werden. Der Aufbau folgt einem Microservice-Ansatz mit klar definierten Zuständigkeiten je Komponente.

---

## 🔹 Komponentenübersicht

### 1. **Client** (`client/`)
- **Zweck:** CLI zur Interaktion mit dem Dispatcher
- **Funktion:** Aufgaben definieren und absenden
- **Kommunikation:** HTTP-Anfragen an den Dispatcher

### 2. **Dispatcher** (`dispatcher/`)
- **Zweck:** Zentrale Steuerinstanz
- **Funktion:** Entgegennahme von Tasks vom Client, Routing an passende Worker
- **Kommunikation:**
  - Empfängt HTTP von Client
  - Sucht Worker via Nameservice
  - Leitet Tasks via UDP/HTTP an Worker weiter

### 3. **Nameservice** (`nameservice/`)
- **Zweck:** Service Discovery
- **Funktion:** Registrierung und Lookup aktiver Worker anhand ihrer Typen
- **Datenhaltung:** JSON-Registry (`registry.json`)

### 4. **Worker (5 Instanzen)** (`worker/`)
- **Zweck:** Task-Spezialisierung
- **Typen:**
  - `reverse`
  - `hash`
  - `sum`
  - `upper`
  - `wait`
- **Start via:** `worker.py <type>`
- **Kommunikation:** UDP-Server erwartet Anfragen vom Dispatcher

### 5. **Monitoring** (`monitoring/`)
- **Zweck:** Beobachtung des Systems
- **Funktion:** Anzeige des Status aktiver Container und registrierter Worker
- **Besonderheiten:** Zugriff auf Docker-Socket (`/var/run/docker.sock`)

### 6. **Shared Module** (`shared/`)
- **Funktion:** Gemeinsame Strukturen (z. B. Protokolle, Hilfsfunktionen)
- **Beispiele:**
  - `protocol.py`: Nachrichtendefinition
  - `task.py`: Repräsentation von Tasks
  - `utils.py`: Logging & Serialisierung

### 7. **Devtools** (`devtools/`)
- **Tools für lokale Entwicklung:**
  - `compose_generator.py`: Erzeugt Docker-Compose-Dateien
  - `runner.py`: Startet das System lokal kontrolliert

---

## 🤖 Laufzeitstruktur

```plaintext
Client
  |
  v
Dispatcher <-----> Nameservice
  |
  v
Worker [hash, reverse, ...]
  |
  v
Monitoring
```

- Der **Client** sendet Tasks an den **Dispatcher**.
- Der **Dispatcher** kontaktiert den **Nameservice**, um den passenden **Worker** zu finden.
- Der gewählte **Worker** bearbeitet den Task und sendet das Ergebnis zurück.
- Der **Monitoring-Service** beobachtet das gesamte System und stellt Statusinformationen bereit.

---

## 🛠 Technologie-Stack

| Komponente      | Technologie             |
|----------------|--------------------------|
| Containerisierung | Docker, Docker Compose |
| Sprache         | Python 3                |
| Kommunikation   | HTTP, UDP               |
| Monitoring      | Python + Docker API     |

---

## 📈 Skalierbarkeit & Modularität

- Neue Worker-Typen lassen sich durch Hinzufügen neuer Entrypoints in `worker.py` und `workers.json` ergänzen.
- Die Komponenten können getrennt entwickelt, getestet und deployed werden.
- Kommunikation über standardisierte Protokolle ermöglicht flexible Erweiterbarkeit.

---

## ⚖️ Verantwortlichkeiten & Trennung

- **Single Responsibility Principle** auf Systemebene angewendet
- Jedes Modul fokussiert auf genau eine Aufgabe:
  - Dispatcher = Routing
  - Nameservice = Lookup
  - Worker = Processing
  - Client = Input/Output
  - Monitoring = Beobachtung

---

## 🚀 Fazit

Diese Architektur ermöglicht ein flexibles, nachvollziehbares und erweiterbares Task-Verarbeitungssystem mit klar definierten Schnittstellen und Zuständigkeiten. Sie eignet sich für den Einsatz in Entwicklungs- und Testumgebungen mit Fokus auf Modularität und Sichtbarkeit der Abläufe.
