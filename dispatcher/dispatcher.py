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
lock = threading.Lock()

worker_indices = {}  # Maintains round-robin index per task type

def lookup_worker(task_type):
    """
    Lookup the list of worker addresses responsible for a given task type.
    Implements round-robin selection if multiple workers are available.
    """
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


def handle_post_task(data, addr, sock):
    """
    Handles an incoming POST task request by creating a new task, queuing it, and dispatching it to an appropriate worker.
    Parameters:
        data (dict): A dictionary containing the task details with the following keys:
            - "type": A string indicating the type of task.
            - "payload": The payload associated with the task.
        addr (tuple): The address (IP, port) of the request sender.
        sock (socket.socket): The UDP socket used for communication to send responses and dispatch tasks.
    Side Effects:
        - Increments the global task_id_counter and creates a new task with a unique ID.
        - Appends the new task to the global task_queue.
        - Updates the global task_results dictionary with the new task.
        - Sends a UDP message dispatching the task to an identified worker based on its type.
        - Sends a UDP response back to the sender confirming receipt or reporting errors.
        - Logs relevant information and error messages.
    Raises:
        ValueError: If the worker address format is invalid.
        Exception: Catches and logs any exceptions encountered during dispatch, sending an error response back to the client.
    Returns:
        None: The function communicates outcomes through UDP responses.
    """
    
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
    logging.debug(f"Selected worker address: {worker_address}")
    if worker_address:
        try:
            host, port_str = worker_address.split(":")
            try:
                port = int(port_str.strip())
                resolved_ip = socket.gethostbyname(host)
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as send_sock:
                    logging.debug(f"Sending to socket address: {(resolved_ip, port)}")
                    logging.info(f"Sending task {task.id} to resolved IP {resolved_ip}:{port}")
                    send_sock.sendto(encode_message("TASK", task.__dict__), (resolved_ip, port))
            except Exception as e:
                logging.error(f"DNS resolution or dispatch failed for task {task.id} to {worker_address}: {e}")
                sock.sendto(encode_message("RESPONSE", {"error": f"Dispatch failed: {str(e)}"}), addr)
                return
            logging.info(f"Task {task.id} received from {addr}, dispatched to worker {worker_address}")
        except Exception as e:
            logging.error(f"Dispatch failed for task {task.id} to {worker_address}: {str(e)}")
            sock.sendto(encode_message("RESPONSE", {"error": f"Dispatch failed: {str(e)}"}), addr)
            return
    else:
        logging.warning(f"No worker available for task type '{task.type}' (task ID {task.id})")
        sock.sendto(encode_message("RESPONSE", {"error": "No worker available for task type"}), addr)
        return

    sock.sendto(encode_message("RESPONSE", {"message": f"Task received, ID = {task.id}"}), addr)


def handle_get_result(data, addr, sock):
    """
    Handles a GET_RESULT request by retrieving the result for the specified task.
    This function extracts the task identifier from the 'data' dictionary, looks up the corresponding task in a shared task_results 
    dictionary (access controlled by a lock), and sends an appropriate response via the provided socket. If the task exists and a result 
    is available, the result is returned; if the task exists but the result is not yet ready, an error message is returned to that effect; 
    and if the task is not found, an error message indicating the missing task is returned.
    Parameters:
        data (dict): A dictionary expected to contain the key 'task_id' that identifies the task.
        addr (tuple): The address (IP, port) of the requester.
        sock (socket.socket): The socket used to send the response back to the client.
    Returns:
        None
    Side Effects:
        Logs the result request and its outcome using the logging module.
        Sends a response to the requester via the provided socket.
    """
    
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
    """
    Handles storing the result of a task upon receiving it.
    Extracts the task ID and result from the provided data, updates the matching task's result,
    status, and completion timestamp within a thread-safe block, logs the update, and sends a response 
    back to the sender using the provided socket.
    Parameters:
        data (dict): Dictionary containing task-related information. Expected to have the keys:
                     - "task_id": The unique identifier for the task.
                     - "result": The computation result to be stored.
        addr (tuple): The address of the sender from which the result was received.
        sock (socket.socket): The UDP socket used to send the response message.
    Returns:
        None
    Side Effects:
        - Updates a shared task result store (protected by a lock).
        - Logs the receipt and handling of the task's result.
        - Sends a response message back to the sender.
    """
    
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
    logging.info(f"Result received for task {task_id} from {addr}")
    sock.sendto(encode_message("RESPONSE", response), addr)


def dispatcher_loop():
    """
    Continuously listens for incoming UDP messages on the configured HOST and PORT,
    decodes each message into its type and content, and dispatches the message to the
    appropriate handler function by starting a new thread. The function handles three
    types of messages: POST_TASK, GET_RESULT, and RESULT_RETURN. When a message with an
    unrecognized type is received, it logs a warning and responds with an error message.
    Behavior:
        - Creates a UDP socket and binds it to the specified HOST and PORT.
        - Enters an infinite loop, continuously waiting for incoming messages.
        - Decodes each received message and spawns a new thread to handle the request
          based on its type.
        - For invalid message types, logs a warning and sends an error response to the sender.
    Parameters:
        None
    Returns:
        None
    Notes:
        This function runs indefinitely until the process is terminated.
    """
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    print(f"[Dispatcher] Listening on {HOST}:{PORT}")
    logging.info(f"Dispatcher started on {HOST}:{PORT}")

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
            logging.warning(f"Invalid message type received from {addr}: {msg_type}")
            sock.sendto(encode_message("RESPONSE", {"error": "Invalid message type"}), addr)


if __name__ == "__main__":
    dispatcher_loop()