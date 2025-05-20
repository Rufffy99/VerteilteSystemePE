# TaskGrid+ – Workflow Description

This document describes the end-to-end workflow of how a task moves through the TaskGrid+ system, from submission by the client to result delivery.

---

## 🔄 Workflow Steps

### 1. Task Submission

**Client → Dispatcher**
- The client sends a `POST_TASK` message via UDP.
- The message includes the task type (e.g., `"reverse"`) and the input data (`payload`).

```json
{
  "type": "POST_TASK",
  "data": {
    "type": "reverse",
    "payload": "OpenAI"
  }
}
```

---

### 2. Task Queuing and Worker Resolution

**Dispatcher**
- Receives the task and assigns it a unique task ID.
- Saves it to the task queue with status `"pending"`.
- Sends a `LOOKUP_WORKER` request to the NameService to resolve a suitable worker address for the task type.

---

### 3. Worker Lookup

**Dispatcher → NameService**
- The dispatcher queries the NameService with the task type.

```json
{
  "type": "LOOKUP_WORKER",
  "data": {
    "type": "reverse"
  }
}
```

**Response from NameService:**

```json
{
  "address": "worker-reverse:6000"
}
```

---

### 4. Task Dispatching

**Dispatcher → Worker**
- The dispatcher sends the full task object (as JSON) to the resolved worker address.

---

### 5. Task Processing

**Worker**
- The worker receives the task, identifies the correct handler module (`worker_types/reverse.py`), and processes the payload.
- The result is returned via a `RESULT_RETURN` message to the Dispatcher.

```json
{
  "type": "RESULT_RETURN",
  "data": {
    "task_id": 42,
    "result": "IAnepO"
  }
}
```

---

### 6. Result Storage

**Dispatcher**
- Saves the result for the task.
- Updates task status to `"done"` and sets `timestamp_completed`.

---

### 7. Client Result Query

**Client → Dispatcher**
- The client can request the result using `GET_RESULT`.

```json
{
  "type": "GET_RESULT",
  "data": {
    "task_id": 42
  }
}
```

**Dispatcher Response:**

```json
{
  "result": "IAnepO"
}
```

---

## 🧩 Summary Flow

```plaintext
Client → Dispatcher → NameService → Dispatcher → Worker
        ←             ←             ←         ←

Client → Dispatcher ← Result
```

---

## 📝 Notes

- Each step involves a UDP message exchange
- Each component runs independently in a container
- The dispatcher manages task state and result persistence
