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
├── monitoring/         # Basic REST monitoring interface
├── shared/             # Shared data structures and protocol
├── docker-compose.yml  # Compose file to launch the system
└── docs/               # Documentation and test protocols
```

---

## 🚀 Quickstart

Build and start the system
```bash
docker-compose build
docker-compose up
```

Submit a task via client
```bash
docker-compose run client send reverse "Hello World"
```

Query the result of task ID 1
```bash
docker-compose run client result 1
```

---

## 🛠️ Extending Task Types

To add a new task type:
	1.	Create a new Python file in worker/worker_types/, e.g. foobar.py
	2.	Implement a handle(payload: str) -> str function
	3.	That’s it — the system will automatically detect the new type.


---

## 📦 Dependencies

	•	Python 3.11
	•	Docker, Docker Compose
	•	Flask (for monitoring only)