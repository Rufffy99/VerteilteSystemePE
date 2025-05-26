# COMMUNICATION.md

## 📡 Communication overview

The system is based on a hybrid communication architecture:
- **HTTP** is used for client-dispatcher interaction.
- UDP** is used for internal communication between dispatcher and workers.
- **Monitoring** uses the Docker Engine API for status monitoring.

---

## 🔗 Communication paths

#1 Client → Dispatcher
- Protocol:** HTTP
- Method:** POST
- Purpose:** Sending tasks (tasks)
- Data format:** JSON
- **Port:** 4000
- **Example:**
 ```json
 {
 "type": "reverse",
 "payload": "OpenAI"
 }
  ```

---

### 2nd dispatcher → name service
- Protocol:** HTTP
- **Purpose:** Retrieval of registered workers for specific task type
- **Port:** 5001
- **Response:** IP/port of a matching worker

---

### 3rd Dispatcher → Worker
- Protocol:** UDP
- Purpose:** Dispatching the task for processing
- Mechanism:**
  - The dispatcher sends a UDP packet with the serialized task.
  - The worker listens on port 6000.
- Port (internal):** 6000 (fixed for all workers, mapped externally by Compose)
- Data format:** JSON, serialized

---

### 4th worker → Dispatcher (response)
- Protocol:** UDP
- Purpose:** Return of the result
- Mechanism:**
  - The worker sends the result back to the sender address.
  - The response contains the result + metadata.

---

### 5. monitoring → Docker
- Protocol:** Docker Engine API (Unix Socket)
- **File:** `/var/run/docker.sock`
- Purpose:** Container status, health checks, log evaluation

---

## 🔐 Security aspects

- UDP is connectionless: no guaranteed delivery → simple retry logic required
- JSON messages do not contain any sensitive data
- Internal communication takes place in the private Docker network (`tasknet`)
- No external access to UDP ports through Docker Compose

---

## 🧪 Example communication flow

```plaintext
Client --> Dispatcher (HTTP POST)
Dispatcher --> Nameservice (HTTP GET)
Dispatcher --> Worker (UDP SEND)
Worker --> Dispatcher (UDP REPLY)
Dispatcher --> Client (HTTP Response)
````

---

## 📦 Message structure (UDP)

```json
{
 "id": "task-123",
 "type": "sum",
 "payload": "1,2,3,4"
}
```

Response:
```json
{
 "id": "task-123",
 "result": 10
}
````

---

## 🧰 Tools & formats

- Serialization:** JSON via UDP (text-based)
- Error handling:** Worker timeout + logging in the dispatcher
- **Broadcasts:** not used - direct point-to-point communication

---

## 🔁 Repetitions & error handling

- UDP may lose packets - Dispatcher implements timeouts & retries
- No confirmation by worker → Dispatcher actively evaluates return channel

Translated with DeepL.com (free version)