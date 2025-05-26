# TECHNOLOGIES.md

## ⚙️ Überblick

Dieses Projekt nutzt moderne Technologien aus den Bereichen Containerisierung, Netzwerkkommunikation und verteilte Systeme. Der Fokus liegt auf einfacher Erweiterbarkeit, klarer Trennung der Komponenten und standardisierten Schnittstellen.

---

## 🧠 Programmiersprache

- **Python 3.10+**
  - Hauptsprache für sämtliche Services
  - Nutzung moderner Features wie `dataclasses`, `asyncio`, `json`, `socket`

---

## 🐳 Containerisierung

- **Docker**
  - Jede Komponente ist ein eigenständiger Docker-Container
  - Multi-Stage Dockerfiles optional möglich

- **Docker Compose**
  - Version: 3.9
  - Orchestriert alle Services lokal oder im CI

---

## 🌐 Netzwerk & Kommunikation

| Bereich        | Technologie   | Zweck                              |
|----------------|---------------|-------------------------------------|
| Client ↔ Dispatcher | HTTP (REST)   | Aufgaben einreichen                |
| Dispatcher ↔ Nameservice | HTTP        | Worker-Abfrage                     |
| Dispatcher ↔ Worker | UDP          | Aufgabenweitergabe & Rückmeldung  |
| Monitoring ↔ Docker | Docker API   | Statusinformationen & Logs        |

- UDP-Kommunikation erfordert Timeout- und Retry-Mechanismen
- Interner Docker-Netzwerkname `tasknet` für Service-Kommunikation

---

## 📦 Datenformate & Protokolle

- **JSON** als einheitliches Format für:
  - Task Requests
  - Worker Responses
  - Registry-Abfragen

- **Interne Protokolle:**
  - `protocol.py` definiert Nachrichtentypen
  - `task.py` modelliert Aufgaben

---

## 🧪 Entwicklungstools

- **Python-Tools (devtools/):**
  - `runner.py`: Startet Komponenten lokal
  - `compose_generator.py`: Dynamische Compose-Dateierzeugung

- **Testing:** Unittest-basiert + manuelle Simulationen via `test_client_simulation.py`

---

## 📊 Logging

- Jeder Service schreibt Logs in ein gemeinsames Volume (`/logs`)
- Zugriff über gemountete Volumes in Docker Compose
- Standardisiertes Format über `utils.py`

---

## 🗂 Konfigurationsdateien

| Datei               | Zweck                         |
|---------------------|-------------------------------|
| `docker-compose.yml` | Container-Definitionen        |
| `workers.json`       | Aktive Worker-Typen + Meta    |
| `registry.json`      | Registrierte Worker-Liste     |
| `requirements.txt`   | Python-Abhängigkeiten pro Modul |

---

## 🔐 Sicherheit & Isolation

- Keine Ports nach außen exponiert (außer manuell via Compose)
- UDP nur intern verwendet
- Zugriff auf Docker-API nur vom Monitoring erlaubt

---

## 🧩 Erweiterbarkeit

- Neue Worker = neue Entry-Args in `worker.py` + Eintrag in `workers.json`
- Neue Komponenten leicht integrierbar via Compose & gemeinsame Protokolle
