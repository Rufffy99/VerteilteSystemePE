# TaskGrid+ – Build & Deployment Instructions

This document describes how to build, configure, and run the TaskGrid+ system using Docker and Docker Compose.

---

## 🐳 Prerequisites

- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/)

---

## 📁 Project Structure (Simplified)

```
.
├── client/
├── dispatcher/
├── worker/
│   └── worker_types/
├── nameservice/
├── monitoring/
├── shared/
├── docker-compose.yml
└── docs/
```

---

## 🔨 Build the Project

To build all containers using Docker Compose:

```bash
docker-compose build
```

This will:
- Build a Docker image for each component using its Dockerfile
- Install required dependencies (e.g., `Flask` for monitoring)
- Copy shared modules (e.g., `shared/`) into each build context

---

## 🚀 Start the System

Launch all services using:

```bash
docker-compose up
```

This will start the following services:

- `nameservice`
- `dispatcher`
- One or more `worker-*` containers
- `client` (manually run commands)
- `monitoring`

---

## ▶️ Running Client Commands

### Submit a Task
```bash
docker-compose run client send reverse "Hello world"
```

### Query Result
```bash
docker-compose run client result 1
```

---

## 🧪 Adding Workers

To run a worker of a specific type, extend `docker-compose.yml` like this:

```yaml
  worker-uppercase:
    build: ./worker
    command: ["python", "worker.py", "upper"]
    ports:
      - "6002:6000"
    depends_on:
      - dispatcher
      - nameservice
```

Or launch from command line (optional):

```bash
docker-compose run worker python worker.py upper
```

---

## 🧹 Cleaning Up

To stop and remove all containers:

```bash
docker-compose down
```

To rebuild cleanly:

```bash
docker-compose down -v --remove-orphans
docker-compose build --no-cache
```

---

## 🛠 Troubleshooting

- Ensure the container names match your Compose service names (e.g. `dispatcher`, `nameservice`)
- Use `docker-compose logs` for debugging
- If using shared code (`shared/`), ensure it's copied correctly into each image

---

## 📦 Environment Notes

- Each component runs in its own container
- Networking is handled by Docker Compose's internal DNS
- Ports can be mapped externally if needed (see `ports:` section)
