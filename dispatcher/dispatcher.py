import socket
import threading
import time
import json
from shared.protocol import decode_message, encode_message, POST_TASK, GET_RESULT, RESULT_RETURN, LOOKUP_WORKER
from shared.task import Task
import os
import logging

LOG_DIR = os.environ.get("LOG_DIR", ".")
LOG_PATH = os.path.join(LOG_DIR, "dispatcher.log")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, LOG_PATH),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

HOST = "0.0.0.0"
PORT = 4000
NAMESERVICE_ADDRESS = ("nameservice", 5001)

task_queue = []
task_results = {}
task_id_counter = 1
worker_busy = {}  # Tracks whether a worker is currently processing a task
lock = threading.Lock()

worker_indices = {}  # Maintains round-robin index per task type

live_stats = {
    "total_tasks": 0,
    "completed_tasks": 0,
    "open_tasks": 0,
    "avg_completion_time": 0,
    "avg_completion_by_worker": {}
}

def lookup_worker(task_type):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        msg = encode_message(LOOKUP_WORKER, {"type": task_type})
        sock.sendto(msg, NAMESERVICE_ADDRESS)
        sock.settimeout(2.0)
        try:
            data, _ = sock.recvfrom(4096)
            _, response = decode_message(data)
            address = response.get("address")
            if not address:
                return None
            return address
        except socket.timeout:
            return None

def try_dispatch_tasks():
    logging.debug("Trying to dispatch tasks")
    with lock:
        for task in list(task_queue):
            if task.status == "done":
                task_queue.remove(task)
                continue
            worker_address = lookup_worker(task.type)
            if not worker_address or worker_busy.get(worker_address, False):
                continue
            try:
                host, port_str = worker_address.split(":")
                port = int(port_str.strip())
                resolved_ip = socket.gethostbyname(host)
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as send_sock:
                    task.assigned_worker = worker_address
                    send_sock.sendto(encode_message("TASK", task.__dict__), (resolved_ip, port))
                worker_busy[worker_address] = True
                task_queue.remove(task)
                logging.info(f"Task {task.id} dispatched to {worker_address}")
            except Exception as e:
                logging.error(f"Failed to dispatch task {task.id}: {e}")

def handle_post_task(data, addr, sock):
    global task_id_counter
    with lock:
        task_id = task_id_counter
        task_id_counter += 1

        live_stats["open_tasks"] += 1
        live_stats["total_tasks"] += 1

        task = Task(
            id=task_id,
            type=data["type"],
            payload=data["payload"],
            timestamp_created=time.time(),
            status="pending",
            result=None,
            assigned_worker=None
        )
        task.assigned_worker = None

        task_queue.append(task)
        task_results[task.id] = task

    try_dispatch_tasks()

    try:
        sock.sendto(encode_message("RESPONSE", {"message": f"Task received, ID = {task.id}"}), addr)
        logging.info(f"Sent response for task {task.id} to {addr}")
    except Exception as e:
        logging.error(f"Failed to send response for task {task.id} to {addr}: {e}")

def handle_get_result(data, addr, sock):
    task_id = data.get("task_id")
    with lock:
        task = task_results.get(task_id)
    if task and task.result:
        response = {"result": task.result}
    elif task:
        response = {"error": "Result not ready"}
    else:
        response = {"error": "Task not found"}

    logging.info(f"Result request for task {task_id} from {addr}: {response}")
    sock.sendto(encode_message("RESPONSE", response), addr)

def handle_result_return(data, addr, sock):
    task_id = data.get("task_id")
    result = data.get("result")
    with lock:
        task = task_results.get(task_id)
        if task:
            task.result = result
            now = time.time()
            task.status = "done"
            task.timestamp_completed = now
            if task in task_queue:
                task_queue.remove(task)

            duration = task.timestamp_completed - task.timestamp_created
            live_stats["completed_tasks"] += 1
            live_stats["open_tasks"] -= 1

            all_durations = [
                t.timestamp_completed - t.timestamp_created
                for t in task_results.values()
                if t.status == "done"
            ]
            if all_durations:
                live_stats["avg_completion_time"] = round(sum(all_durations) / len(all_durations), 2)

            worker_times = {}
            worker_counts = {}
            for t in task_results.values():
                if t.status == "done":
                    worker = t.type
                    dur = t.timestamp_completed - t.timestamp_created
                    worker_times[worker] = worker_times.get(worker, 0) + dur
                    worker_counts[worker] = worker_counts.get(worker, 0) + 1
            live_stats["avg_completion_by_worker"] = {
                w: round(worker_times[w] / worker_counts[w], 2)
                for w in worker_times
            }
            response = {"message": "Result stored"}
        else:
            response = {"error": "Task ID not found"}
    logging.info(f"Result received for task {task_id} from {addr}")
    sock.sendto(encode_message("RESPONSE", response), addr)

    if task and task.assigned_worker:
        worker_busy[task.assigned_worker] = False
    try_dispatch_tasks()

def handle_get_all_tasks(data, addr, sock):
    logging.info(f"Handling GET_ALL_TASKS request from {addr}")
    with lock:
        tasks_serialized = [t.__dict__ for t in task_results.values()]
        total = len(tasks_serialized)
        done = sum(1 for t in tasks_serialized if t.get("status") == "done")
        pending = sum(1 for t in tasks_serialized if t.get("status") == "pending")
        avg_completion_time = None
        completion_times = [
            t["timestamp_completed"] - t["timestamp_created"]
            for t in tasks_serialized
            if t.get("status") == "done" and t.get("timestamp_completed") and t.get("timestamp_created")
        ]
        if completion_times:
            avg_completion_time = sum(completion_times) / len(completion_times)

        stats = {
            "total": total,
            "done": done,
            "pending": pending,
            "avg_completion_time": avg_completion_time
        }

    sock.sendto(encode_message("RESPONSE", {"stats": stats, "tasks": tasks_serialized}), addr)

def handle_get_stats(data, addr, sock):
    logging.info(f"Handling GET_STATS request from {addr}")
    with lock:
        pending = [
            t.__dict__ for t in task_results.values()
            if t.status == "pending"
        ][:10]

        stats_copy = dict(live_stats)

    sock.sendto(encode_message("RESPONSE", {"stats": stats_copy, "pending": pending}), addr)

def dispatcher_loop():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    print(f"[Dispatcher] Listening on {HOST}:{PORT}")
    logging.info(f"Dispatcher started on {HOST}:{PORT}")

    while True:
        data, addr = sock.recvfrom(4096)
        msg_type, content = decode_message(data)
        logging.info(f"Received message from {addr}: type={msg_type}, content={content}")

        if msg_type == POST_TASK:
            logging.info(f"Dispatching POST_TASK from {addr}")
            threading.Thread(target=handle_post_task, args=(content, addr, sock)).start()
        elif msg_type == GET_RESULT:
            threading.Thread(target=handle_get_result, args=(content, addr, sock)).start()
        elif msg_type == RESULT_RETURN:
            threading.Thread(target=handle_result_return, args=(content, addr, sock)).start()
        elif msg_type == "GET_ALL_TASKS":
            threading.Thread(target=handle_get_all_tasks, args=(content, addr, sock)).start()
        elif msg_type == "GET_STATS":
            threading.Thread(target=handle_get_stats, args=(content, addr, sock)).start()
        else:
            logging.warning(f"Invalid message type received from {addr}: {msg_type}")
            sock.sendto(encode_message("RESPONSE", {"error": "Invalid message type"}), addr)

if __name__ == "__main__":
    dispatcher_loop()