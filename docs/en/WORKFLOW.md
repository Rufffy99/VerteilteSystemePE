# WORKFLOW.md

## 🔄 System workflow: Task processing from A to Z

This document describes the complete workflow of a task in the system - from receipt to processing and delivery of results. The focus is on the interaction of the components and the data flows.

---

## 🧭 Process overview

```plaintext
[1] Client → Dispatcher (HTTP)
[2] Dispatcher → Nameservice (HTTP)
[3] Dispatcher → Worker (UDP)
[4] Worker → Dispatcher (UDP)
[5] Dispatcher → Client (HTTP)
````

---

## 🧾 Step-by-step

### 1st client sends task

- The user enters a task via the CLI frontend.
- Example: “Reverse the string `hello world`”.
- The client wraps the task in a JSON and sends it to the dispatcher via HTTP.

```json
POST /task
{
 "type": "reverse",
 "payload": "hello world"
}
```

---

### 2. dispatcher contacts name service

- The dispatcher calls `/lookup/reverse`.
- The name service searches the registry (`registry.json`) for a registered worker of this type.
- Return: IP and port (e.g. `worker-reverse:6000`).

---

### 3. dispatcher sends task to worker

- The task is sent to the `worker-reverse` via a UDP packet.
- Content: serialized task including `id`, `type`, `payload`.

---

### 4. worker processes and responds

- The worker receives the message, recognizes its type (`reverse`) and processes the payload.
- The result (`"dlrow olleh"`) is sent back to the sender (dispatcher) via a UDP packet.

---

### 5. dispatcher sends response to client

- The dispatcher receives the response and maps it to the original request.
- Response sent back to the client via HTTP:

```json
{
 "id": "task-001",
 "result": "dlrow olleh"
}
```

---

## 🧩 Special cases

### 🔁 No response from the worker

- Dispatcher waits with timeout.
- If no response: Retry or error to client.

### 🧍 No worker registered

- Dispatcher receives 404 from name service.
- Response to client: Error `"No worker available for type <x>"`.

---

## 🧠 Internal data flows

- `task_id` is generated in the dispatcher.
- Logging takes place in every step in `/logs/`.
- UDP communication is stateless - responses must be assigned using `task_id`.

---

## 🔍 Observability

- The monitoring service shows:
  - Active containers
  - Registered workers
  - Errors or inactivity
- Access via web interface (port 8080)

---

## 🧪 Example (sum)

```json
POST /task
{
 "type": "sum",
 "payload": "1,2,3"
}
```

Response:

```json
{
 "id": "task-xyz",
 "result": 6
}
```

---

## 🧵 Summary of the workflow

| Step | Source | Destination | Protocol | Content |
|--------|------------|--------------|-----------|----------------|
| 1 | Client | Dispatcher | HTTP | Task Request |
| 2 | Dispatcher | Nameservice | HTTP | Worker-Lookup |
| 3 | Dispatcher | Worker | UDP | Task |
| 4 | Worker | Dispatcher | UDP | Result |
| 5 | Dispatcher | Client | HTTP | Response |