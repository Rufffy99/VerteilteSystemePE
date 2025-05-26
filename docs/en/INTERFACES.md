# INTERFACES.md

## 🎯 Overview of the interfaces

This document describes the internal and external interfaces of the system components. It defines the interactions between the modules as well as their protocols, endpoints and formats.

---

## 🌐 External interfaces

### 1st client → Dispatcher

- Type:** HTTP REST
- Method:** POST
- **Endpoint:** `http://dispatcher:4000/task`
- Description:** The client sends a task for processing.
- **Request Body (JSON):**
 ```json
 {
 "type": "reverse",
 "payload": "OpenAI"
 }
  ```
- **Response Body (JSON):**
 ```json
 {
 "id": "task-abc123",
 "result": "IAnepO"
 }
  ```

---

## 🔁 Internal interfaces

### 2nd dispatcher → name service

- Type:** HTTP GET
- **Endpoint:** `http://nameservice:5001/lookup/<task_type>`
- **Description:** Query which worker is registered for a task type.
- **Response:**
 ```json
 {
 "host": "worker-reverse",
 "port": 6000
 }
 ```

---

### 3rd Dispatcher → Worker

- **Type:** UDP socket
- Address:** IP + Port 6000
- Description:** Serialized message with the task is sent via UDP.
- **Payload:**
 ```json
 {
 "id": "task-001",
 "type": "sum",
 "payload": "1,2,3"
 }
  ```

---

### 4th worker → Dispatcher (response)

- Type:** UDP socket
- **Address:** Return channel of the sender address
- Description:** Worker sends back result
- **Payload:**
 ```json
 {
 "id": "task-001",
 "result": 6
 }
 ```

---

### 5. monitoring → Docker Engine

- **Type:** Unix socket (`/var/run/docker.sock`)
- Description:** Container status via Docker API
- Function:** Visualization & health checks
- **Examples:**
  - Status: `GET /containers/json`
  - Logs: `GET /containers/<id>/logs`

---

## 📂 Common data structures

### Task

```json
{
 "id": "task-uuid",
 "type": "worker_type",
 "payload": "<string>"
}
```

### Result

```json
{
 "id": "task-uuid",
 "result": "<computed_value>"
}
```

---

## 🛡 Error cases & behavior

- **Invalid task type:** Dispatcher gives 400 error Client
- **No worker registered:** Dispatcher returns 404
- **UDP timeout:** Dispatcher waits with timeout and returns 504

---

## 🔧 Configurable parameters

- Worker types and activation status: `workers.json`
- UDP timeouts and retries: configured in the dispatcher script
- Port assignments: `docker-compose.yml`

---

## 🔄 Summary

| From | To | Protocol | Format | Description |
|----------------|------------------|-----------|--------|----------------------------------- |
| Client | Dispatcher | HTTP | JSON | Sends new tasks |
| Dispatcher | Nameservice | HTTP | JSON | Searches for responsible workers |
| Dispatcher | Worker | UDP | JSON | Routes task for processing |
| Worker | Dispatcher | UDP | JSON | Returns result |
| Monitoring | Docker API | Socket | JSON | Fetches status & logs of containers |