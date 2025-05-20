# TaskGrid+ – Technologies and Dependencies

This document outlines the core technologies, languages, and external libraries used in the TaskGrid+ system.

---

## 🖥️ Programming Language

- **Python 3.11**
  - Chosen for its simplicity, socket programming capabilities, and dynamic module handling.

---

## 🐳 Containerization

- **Docker**
  - Each component runs in an isolated container for modularity and portability.

- **Docker Compose**
  - Orchestrates the multi-container system.
  - Provides internal DNS for service discovery (e.g., `dispatcher`, `nameservice`).

---

## 📦 Python Dependencies

| Component     | Library       | Purpose                          |
|---------------|---------------|----------------------------------|
| Monitoring    | `Flask`       | REST API for system stats        |
| All Components| `socket` (std)| UDP-based communication          |
| All Components| `json` (std)  | Message serialization            |
| Workers       | `importlib`   | Dynamic task type loading        |
| Dispatcher    | `threading`   | Parallel message handling        |

All other modules used are part of the Python Standard Library.

---

## 🔌 Communication Protocol

- **UDP** (User Datagram Protocol)
  - Lightweight, connectionless transport for internal service communication.
  - JSON-based message encoding for structured payloads.

---

## 🧪 Testing & Logging

- Logging is done using `print()` or `logging` (optional future improvement).
- Test protocols recorded manually (see `TEST_REPORT.md`).

---

## 🧩 Architecture Design Principles

- Modular: each component has a single responsibility
- Extensible: new task types can be added via Python modules
- Transparent: clear interface definitions and message formats
- Portable: easy to deploy using Docker and Compose

---

## 🔐 Security Note

- UDP does not include transport-level encryption or verification.
- TaskGrid+ is intended for trusted, controlled environments (e.g., academic or internal use).
