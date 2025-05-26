# TaskGrid+

**TaskGrid+** is a modular, distributed task processing system using Docker containers and UDP communication. It allows dynamic registration and resolution of worker services via a nameservice, and supports the extension of task types through simple module addition.

---

## 🧩 Features

- Distributed task management using Dispatcher and Workers
- Dynamic service discovery via custom Nameservice
- Modular task processing (e.g. `reverse`, `sum`, `hash`, `upper`, `wait`)
- UDP-based communication between all components
- Monitoring via REST API
- Fully containerized using Docker Compose

---

## 🗂️ Project Structure

```plaintext
.
├── client/             # Sends tasks and queries results
├── dispatcher/         # Queues, dispatches tasks, stores results
├── worker/             # Dynamically loaded workers by type
│   └── worker_types/   # Task type handlers (e.g. reverse.py)
├── nameservice/        # Worker registry & lookup service
├── monitoring/         # REST-based monitoring dashboard
├── shared/             # Shared protocol & models
├── devtools/           # CLI tools and compose generator
├── docs/               # Documentation and test protocols
├── docker-compose.yml              # Legacy fallback compose file
├── docker-compose.generated.yml    # Dynamically generated compose file
├── workers.json                   # Active workers list
├── start.py                       # Unified CLI entry point
├── start.man.txt                  # CLI manual
└── requirements.txt               # Python dependencies
```

---

## 🚀 Quickstart

Run everything with one command:

```bash
python start.py build --reset --no-cache -d
```

To view the manual:

```bash
python start.py --man
```

You can also regenerate only the compose file:

```bash
python start.py regen-compose
```

Or reset everything:

```bash
python start.py reset
```

---

## 🛠️ Extending Task Types

To add a new task type:

1. Create a Python file in `worker/worker_types/`, e.g. `foobar.py`
2. Implement a `handle(payload: str) -> str` function
3. Add the worker to `workers.json` in the root:

```json
{
  "workers": [
    {
      "name": "foobar",
      "active": true,
      "description": "Does something useful with the input string."
    }
  ]
}
```

Workers from `workers.json` will be auto-launched with `start.py build`.