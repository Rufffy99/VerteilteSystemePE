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

def lookup_worker(task_type): # TODO
    """
    Lookup a worker's address based on the given task type.
    This function creates a UDP socket to send a lookup request message containing the task type
    to the name service (address specified by NAMESERVICE_ADDRESS). It then waits for a response with 
    a timeout of 2 seconds. If a valid response is received and contains a worker address, that address
    is returned. Otherwise, or if the socket times out, the function returns None.
    Parameters:
        task_type: The type of task for which a worker's address is being requested.
    Returns:
        The address of the worker as received from the lookup, or None if no valid address is found or
        if the request times out.
    """
    logging.info(f"Lookup worker for task type: {task_type}")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        msg = encode_message(LOOKUP_WORKER, {"type": task_type})
        try:
            sock.sendto(msg, NAMESERVICE_ADDRESS)
            logging.info(f"Sent lookup message to name service at {NAMESERVICE_ADDRESS}")
        except Exception as e:
            logging.error(f"Failed to send lookup message: {e}")
            return None
        sock.settimeout(2.0)
        try:
            data, _ = sock.recvfrom(4096)
            logging.info("Received response from name service")
            _, response = decode_message(data)
            address = response.get("address")
            if not address:
                logging.warning("No worker address found in name service response")
                return None
            logging.info(f"Worker address found: {address}")
            return address
        except socket.timeout:
            logging.warning("Timeout waiting for name service response")
            return None

def try_dispatch_tasks(): # TODO
    """
    Tries to dispatch tasks from the global task_queue to available workers.
    This function iterates over a copy of the global task_queue while holding a lock
    to ensure thread-safe access. For each task in the queue, it performs the following:
    - If the task's status is "done", the task is removed from the queue.
    - It looks up an available worker corresponding to the task's type.
    - If no worker is found or the selected worker is marked as busy, the task is skipped.
    - Otherwise, the worker's address is parsed and resolved into an IP address.
    - A UDP socket is created to send the task, encoded as a message, to the worker.
    - After successful dispatch, the worker is marked as busy, and the task is removed from the queue.
    - Any exceptions encountered during dispatch are logged as errors.
    Notes:
    - Global resources such as task_queue, lock, and worker_busy are used for coordination.
    - The task is dispatched using a UDP protocol and expects the worker to process the message.
    - The function handles and logs exceptions to ensure that failures during dispatching
        do not halt the process.
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

def handle_post_task(data, addr, sock): # TODO
    """
    Handles a POST task request by creating a new task from the provided data,
    updating global task counters and statistics, appending the task to the task queue,
    and dispatching tasks. Finally, it sends a response back to the requester.
    Parameters:
        data (dict): A dictionary containing task data. Expected keys include:
                     - "type": The type of the task.
                     - "payload": The payload or content associated with the task.
        addr (tuple): The address (IP, port) of the client sending the request.
        sock (socket.socket): The UDP socket used for sending the response message.
    Side Effects:
        - Increments the global task_id_counter.
        - Updates live_stats by incrementing "open_tasks" and "total_tasks".
        - Creates and enqueues a new Task object in task_queue.
        - Stores the task in task_results for future reference.
        - Initiates task dispatching via try_dispatch_tasks().
    Exceptions:
        - Logs an error message if there's any failure in sending the response back to the client.
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

def handle_get_result(data, addr, sock): # TODO
    """
    Handles a GET result request by retrieving the task's result based on a given task ID and sending an appropriate response.
    Parameters:
        data (dict): A dictionary containing the request data. It must include a "task_id" key.
        addr (tuple): The address (host, port) of the request sender.
        sock (socket.socket): The socket used to send the response.
    Behavior:
        - Retrieves the task associated with the "task_id" from a shared dictionary (access protected by a lock).
        - If the task is found and its result is available, constructs a response containing the result.
        - If the task is found but its result is not yet ready, constructs a response indicating that the result is not ready.
        - If the task is not found, constructs a response indicating that the task was not found.
        - Logs the request and the constructed response.
        - Encodes and sends the response message to the requester via the provided socket.
    Returns:
        None
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

def handle_result_return(data, addr, sock): # TODO
    """
    Process the result of a task returned from a worker.
    This function retrieves and updates the task corresponding to the provided
    result data. It adjusts task details such as its result, timestamps, and status,
    and updates global statistics including completion counts and average completion
    times. Additionally, it removes the task from the pending queue if necessary,
    sends a response back to the worker via the provided socket, and updates the worker's
    availability before attempting to dispatch new tasks.
    Args:
        data (dict): Dictionary containing task information with expected keys:
            - "task_id": Unique identifier for the task.
            - "result": The result produced by the worker.
        addr (tuple): The address (IP, port) of the worker that submitted the result.
        sock (socket.socket): The UDP socket used to send the response message back.
    Side Effects:
        - Updates the global task_results, task_queue, live_stats, and worker_busy
          data structures.
        - Computes overall and per-worker average task completion times.
        - Logs the receipt of the task result.
        - Responds to the worker using the sock by sending an encoded message.
        - Triggers task dispatching through a call to try_dispatch_tasks().
    Notes:
        This function assumes the existence of several global variables and helper
        functions (lock, task_results, task_queue, live_stats, worker_busy, encode_message,
        try_dispatch_tasks) that manage shared state and messaging within the application.
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
    Handles a GET_ALL_TASKS request by retrieving and processing task data, then sending back
    the serialized task list along with associated statistics.
    Parameters:
        data: The request payload (not used in processing within this function).
        addr (tuple): The address of the client that sent the request.
        sock (socket.socket): The socket used to send the response.
    Behavior:
        - Logs the receipt of the GET_ALL_TASKS request.
        - Acquires a lock to safely access and iterate over the shared task_results data.
        - Serializes each task object into a dictionary.
        - Computes statistics including:
              total: The total number of tasks.
              done: The number of tasks with the status "done".
              pending: The number of tasks with the status "pending".
              avg_completion_time: The average time between 'timestamp_created' and 
                                   'timestamp_completed' for tasks that are done.
        - Encodes the response using encode_message with a "RESPONSE" type and includes both the
          computed statistics and the list of serialized tasks.
        - Sends the response to the asking client using sock.sendto.
    Returns:
        None. The function sends the response directly through the provided socket.
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
    Handle a GET_STATS request by gathering and sending the current statistics and a list of pending tasks.
    This function logs the reception of a GET_STATS request, extracts up to 10 pending tasks (represented by their
    dictionary representations) from the shared task_results collection, and makes a copy of the live_stats dictionary.
    It then sends these details back to the client via the specified socket.
    Parameters:
        data (any): The request payload. Its structure is not explicitly defined in this context.
        addr (tuple): A tuple containing the client's address information (IP and port), used as the destination for the response.
        sock (socket.socket): The socket object through which the response message will be sent.
    Side Effects:
        - Logs information regarding incoming GET_STATS requests.
        - Acquires a lock while accessing shared mutable state to ensure thread-safety.
        - Sends a response message with the current statistics and pending task details to the client.
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
    Starts the dispatcher loop, which listens for and processes incoming messages via a UDP socket.
    This function performs the following tasks:
        - Creates a UDP socket and binds it to the specified HOST and PORT.
        - Logs the start-up of the dispatcher with its listening address.
        - Enters an infinite loop to continuously receive UDP messages.
        - Decodes each message to determine its type and extract its content.
        - Logs details about the received message and the sender's address.
        - Depending on the message type, dispatches the appropriate handler in a new thread:
            • POST_TASK: For processing task submission requests.
            • GET_RESULT: For handling requests to fetch the result of a task.
            • RESULT_RETURN: For processing messages that return task results.
            • GET_ALL_TASKS: For returning a list of all tasks.
            • GET_STATS: For providing dispatcher statistics.
        - For any unrecognized message type, logs a warning and sends an error response back to the sender.
    Note:
        - This function runs indefinitely and is expected to be terminated externally.
        - The use of threading enables concurrent processing of incoming messages.
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