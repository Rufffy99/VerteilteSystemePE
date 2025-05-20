# TaskGrid+ – System Architecture

This document describes the architectural structure, design principles, and responsibilities of each component within the TaskGrid+ distributed task processing system.

## 🧱 Architectural Overview

```
                +------------------------+
                |        Client          |
                |------------------------|
                | send_task(),           |
                | request_result()       |
                +-----------+------------+
                            |
                            ▼
                +-----------+------------+
                |        Dispatcher       |
                |------------------------|
                | Queueing, Worker lookup|
                | Result collection      |
                +-----------+------------+
                            |
            +---------------+---------------+
            |                               |
            ▼                               ▼
 +-------------------+          +-------------------+
 |   Worker: reverse  |   ...    |   Worker: sum     |
 |-------------------|          |-------------------|
 | process_task()     |         | process_task()     |
 +-------------------+         +-------------------+
            ▲                               ▲
            |                               |
    (UDP to Dispatcher)            (UDP to Dispatcher)

                            ▲
                            |
                            ▼
              +--------------------------+
              |      NameService         |
              |--------------------------|
              | Worker registration      |
              | Type → Address mapping   |
              +--------------------------+

                            ▲
                            |
                            ▼
              +--------------------------+
              |      Monitoring          |
              |--------------------------|
              | Stats: task count, load, |
              | worker activity          |
              +--------------------------+
```

## 🔧 Component Responsibilities

### 1. Client
- Sends tasks to Dispatcher via `POST_TASK`
- Queries results by Task ID via `GET_RESULT`
- CLI interface for user interaction

### 2. Dispatcher
- Receives tasks and enqueues them
- Resolves the appropriate Worker using NameService
- Dispatches tasks to Worker via UDP
- Stores results and responds to result queries

### 3. Worker
- Registers itself with the NameService at startup
- Receives task, processes it using a handler (e.g., `reverse.py`)
- Sends the result back to Dispatcher
- Supports dynamic extension by adding modules to `worker_types/`

### 4. NameService
- Maintains a dynamic registry of worker type → address mappings
- Responds to Dispatcher `LOOKUP_WORKER` and Worker `REGISTER_WORKER` messages

### 5. Monitoring
- Provides system insights over a REST API
- Exposes number of workers, queue size, processing time (future extensible)

## 🔁 Communication Design

- All communication is UDP-based using JSON-encoded messages
- Messages follow a standard structure with:
  - `type` (e.g., "POST_TASK")
  - `data` (payload with task or metadata)
- Each component runs in its own Docker container

## 🧩 Modularity & Extensibility

- Adding new task types is as simple as dropping a `.py` file into `worker_types/`
- Worker dispatch logic is decoupled from the Dispatcher — supports horizontal scaling
- Components can be replaced or extended without breaking the communication protocol

## 📦 Container-Oriented Architecture

- Docker Compose handles orchestration and service naming
- Services resolve each other via DNS (e.g., `nameservice`, `dispatcher`)
- Shared volume (optional) for logging and testing

## 📝 Design Rationale

- UDP was chosen for lightweight, stateless communication
- Decentralized processing via Workers allows scaling and isolation
- NameService provides runtime flexibility instead of static configuration
