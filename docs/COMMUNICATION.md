# TaskGrid+ – Communication Protocol

This document defines the structure of messages exchanged between the components of TaskGrid+, and explains the purpose and flow of each message type in the system.

---

## 📦 Message Transport

All communication is based on **UDP** sockets using **JSON-encoded messages**.

---

## 🧱 Message Format

Each message follows this general structure:

```json
{
  "type": "MESSAGE_TYPE",
  "data": {
    // payload depending on message type
  }
}
```

Encoded using UTF-8 and sent over UDP.

---

## 📄 Task Data Structure (`task_t`)

This data structure is shared across the system and represents a single task.

```json
{
  "id": 123,
  "type": "reverse",
  "payload": "Hello",
  "result": "",
  "status": "pending",
  "timestamp_created": 1680000000.0,
  "timestamp_completed": 0.0
}
```

Used when sending and receiving tasks between Client → Dispatcher → Worker.

---

## 📨 Message Types

### 1. `POST_TASK`
**Sender:** Client → Dispatcher  
**Purpose:** Submit a new task

**Payload:**
```json
{
  "type": "reverse",
  "payload": "Hello"
}
```

**Response:**
```json
{
  "message": "Task received, ID = 42"
}
```

---

### 2. `GET_RESULT`
**Sender:** Client → Dispatcher  
**Purpose:** Request result of a completed task

**Payload:**
```json
{
  "task_id": 42
}
```

**Response:**
```json
{
  "result": "olleH"
}
```

---

### 3. `RESULT_RETURN`
**Sender:** Worker → Dispatcher  
**Purpose:** Send the result of a processed task

**Payload:**
```json
{
  "task_id": 42,
  "result": "olleH"
}
```

**Response:**
```json
{
  "message": "Result stored"
}
```

---

### 4. `REGISTER_WORKER`
**Sender:** Worker → NameService  
**Purpose:** Register as a handler for a specific task type

**Payload:**
```json
{
  "type": "reverse",
  "address": "worker-reverse:6000"
}
```

**Response:**
```json
{
  "message": "Successfully registered"
}
```

---

### 5. `LOOKUP_WORKER`
**Sender:** Dispatcher → NameService  
**Purpose:** Find an available worker for a given task type

**Payload:**
```json
{
  "type": "reverse"
}
```

**Response:**
```json
{
  "address": "worker-reverse:6000"
}
```

---

### 6. `DEREGISTER_WORKER` *(optional)*
**Sender:** Worker → NameService  
**Purpose:** Unregister a previously registered worker

**Payload:**
```json
{
  "address": "worker-reverse:6000"
}
```

**Response:**
```json
{
  "message": "Deregistered 1 entries"
}
```

---

## 💡 Notes

- All messages are handled asynchronously using threads
- UDP ensures fast, lightweight communication but does not guarantee delivery
- Message processing should always handle invalid or missing fields

---

## 📚 References

- See `shared/protocol.py` for encoder/decoder implementation
- Message types are defined as constants to ensure consistency

