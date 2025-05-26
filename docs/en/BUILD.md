# BUILD.md

## 🏗️ Build process overview

The project uses **Docker** to containerize all components. The build process is fully defined via `docker-compose` and supports both local development and automated deployment.

---

## 📁 Directory structure for builds

Each main component has its own directory with:
- `Dockerfile`: Definition of the container image
- `requirements.txt`: Python dependencies

### Example structure:
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

## ⚙️ Build steps

### 1. requirements

- Docker (v20+ recommended)
- Docker Compose (v2.0+ integrated)
- Optional: `python3` + `pip` (for local tools)

### 2nd build via Docker Compose

```bash
docker-compose build
````

This creates all defined services:

- `client`
- `dispatcher`
- `nameservice`
- `monitoring`
- `worker-<type>` (multiple)

### 3. single service build

```bash
docker-compose build <service-name>
````

Example:

```bash
docker-compose build worker-reverse
```

---

## 🧪 Local execution (without Docker)

For development and debugging purposes, individual components can also be executed directly locally, e.g:

```bash
pip install -r shared/requirements.txt
python dispatcher/dispatcher.py
````

Note: Network communication may have to be adapted (ports, hostnames).

---

## 🔁 Rebuild for changes

For code or dependency changes:

```bash
docker-compose build --no-cache
```

---

## 📂 Artifacts

- **Docker images**: individual for each component
- **Volumes**: persistent data, e.g. logs (`/logs`)
- **`workers.json`**: central configuration file for workers

---

## 🧰 Help tools

The `devtools/` directory contains tools to support the build:

- `compose_generator.py`: generates Docker Compose files
- `runner.py`: executes containers automatically after configuration

---

## ✅ Best practices

- Use separate images per worker type for clear separation
- Build only changed services for faster workflow
- Use logs via volume sharing for simplified debugging

---

## 🚧 Troubleshooting

| Problem | Solution |
|--------|--------|
| Port collision | Check `docker-compose.yml` for duplicate ports |
| Container does not start | Check logs with `docker-compose logs <service>` |
| Build error | `--no-cache` or use `docker system prune` |

Translated with DeepL.com (free version)