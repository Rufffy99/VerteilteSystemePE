# TECHNOLOGIES.md

## ⚙️ Overview

This project uses modern technologies from the areas of containerization, network communication and distributed systems. The focus is on simple expandability, clear separation of components and standardized interfaces.

---

## 🧠 Programming language

- Python 3.10+**
  - Main language for all services
  - Use of modern features such as `dataclasses`, `asyncio`, `json`, `socket`

---

## 🐳 Containerization

- Docker
  - Each component is an independent Docker container
  - Multi-stage Dockerfiles optionally possible

- Docker Compose**
  - Version: 3.9
  - Orchestrates all services locally or in the CI

---

## 🌐 Network & Communication

| Domain | Technology | Purpose |
|----------------|---------------|-------------------------------------|
| Client ↔ Dispatcher | HTTP (REST) | Submit Tasks |
| Dispatcher ↔ Nameservice | HTTP | Worker Query |
| Dispatcher ↔ Worker | UDP | Task Forwarding & Feedback |
| Monitoring ↔ Docker | Docker API | Status Information & Logs |

- UDP communication requires timeout and retry mechanisms
- Internal Docker network name `tasknet` for service communication

---

## 📦 Data formats & protocols

- **JSON** as a standardized format for:
  - Task Requests
  - Worker Responses
  - Registry queries

- **Internal protocols:**
  - `protocol.py` defines message types
  - `task.py` models tasks

---

## 🧪 Development tools

- Python tools (devtools/):**
  - `runner.py`: Starts components locally
  - `compose_generator.py`: Dynamic compose file generation

- **Testing:** Unittest-based + manual simulations via `test_client_simulation.py`

---

## 📊 Logging

- Each service writes logs to a shared volume (`/logs`)
- Access via mounted volumes in Docker Compose
- Standardized format via `utils.py`

---

## 🗂 Configuration files

| file | purpose |
|---------------------|-------------------------------|
| `docker-compose.yml` | container definitions |
| `workers.json` | active worker types + meta |
| `registry.json` | registered worker list |
| `requirements.txt` | Python dependencies per module |

---

## 🔐 Security & isolation

- No ports exposed to the outside (except manually via Compose)
- UDP only used internally
- Access to Docker API only allowed from monitoring

---

## 🧩 Extensibility

- New workers = new entry args in `worker.py` + entry in `workers.json`
- New components can be easily integrated via Compose & common protocols