# ARCHITECTURE.md

## 🔄 Overview

This system is a modular distributed architecture for task processing, consisting of several specialized services that are containerized and orchestrated via Docker Compose. The structure follows a microservice approach with clearly defined responsibilities for each component.

---

## 🔹 Component overview

### 1. **Client** (`client/`)
- **Purpose:** CLI for interaction with the dispatcher
- **Function:** Define and send tasks
- **Communication:** HTTP requests to the dispatcher

### 2. **Dispatcher** (`dispatcher/`)
- **Purpose:** Central control instance
- **Function:** Receiving tasks from the client, routing to suitable workers
- Communication:**
  - Receives HTTP from client
  - Searches for workers via name service
  - Forwards tasks to workers via UDP/HTTP

### 3. **Nameservice** (`nameservice/`)
- Purpose:** Service Discovery
- **Function:** Registration and lookup of active workers based on their types
- **Data storage:** JSON registry (`registry.json`)

### 4. **Worker (5 instances)** (`worker/`)
- **Purpose:** ** Task specialization
- **Types:**
  - `reverse`
  - `hash`
  - `sum`
  - `upper`
  - `wait`
- **Start via:** `worker.py <type>`
- **Communication:** UDP server expects requests from the dispatcher

### 5. **monitoring** (`monitoring/`)
- **Purpose:** Observation of the system
- **Function:** Display of the status of active containers and registered workers
- **Special features:** Access to Docker socket (`/var/run/docker.sock`)

### 6. **Shared Module** (`shared/`)
- **Function:** Shared structures (e.g. protocols, auxiliary functions)
- **Examples:**
  - `protocol.py`: Message definition
  - `task.py`: Representation of tasks
  - `utils.py`: Logging & serialization

### 7. **Devtools** (`devtools/`)
- **Tools for local development:**
  - `compose_generator.py`: Generates Docker Compose files
  - `runner.py`: Starts the system locally controlled

---

## 🤖 Runtime structure

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
````

- The **client** sends tasks to the **dispatcher**.
- The **Dispatcher** contacts the **Nameservice** to find the appropriate **Worker**.
- The selected **Worker** processes the task and sends the result back.
- The **Monitoring Service** monitors the entire system and provides status information.

---

## 🛠 Technology stack

| Component        | Technology               |
|------------------|--------------------------|
| Containerization | Docker, Docker Compose   |
| Language         | Python 3                 |
| Communication    | HTTP, UDP                |
| Monitoring       | Python + Docker API      |

---

## 📈 Scalability & modularity

- New worker types can be added by adding new entrypoints in `worker.py` and `workers.json`.
- The components can be developed, tested and deployed separately.
- Communication via standardized protocols enables flexible extensibility.

---

## ⚖️ Responsibilities & separation

- **Single Responsibility Principle** applied at system level
- Each module focuses on exactly one task:
  - Dispatcher = Routing
  - Nameservice = Lookup
  - Worker = Processing
  - Client = Input/Output
  - Monitoring = Observation

---

## 🚀 Conclusion

This architecture enables a flexible, traceable and expandable task processing system with clearly defined interfaces and responsibilities. It is suitable for use in development and test environments with a focus on modularity and visibility of processes.

Translated with DeepL.com (free version)