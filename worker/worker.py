import socket
import threading
import time
import importlib
from shared.protocol import (
    decode_message, encode_message,
    REGISTER_WORKER, RESULT_RETURN
)
from shared.task import Task
import json
import sys

DISPATCHER_ADDRESS = ("dispatcher", 4000)
NAMESERVICE_ADDRESS = ("nameservice", 5000)

WORKER_TYPE = sys.argv[1] if len(sys.argv) > 1 else "reverse"
WORKER_PORT = 6000

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
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    msg = encode_message(REGISTER_WORKER, {
        "type": WORKER_TYPE,
        "address": f"worker:{WORKER_PORT}"
    })
    sock.sendto(msg, NAMESERVICE_ADDRESS)
    print(f"[Worker-{WORKER_TYPE}] Registered with nameservice")


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
    print(f"[Worker-{WORKER_TYPE}] Sent result for task {task_id}")


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
    try:
        if task.type not in ALLOWED_TASK_TYPES:
            raise ValueError(f"Invalid task type: {task.type}")
        module = importlib.import_module(f"worker.worker_types.{task.type}")
        result = module.handle(task.payload)
        task.status = "done"
    except Exception as e:
        result = f"Error processing task: {e}"
        task.status = "failed"
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
    print(f"[Worker-{WORKER_TYPE}] Listening on port {WORKER_PORT}")

    while True:
        data, addr = sock.recvfrom(RECEIVE_BUFFER_SIZE)
        _, content = decode_message(data)
        threading.Thread(target=process_task, args=(content,)).start()


if __name__ == "__main__":
    run_worker()