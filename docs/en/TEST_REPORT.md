# TaskGrid+ – Test Report

This document summarizes test cases executed on the TaskGrid+ system, including task types, payloads, expected vs. actual results, and log snapshots.

---

## 🧪 Test Environment

- Docker Compose with the following services:
  - nameservice
  - dispatcher
  - worker-reverse
  - worker-sum
  - client
- Monitoring REST service active on port 7000

---

## ✅ Test Cases

### Test 1: Reverse Task
- **Command:** `client send reverse "Hello"`
- **Expected:** `"olleH"`
- **Result:** ✅ Passed

### Test 2: Sum Task
- **Command:** `client send sum "1,2,3"`
- **Expected:** `"6"`
- **Result:** ✅ Passed

### Test 3: Uppercase Task
- **Command:** `client send upper "openai"`
- **Expected:** `"OPENAI"`
- **Result:** ✅ Passed

### Test 4: SHA256 Hash Task
- **Command:** `client send hash "abc"`
- **Expected:** SHA256 of `"abc"` in hex
- **Result:** ✅ Passed

### Test 5: Wait Task (Simulated Delay)
- **Command:** `client send wait "2"` (seconds)
- **Expected:** No error, delay in response
- **Result:** ✅ Passed

### Test 6: Invalid Task Type
- **Command:** `client send unknown "data"`
- **Expected:** Error message
- **Result:** ✅ Passed with error: `Invalid task type: unknown`

---

## 🖥 Logs Snapshot (Dispatcher)

```
[Dispatcher] Received task: type=reverse
[Dispatcher] Lookup: reverse → worker-reverse:6000
[Dispatcher] Dispatched task ID 1
[Dispatcher] Result received for task ID 1
```

---

## 📊 Monitoring Snapshot

At time of test:

```json
{
  "active_workers": 3,
  "pending_tasks": 0,
  "average_duration": 1.1
}
```

---

## 📌 Summary

| Test Case         | Status |
|-------------------|--------|
| Reverse           | ✅     |
| Sum               | ✅     |
| Upper             | ✅     |
| Hash              | ✅     |
| Wait              | ✅     |
| Invalid Task Type | ✅     |

All functional requirements tested successfully. Logs confirm proper task lifecycle behavior.

---

## 📎 Notes

- Testing was performed with simulated data and controlled payloads.
- Results match expected outputs and response formats as defined in INTERFACES.md.
