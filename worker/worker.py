import socket
import threading
import time
import importlib.util
import logging
import os
from shared.protocol import (
    decode_message, encode_message,
    REGISTER_WORKER, RESULT_RETURN
)
from shared.task import Task
from pathlib import Path
import sys
import signal

HEARTBEAT = "HEARTBEAT"

DISPATCHER_ADDRESS = ("dispatcher", 4000)
NAMESERVICE_ADDRESS = ("nameservice", 5001)

WORKER_TYPE = sys.argv[1] if len(sys.argv) > 1 else "reverse"
WORKER_PORT = 6000

# Logging configuration
LOG_DIR = os.environ.get("LOG_DIR", ".")
LOG_PATH = os.path.join(LOG_DIR, f"worker_{WORKER_TYPE}.log")
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

RECEIVE_BUFFER_SIZE = 4096

def load_allowed_task_types():
    """
    Load allowed task types from the 'worker_types' directory.
    This function inspects the directory named "worker_types" located in the same directory as this file. 
    It gathers the stem (filename without extension) from each Python file present in that directory, 
    excluding the "__init__.py" file, and returns them as a set.
    Returns:
        set: A set of strings representing the allowed task types, derived from the filenames in the directory.
    """
    
    types_path = Path(__file__).parent / "worker_types"
    return {
        f.stem for f in types_path.glob("*.py")
        if f.is_file() and f.name != "__init__.py"
    }

ALLOWED_TASK_TYPES = load_allowed_task_types()

def import_task_handler(task_type):
    """
    Imports and returns a module that handles a task based on its type.
    This function dynamically imports a task handler module located in the "worker_types" 
    subdirectory relative to the current file. The module filename is derived from the
    provided task type.
    Args:
        task_type (str): The name of the task type. This is used to construct the module's
                         filename (e.g., "example" corresponds to "example.py").
    Returns:
        module: The imported module object corresponding to the provided task type.
    Note:
        This function assumes that the module file exists in the expected directory structure.
        Errors during module loading (e.g., file not found, syntax errors in the module) will
        propagate as exceptions.
    """
    module_path = Path(__file__).parent / "worker_types" / f"{task_type}.py"
    spec = importlib.util.spec_from_file_location(task_type, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def get_container_address():
    """
    Determines and returns the container's network address as a string in the format "<ip>:<port>".
    This function attempts to determine the container's IP address by creating a UDP socket that connects to
    Google's public DNS server (8.8.8.8) on port 80. The IP address is extracted from the socket's own address.
    If any exception occurs during this process, it falls back to resolving the hostname's IP address using the
    socket's gethostbyname method. The returned string appends the port number (WORKER_PORT) to the IP address.
    Returns:
        str: The container's address in the format "<ip>:<port>".
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
    except Exception:
        ip = socket.gethostbyname(socket.gethostname())
    return f"{ip}:{WORKER_PORT}"

def register_with_nameservice(max_attempts=10, delay=1):
    """
    Attempts to register the worker with the nameservice by sending a registration message
    that includes the worker type and container address.

    This function will try to register the worker up to 'max_attempts' times, waiting 'delay'
    seconds between each attempt. On each try, it sends a message via a UDP socket to the nameservice
    and waits for a response. If the registration is successful, it logs the response and returns.
    If all attempts fail, it logs an error and exits the program.

    Parameters:
        max_attempts (int, optional): The maximum number of registration attempts (default is 10).
        delay (int, optional): The delay in seconds between successive registration attempts (default is 1).

    Returns:
        None

    Side Effects:
        - May exit the program if registration fails after the maximum number of attempts.
        - Logs registration status and errors.
    """

    msg = encode_message(REGISTER_WORKER, {
        "type": WORKER_TYPE.lower(),
        "address": get_container_address()
    })

    for attempt in range(1, max_attempts + 1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1)
            sock.sendto(msg, NAMESERVICE_ADDRESS)
            data, _ = sock.recvfrom(RECEIVE_BUFFER_SIZE)
            _, response = decode_message(data)
            logging.info(f"Registered with nameservice: {response}")
            return
        except Exception as e:
            logging.warning(f"Registration attempt {attempt}/{max_attempts} failed: {e}")
            time.sleep(delay)

    logging.error("Could not register with nameservice after several attempts. Exiting.")
    sys.exit(1)

def deregister_with_nameservice():
    """
    Deregister the worker from the nameservice.
    This function creates a UDP socket, encodes a deregistration message containing the worker type and its address,
    and sends the message to the nameservice. If the message is sent successfully, an informational log is recorded.
    If an error occurs during this process, the exception is caught and an error log is recorded.
    Raises:
        Exception: If any error occurs during socket creation, message encoding, or sending.
    """
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        msg = encode_message("DEREGISTER_WORKER", {
            "type": WORKER_TYPE.lower(),
            "address": get_container_address()
        })
        sock.sendto(msg, NAMESERVICE_ADDRESS)
        logging.info(f"Deregistered from nameservice as type '{WORKER_TYPE}' on port {WORKER_PORT}")
    except Exception as e:
        logging.error(f"Failed to deregister from nameservice: {e}")

def send_heartbeat():
    """
    Send heartbeat message in an infinite loop.
    Creates a UDP socket and continuously sends a heartbeat message to the name service.
    The heartbeat message includes the worker type (as a lowercase string) and the container's address.
    If sending the message is successful, a debug log is recorded; otherwise, an error log is recorded.
    The function pauses for 10 seconds between each heartbeat message.
    Note:
        This function runs indefinitely, so it should be executed in a separate thread or process
        to avoid blocking the main execution flow.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    msg = encode_message(HEARTBEAT, {
        "type": WORKER_TYPE.lower(),
        "address": get_container_address()
    })
    while True:
        try:
            sock.sendto(msg, NAMESERVICE_ADDRESS)
            logging.debug("Heartbeat sent")
        except Exception as e:
            logging.error(f"Failed to send heartbeat: {e}")
        time.sleep(10)

def handle_shutdown(signum, frame):
    """
    Handles the shutdown process by deregistering the worker from the name service,
    logging the shutdown event, and exiting the application.
    Parameters:
        signum (int): The signal number triggering the shutdown.
        frame (FrameType): The current stack frame (unused).
    This function performs cleanup operations and then terminates the program
    with an exit code of 0.
    """
    deregister_with_nameservice()
    logging.info("Worker shutting down...")
    sys.exit(0)

def send_result(task_id, result):
    """
    Send the result of a completed task to the dispatcher over a UDP connection.
    Args:
        task_id: The unique identifier of the task.
        result: The result produced by the task.
    Side Effects:
        - Creates a new UDP socket to send the result.
        - Logs the operation using logging.info.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    msg = encode_message(RESULT_RETURN, {
        "task_id": task_id,
        "result": result
    })
    sock.sendto(msg, DISPATCHER_ADDRESS)
    logging.info(f"Sent result for task {task_id}: {result}")

def process_task(task_data):
    """
    Processes a task based on the provided task data by performing the following steps:
    1. Instantiates a Task object using the given task_data.
    2. Logs the start of task processing.
    3. Validates the task type against a set of allowed types.
    4. Dynamically imports the corresponding task handler module.
    5. Executes the handler on the task payload.
    6. Updates the task status to "done" if processing succeeds; otherwise, sets it to "failed" and logs the error.
    7. Records the completion timestamp.
    8. Sends the processing result using the send_result function.
    Parameters:
        task_data (dict): A dictionary containing the necessary parameters to construct a Task object,
                          including fields such as 'id', 'type', and 'payload'.
    Raises:
        ValueError: If the task type is not in ALLOWED_TASK_TYPES.
    Side Effects:
        - Logs processing details and errors.
        - Updates the Task object's status and completion timestamp.
        - Invokes send_result to deliver the result.
    """
    task = Task(**task_data)
    logging.info(f"Processing task {task.id} of type '{task.type}' with payload: {task.payload}")
    try:
        if task.type not in ALLOWED_TASK_TYPES:
            raise ValueError(f"Invalid task type: {task.type}")
        module = import_task_handler(task.type)
        result = module.handle(task.payload)
        task.status = "done"
    except Exception as e:
        result = f"Error processing task: {e}"
        task.status = "failed"
        logging.error(f"Failed to process task {task.id}: {e}")
    finally:
        task.timestamp_completed = time.time()

    send_result(task.id, result)

def run_worker():
    """
    Runs the worker process that listens for tasks via UDP and processes them concurrently.
    This function performs the following steps:
    1. Registers the worker with a name service.
    2. Creates a UDP socket bound to "0.0.0.0" on the specified WORKER_PORT.
    3. Logs that it is listening on the port as the defined WORKER_TYPE.
    4. Sets up signal handlers for SIGINT and SIGTERM to allow graceful shutdown via the handle_shutdown function.
    5. Starts a daemon thread to periodically send heartbeat messages (using the send_heartbeat function) to indicate the worker is alive.
    6. Enters an infinite loop to receive data (up to RECEIVE_BUFFER_SIZE) from the socket. For each received task:
        - Logs the address of the sender.
        - Decodes the received data using decode_message.
        - Starts a new thread to process the task content by invoking process_task.
    The function does not return any value and is designed to run continuously until interrupted.
    """
    
    register_with_nameservice()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", WORKER_PORT))
    logging.info(f"Listening on port {WORKER_PORT} as type '{WORKER_TYPE}'")

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    threading.Thread(target=send_heartbeat, daemon=True).start()

    while True:
        data, addr = sock.recvfrom(RECEIVE_BUFFER_SIZE)
        logging.info(f"Received task from {addr}")
        _, content = decode_message(data)
        threading.Thread(target=process_task, args=(content,)).start()

if __name__ == "__main__":
    run_worker()