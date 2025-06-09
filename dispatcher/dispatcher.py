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

MAX_LOOKUP_ATTEMPTS = 10

# Global data structures and synchronization lock
task_queue = []
task_results = {}
task_id_counter = 1
worker_busy = {}
lock = threading.Lock()
worker_indices = {}
live_stats = {
    "total_tasks": 0,
    "completed_tasks": 0,
    "open_tasks": 0,
    "avg_completion_time": 0,
    "avg_completion_by_worker": {}
}

def lookup_worker(task_type):
    """
    Lookup a worker for a given task type using the name service.
    This function sends a UDP lookup request carrying the specified task type to a name service.
    It will attempt to receive a valid worker address from the service up to MAX_LOOKUP_ATTEMPTS times.
    If the address is successfully retrieved, it is returned. The function logs each attempt, including any
    timeouts or errors encountered during the lookup process.
    Parameters:
        task_type (str): The type of task for which a worker is being looked up.
    Returns:
        str or None: The address of the worker if found, otherwise None.
    """
    
    logging.info(f"Lookup worker for task type: {task_type}")
    msg = encode_message(LOOKUP_WORKER, {"type": task_type})
    for attempt in range(MAX_LOOKUP_ATTEMPTS):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            try:
                sock.sendto(msg, NAMESERVICE_ADDRESS)
                sock.settimeout(1.0)
                data, _ = sock.recvfrom(4096)
                _, response = decode_message(data)
                address = response.get("address")
                if not address:
                    logging.warning("No worker address found in name service response")
                    return None
                logging.info(f"Worker address found: {address}")
                return address
            except socket.timeout:
                logging.warning(f"Attempt {attempt + 1}: Timeout waiting for name service response")
            except Exception as e:
                logging.error(f"Attempt {attempt + 1}: Lookup failed: {e}")
            time.sleep(1)
    logging.error("Max retries exceeded during worker lookup")
    return None

def try_dispatch_tasks():
    """
    Dispatch tasks from the task_queue to available workers.
    This function iterates through a copy of the global task_queue while holding a lock to ensure thread-safety.
    For each task in the queue, it performs the following steps:
    1. If the task status is "done", removes it from task_queue.
    2. Looks up an available worker based on the task type. If no worker is found or the worker is currently busy,
        the task is skipped.
    3. Parses the worker's address into hostname and port, resolves the hostname to an IP address, and sends the task
        details (serialized as a dictionary) using a UDP socket.
    4. Marks the worker as busy, logs the dispatching, and removes the successfully dispatched task from task_queue.
    Any exceptions raised during the process are caught and logged as errors without aborting the dispatch loop.
    """
    
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
    """
    Handles an incoming POST_TASK request by creating a new task, updating live statistics, enqueuing the task,
    and dispatching tasks to available workers. Sends a response back to the client with the assigned task ID.
    Parameters:
        data (dict): A dictionary containing the task details. Expected to have keys 'type' and 'payload'.
        addr (tuple): A tuple representing the client's address to which responses will be sent.
        sock (socket.socket): The socket used for sending responses back to the client.
    Side Effects:
        - Increments the global task_id_counter.
        - Updates the global live_stats dictionary to reflect the new task.
        - Appends the new task to the global task_queue.
        - Records the new task in the global task_results dictionary.
        - May dispatch tasks by calling try_dispatch_tasks().
    Exceptions:
        If an exception occurs during sending the response, it is logged, but not re-raised.
    Note:
        This function uses global variables and a lock to ensure thread-safe operation.
    """
    
    global task_id_counter
    logging.info(f"Received POST_TASK from {addr} with data: {data}")
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
        logging.info(f"Created and enqueued task {task.id} of type '{task.type}' from {addr}")

    try_dispatch_tasks()
    logging.info(f"Dispatched tasks after adding task {task.id}")

    try:
        response = {"message": f"Task received, ID = {task.id}"}
        sock.sendto(encode_message("RESPONSE", response), addr)
        logging.info(f"Sent response for task {task.id} to {addr}: {response}")
    except Exception as e:
        logging.error(f"Failed to send response for task {task.id} to {addr}: {e}")

def handle_get_result(data, addr, sock):
    """
    Handles a GET_RESULT request by retrieving and sending the result of a given task.
    This function extracts the task ID from the provided 'data' dictionary and logs the reception
    of the GET_RESULT request from the specified address 'addr'. It then attempts to retrieve the task
    from a shared 'task_results' resource in a thread-safe manner using a lock.
    If the task exists and its result is available, it prepares a response containing the result.
    If the task exists but the result is not yet ready, it responds with an error indicating that the
    result is not ready. If the task is not found, it responds with an error indicating that the task is
    not present. In all scenarios, the response is logged and then sent to the client using UDP via the
    provided socket 'sock'.
    Args:
        data (dict): A dictionary containing task details, including the "task_id".
        addr (tuple): The address of the client from which the GET_RESULT request originated.
        sock (socket.socket): The UDP socket used to send the response.
    Returns:
        None: This function sends the result directly through the socket.
    """
    
    task_id = data.get("task_id")
    logging.info(f"Handling GET_RESULT for task_id: {task_id} from {addr}")
    with lock:
        task = task_results.get(task_id)

    if task and task.result:
        response = {"result": task.result}
        logging.info(f"Task {task_id} found with result. Sending result.")
    elif task:
        response = {"error": "Result not ready"}
        logging.info(f"Task {task_id} found but result not ready.")
    else:
        response = {"error": "Task not found"}
        logging.info(f"Task {task_id} not found in task_results.")

    logging.info(f"GET_RESULT response for task {task_id} to {addr}: {response}")
    sock.sendto(encode_message("RESPONSE", response), addr)

def handle_result_return(data, addr, sock):
    """
    Handles the receipt and processing of a result returned from a worker for a given task.
    This function updates the task information with the provided result, marks the task as done,
    calculates the task execution duration, updates live statistics (including average completion times
    globally and per worker), and removes the task from the task queue if present. Additionally, it
    sends a response back to the originating address via the provided socket and marks the associated
    worker as available if applicable. Finally, it attempts to dispatch any pending tasks.
    Parameters:
        data (dict): A dictionary containing task-related data, including:
                     - "task_id": An identifier for the task.
                     - "result": The result produced by the worker.
        addr (tuple): The address (IP and port) of the sender of the result.
        sock (socket.socket): The UDP socket used to send the response message.
    Behavior:
        - If the task exists in task_results, its result, status ("done"), and completion timestamp are updated.
        - The task is removed from the task_queue if it is still present.
        - The function updates live_stats with the task's duration and recalculates both the overall average
          completion time and per-worker average completion times.
        - A "Result stored" response is sent back to the client; otherwise, an error message is sent if the task
          is not found.
        - The worker's busy status is updated (set to available) if the task had an assigned worker.
        - Finally, the function calls try_dispatch_tasks() to attempt to process any pending tasks.
    """
    
    logging.info(f"Handling RESULT_RETURN for task {data.get('task_id')} from {addr}")
    task_id = data.get("task_id")
    result = data.get("result")
    with lock:
        task = task_results.get(task_id)
        if task:
            logging.info(f"Task {task_id} found. Updating result and marking as done.")
            task.result = result
            now = time.time()
            task.status = "done"
            task.timestamp_completed = now
            if task in task_queue:
                task_queue.remove(task)
                logging.info(f"Task {task_id} removed from task queue.")
            else:
                logging.info(f"Task {task_id} was not in task queue.")

            duration = task.timestamp_completed - task.timestamp_created
            live_stats["completed_tasks"] += 1
            live_stats["open_tasks"] -= 1
            logging.info(f"Task {task_id} completed in {duration:.2f} seconds.")

            all_durations = [
                t.timestamp_completed - t.timestamp_created
                for t in task_results.values()
                if t.status == "done"
            ]
            if all_durations:
                live_stats["avg_completion_time"] = round(sum(all_durations) / len(all_durations), 2)
                logging.info(f"Updated avg_completion_time: {live_stats['avg_completion_time']} seconds.")

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
            logging.info(f"Updated avg_completion_by_worker: {live_stats['avg_completion_by_worker']}")
            response = {"message": "Result stored"}
        else:
            logging.error(f"Task ID {task_id} not found in task_results.")
            response = {"error": "Task ID not found"}
    logging.info(f"Result received for task {task_id} from {addr}, response: {response}")
    sock.sendto(encode_message("RESPONSE", response), addr)

    if task and task.assigned_worker:
        worker_busy[task.assigned_worker] = False
        logging.info(f"Worker {task.assigned_worker} marked as available.")
    try_dispatch_tasks()
    logging.info("Attempted to dispatch tasks after handling RESULT_RETURN.")

def handle_get_all_tasks(data, addr, sock):
    """
    Handle a GET_ALL_TASKS request by collecting task statistics and sending a response.
    This function acquires a lock to safely access the shared task_results,
    serializes each task into a dictionary, computes statistics such as the total 
    number of tasks, the number of completed ('done') tasks, the number of pending 
    tasks, and the average completion time for tasks that are marked as done. The 
    computed statistics and serialized tasks are then encoded into a message and 
    sent to the requester via the provided socket.
    Parameters:
        data: The request data (not used directly in this function).
        addr: A tuple containing the address of the requester (IP and port).
        sock: The socket over which the response should be sent.
    Returns:
        None. The response is sent directly through the socket.
    """
    
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
    """
    Handles a GET_STATS request by logging the request, gathering relevant stats,
    and sending a response back to the requesting client.
    This function performs the following steps:
    1. Logs an informational message indicating the receipt of a GET_STATS request from the provided address.
    2. Under a thread-safe lock, creates a snapshot of task results that are still pending (up to 10 entries),
        where each task result is converted to a dictionary.
    3. Makes a copy of the current live system statistics.
    4. Sends a response message back to the client with a status code "RESPONSE", including the copied stats and the list of pending tasks,
        using the provided socket and address.
    Parameters:
         data: The incoming data associated with the GET_STATS request (not used within the function).
         addr: The address (IP and port) of the client that made the request.
         sock: The socket object used for sending the response message.
    Returns:
         None
    """
    
    logging.info(f"Handling GET_STATS request from {addr}")
    with lock:
        pending = [
            t.__dict__ for t in task_results.values()
            if t.status == "pending"
        ][:10]

        stats_copy = dict(live_stats)

    sock.sendto(encode_message("RESPONSE", {"stats": stats_copy, "pending": pending}), addr)

def dispatcher_loop():
    """
    Starts an infinite dispatcher loop that listens for incoming UDP messages
    on a specified host and port, decodes the messages, and dispatches them to
    the appropriate handler functions in separate threads based on their type.
    The dispatcher_loop function performs the following actions:
        - Creates a UDP socket and binds it to the predefined HOST and PORT.
        - Enters an infinite loop to continuously listen for incoming UDP messages.
        - Receives and logs raw data along with the sender's address.
        - Decodes the incoming message into a message type and content.
        - Dispatches the handling of messages by spawning new threads for each:
              • POST_TASK messages are handled by handle_post_task.
              • GET_RESULT messages are handled by handle_get_result.
              • RESULT_RETURN messages are handled by handle_result_return.
              • "GET_ALL_TASKS" messages are handled by handle_get_all_tasks.
              • "GET_STATS" messages are handled by handle_get_stats.
        - Logs a warning and responds with an error message if the message type is invalid.
    Note:
        - This function runs indefinitely and does not return.
    """
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    print(f"[Dispatcher] Listening on {HOST}:{PORT}")
    logging.info(f"Dispatcher started on {HOST}:{PORT}")

    while True:
        data, addr = sock.recvfrom(4096)
        logging.info(f"[DEBUG] Raw UDP from {addr}: {data}")
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