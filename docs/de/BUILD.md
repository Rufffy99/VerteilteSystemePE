# BUILD.md

## 🏗️ Build-Prozessübersicht

Das Projekt verwendet **Docker** zur Containerisierung aller Komponenten. Der Build-Prozess ist vollständig über `docker-compose` definiert und unterstützt sowohl lokale Entwicklung als auch automatisiertes Deployment.

---

## 📁 Verzeichnisstruktur für Builds

Jede Hauptkomponente besitzt ein eigenes Verzeichnis mit:
- `Dockerfile`: Definition des Container-Images
- `requirements.txt`: Python-Abhängigkeiten

### Beispielstruktur:
```
client/
  ├── Dockerfile
  └── requirements.txt
dispatcher/
  ├── Dockerfile
  └── requirements.txt
...
```

---

## ⚙️ Build-Schritte

### 1. Voraussetzungen

- Docker (v20+ empfohlen)
- Docker Compose (v2.0+ integriert)
- Optional: `python3` + `pip` (für lokale Tools)

### 2. Build via Docker Compose

```bash
docker-compose build
```

Dies erstellt alle definierten Services:

- `client`
- `dispatcher`
- `nameservice`
- `monitoring`
- `worker-<type>` (mehrfach)

### 3. Einzelner Service-Build

```bash
docker-compose build <service-name>
```

Beispiel:

```bash
docker-compose build worker-reverse
```

---

## 🧪 Lokale Ausführung (ohne Docker)

Für Entwicklungs- und Debugzwecke lassen sich einzelne Komponenten auch direkt lokal ausführen, z. B.:

```bash
pip install -r shared/requirements.txt
python dispatcher/dispatcher.py
```

Hinweis: Dabei muss Netzwerkkommunikation ggf. angepasst werden (Ports, Hostnames).

---

## 🔁 Rebuild bei Änderungen

Bei Code- oder Abhängigkeitsänderungen:

```bash
docker-compose build --no-cache
```

---

## 📂 Artefakte

- **Docker Images**: für jede Komponente individuell
- **Volumes**: persistente Daten, z. B. Logs (`/logs`)
- **`workers.json`**: zentrale Konfigurationsdatei für Worker

---

## 🧰 Hilfstools

Im Verzeichnis `devtools/` befinden sich Werkzeuge zur Unterstützung des Builds:

- `compose_generator.py`: generiert Docker-Compose-Dateien
- `runner.py`: führt Container automatisch nach Konfiguration aus

---

## ✅ Best Practices

- Verwende getrennte Images pro Worker-Typ für klare Trennung
- Baue nur geänderte Services für schnelleren Workflow
- Nutze Logs via Volume-Sharing für vereinfachtes Debugging

---

## 🚧 Troubleshooting

| Problem | Lösung |
|--------|--------|
| Port-Kollision | Prüfe `docker-compose.yml` auf doppelte Ports |
| Container startet nicht | Logs mit `docker-compose logs <service>` prüfen |
| Build-Fehler | `--no-cache` oder `docker system prune` verwenden |
