

import socket
import threading
import time
import json
from shared.protocol import decode_message, encode_message, POST_TASK, GET_RESULT, RESULT_RETURN, LOOKUP_WORKER
from shared.task import Task

HOST = "0.0.0.0"
PORT = 4000
NAMESERVICE_ADDRESS = ("nameservice", 5000)

task_queue = []
task_results = {}
task_id_counter = 1
lock = threading.Lock()


def lookup_worker(task_type):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        msg = encode_message(LOOKUP_WORKER, {"type": task_type})
        sock.sendto(msg, NAMESERVICE_ADDRESS)
        sock.settimeout(2.0)
        try:
            data, _ = sock.recvfrom(4096)
            _, response = decode_message(data)
            return response.get("address")
        except socket.timeout:
            return None


def handle_post_task(data, addr, sock):
    global task_id_counter
    with lock:
        task_id = task_id_counter
        task_id_counter += 1

    task = Task(
        id=task_id,
        type=data["type"],
        payload=data["payload"]
    )

    with lock:
        task_queue.append(task)
        task_results[task.id] = task

    # Dispatch immediately for simplicity
    worker_address = lookup_worker(task.type)
    if worker_address:
        if ":" in worker_address and len(worker_address.split(":")) == 2:
            host, port = worker_address.split(":")
            if host and port.isdigit():
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as send_sock:
                    send_sock.sendto(encode_message("TASK", task.__dict__), (host, int(port)))
            else:
                print(f"[Error] Invalid worker address format: {worker_address}")
        else:
            print(f"[Error] Invalid worker address format: {worker_address}")
    sock.sendto(encode_message("RESPONSE", {"message": f"Task received, ID = {task.id}"}), addr)


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

    sock.sendto(encode_message("RESPONSE", response), addr)


def handle_result_return(data, addr, sock):
    task_id = data.get("task_id")
    result = data.get("result")
    with lock:
        task = task_results.get(task_id)
        if task:
            task.result = result
            task.status = "done"
            task.timestamp_completed = time.time()
            response = {"message": "Result stored"}
        else:
            response = {"error": "Task ID not found"}
    sock.sendto(encode_message("RESPONSE", response), addr)


def dispatcher_loop():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    print(f"[Dispatcher] Listening on {HOST}:{PORT}")

    while True:
        data, addr = sock.recvfrom(4096)
        msg_type, content = decode_message(data)

        if msg_type == POST_TASK:
            threading.Thread(target=handle_post_task, args=(content, addr, sock)).start()
        elif msg_type == GET_RESULT:
            threading.Thread(target=handle_get_result, args=(content, addr, sock)).start()
        elif msg_type == RESULT_RETURN:
            threading.Thread(target=handle_result_return, args=(content, addr, sock)).start()
        else:
            sock.sendto(encode_message("RESPONSE", {"error": "Invalid message type"}), addr)


if __name__ == "__main__":
    dispatcher_loop()