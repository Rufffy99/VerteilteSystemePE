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
    Loads allowed task types by scanning the "worker_types" directory located alongside this file.
    This function examines each Python file in the "worker_types" directory (ignoring any non-file entries and the "__init__.py" file) and extracts the stem (filename without the extension) from valid files. The resulting set of strings represents the task types allowed in the worker.
    Returns:
        set: A set of task type names (as strings) extracted from the valid Python files.
    """
    
    types_path = Path(__file__).parent / "worker_types"
    return {
        f.stem for f in types_path.glob("*.py")
        if f.is_file() and f.name != "__init__.py"
    }

ALLOWED_TASK_TYPES = load_allowed_task_types()

def import_task_handler(task_type):
    """
    Imports and returns a task handler module corresponding to the given task_type.
    This function constructs a file path based on the current file's directory and
    assumes that the corresponding module is located in the "worker_types" subdirectory
    with a filename matching the pattern "<task_type>.py". It dynamically imports the module
    using importlib utilities and returns the module object.
    Parameters:
        task_type (str): The type of task handler to import, corresponding to the module
                         filename (without the .py extension) in the "worker_types" directory.
    Returns:
        module: The imported Python module corresponding to the given task_type.
    Raises:
        FileNotFoundError: If the module file does not exist at the constructed path.
        ImportError: If there is an error during the import of the module.
    """
    
    module_path = Path(__file__).parent / "worker_types" / f"{task_type}.py"
    spec = importlib.util.spec_from_file_location(task_type, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def get_container_address():
    """
    Returns the address of the container or host running the worker.
    This function retrieves the container name from the "HOSTNAME" environment variable if available. If not,
    it uses the host's machine name via socket.gethostname(). It then formats the result by appending the 
    WORKER_PORT to form an address string in the format "<container_name>:<WORKER_PORT>".
    Returns:
        str: The formatted address string for the container or host.
    """
    container_name = os.environ.get("HOSTNAME", socket.gethostname())
    return f"{container_name}:{WORKER_PORT}"

def register_with_nameservice():
    """
    Registers the worker with the nameservice.
    This function performs the following operations:
    1. Creates a UDP socket for communication.
    2. Builds a registration message by encoding the worker's information, which includes:
        - The message type (REGISTER_WORKER)
        - The worker type (WORKER_TYPE)
        - The worker address, formatted as "worker:<WORKER_PORT>".
    3. Sends the encoded message to the nameservice at NAMESERVICE_ADDRESS using the UDP protocol.
    4. Prints a confirmation message indicating the worker has been successfully registered.
    Note:
    Ensure that the following variables and functions are defined in the current context:
         - REGISTER_WORKER
         - WORKER_TYPE
         - WORKER_PORT
         - NAMESERVICE_ADDRESS
         - encode_message
    """
    import socket as pysocket
    hostname = socket.gethostname()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    msg = encode_message(REGISTER_WORKER, {
        "type": WORKER_TYPE,
        "address":f"{get_container_address()}"
    })
    sock.sendto(msg, NAMESERVICE_ADDRESS)
    logging.info(f"Registered with nameservice as type '{WORKER_TYPE}' on port {WORKER_PORT}")

def deregister_with_nameservice():
    """
    Deregisters the worker from the nameservice.
    This function creates a UDP socket, constructs a deregistration message with
    the worker type and address, and sends it to the nameservice. The operation is
    logged to provide information about the deregistration event, including the
    worker type and port.
    Side Effects:
        - Sends a UDP message to the nameservice for deregistration.
        - Logs the deregistration process using the logging system.
    Exceptions:
        - May raise socket-related exceptions if there are issues with network communication.
    """
    
    hostname = socket.gethostname()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    msg = encode_message("DEREGISTER_WORKER", {
        "type": WORKER_TYPE,
        "address":f"{get_container_address()}"
    })
    sock.sendto(msg, NAMESERVICE_ADDRESS)
    logging.info(f"Deregistered from nameservice as type '{WORKER_TYPE}' on port {WORKER_PORT}")

def send_heartbeat():
    """
    Sends periodic heartbeat messages to the nameservice.
    This function creates a UDP socket and constructs a heartbeat message containing
    the worker's type and address. It then enters an infinite loop where it sends the
    heartbeat message to a predefined nameservice address every 10 seconds. Any errors
    encountered during the send operation are logged.
    Note:
        This function relies on external definitions such as:
        - encode_message: To encode the heartbeat message.
        - HEARTBEAT: The message type for heartbeat messages.
        - WORKER_TYPE: The type of worker sending the message.
        - WORKER_PORT: The port on which the worker is accessible.
        - NAMESERVICE_ADDRESS: The address of the nameservice to send the heartbeat to.
    """
    
    hostname = socket.gethostname()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    msg = encode_message(HEARTBEAT, {
        "type": WORKER_TYPE,
        "address":f"{get_container_address()}"
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
    Handles graceful shutdown upon receiving a termination signal.
    Args:
        signum (int): The numeric identifier of the signal.
        frame (frame object): The current stack frame when the signal was received.
    The function deregisters the worker from the nameservice, logs a shutdown message,
    and terminates the process by exiting with a status code of 0.
    """
    
    deregister_with_nameservice()
    logging.info("Worker shutting down...")
    sys.exit(0)

def send_result(task_id, result):
    """
    Sends the result of a completed task to the dispatcher over a UDP socket.
    Parameters:
        task_id: The unique identifier of the task.
        result: The outcome/result of the task to be sent.
    Behavior:
        - Encodes the result and the task_id into a message using the `encode_message` function with a message type of RESULT_RETURN.
        - Sends the encoded message to the dispatcher specified by DISPATCHER_ADDRESS using a UDP socket.
        - Prints a log message indicating the result for the task has been sent, including the WORKER_TYPE and task_id.
    Notes:
        - DISPATCHER_ADDRESS, RESULT_RETURN, and WORKER_TYPE are assumed to be pre-defined global constants.
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
    Process a task by dynamically importing the appropriate worker module based on the task type,
    executing its handle function with the task payload, and sending the result.
    Parameters:
        task_data (dict): A dictionary containing task attributes. It should contain at least:
                          - 'type': A string indicating the type of the task, which determines the worker module to import.
                          - 'id': An identifier for the task.
                          - 'payload': The data to be processed by the worker module.
    Behavior:
        - Creates a Task object from the provided task_data.
        - Dynamically imports the module from "worker.worker_types" corresponding to the task type.
        - Executes the module's handle function using the task payload.
        - Catches any exceptions raised during processing, setting the result to an error message.
        - Sends the task ID and the resulting value (or error message) using send_result.
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
    Initializes and runs the worker service.
    This function performs the following steps:
    1. Registers the worker with a name service.
    2. Creates a UDP socket and binds it to all interfaces ('0.0.0.0') on the specified WORKER_PORT.
    3. Logs the startup message indicating the type of worker and the port it is listening on.
    4. Enters an infinite loop to:
        - Receive messages (up to 4096 bytes).
        - Decode the received message to extract its content.
        - Spawn a new thread to process the task using the decoded content.
    Note:
    - The function depends on several external components: register_with_nameservice, WORKER_PORT, WORKER_TYPE, decode_message, and process_task.
    - Error handling is not explicitly performed within this function; any exceptions from socket operations or message decoding will propagate.
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