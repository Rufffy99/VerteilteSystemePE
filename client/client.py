import socket
import json
import sys
import logging
import os
import random
import argparse
import time

try:
    from shared.protocol import encode_message, decode_message, POST_TASK, GET_RESULT
except ModuleNotFoundError as e:
    print("Error importing shared module:", e)
    print("Make sure PYTHONPATH is set correctly and the shared/ directory exists.")
    sys.exit(1)

LOG_DIR = os.environ.get("LOG_DIR", ".")
LOG_PATH = os.path.join(LOG_DIR, "client.log")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

DISPATCHER_ADDRESS = None
MAX_RETRIES = 5
RETRY_DELAY = 1  # seconds

def send_with_retry(msg, address):
    """
    Send a message reliably over UDP with retry attempts.
    This function sends a given message to a specified address using UDP. It attempts
    to receive a response within a set timeout period. If the response is not received before
    the timeout expires, it retries sending the message up to MAX_RETRIES times, waiting for
    RETRY_DELAY seconds between each attempt.
    Parameters:
        msg (bytes): The message to be sent.
        address (tuple): The destination address as a tuple (host, port).
    Returns:
        Any: The decoded response from the server if a response is received within the allowed
             number of retries. The response is expected to be the second element of the tuple
             returned by the decode_message function.
        None: If no response is received after MAX_RETRIES attempts.
    """
    
    for attempt in range(MAX_RETRIES):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(msg, address)
            sock.settimeout(2)
            try:
                data, _ = sock.recvfrom(4096)
                return decode_message(data)[1]
            except socket.timeout:
                logging.warning(f"Timeout on attempt {attempt + 1}, retrying...")
                time.sleep(RETRY_DELAY)
    return None

def send_task(task_type, payload):
    """
    Sends a task message to the dispatcher with the specified task type and payload.
    This function constructs a message by encoding the task type and payload, then sends it to a predetermined dispatcher address.
    If a response is received from the dispatcher, it prints the response. Otherwise, it prints an error message indicating
    that the dispatcher is unreachable.
    Parameters:
        task_type: The type identifier for the task to be processed by the dispatcher.
        payload: The data or parameters associated with the task.
    Returns:
        None
    """
    
    msg = encode_message(POST_TASK, {
        "type": task_type,
        "payload": payload
    })
    print(f"Sending to dispatcher {DISPATCHER_ADDRESS[0]}:{DISPATCHER_ADDRESS[1]} - Type: {task_type}, Payload: {payload}")
    response = send_with_retry(msg, DISPATCHER_ADDRESS)
    if response:
        print("Task sent:", response)
    else:
        print("Task could not be sent. Dispatcher not reachable.")

def request_result(task_id):
    """
    Request and print the result for a given task from the dispatcher.
    This function encodes a GET_RESULT message with the provided task_id, sends it to the dispatcher
    using a retry mechanism, and then prints the response if received. If the dispatcher is not reachable,
    it prints an error message.
    Parameters:
        task_id (int or str): The identifier of the task for which the result is being requested.
    Side Effects:
        Prints output to the console indicating the status of the request and the received result.
    """
    
    msg = encode_message(GET_RESULT, {"task_id": task_id})
    print(f"Requesting result from dispatcher {DISPATCHER_ADDRESS[0]}:{DISPATCHER_ADDRESS[1]} - Task ID: {task_id}")
    response = send_with_retry(msg, DISPATCHER_ADDRESS)
    if response:
        print("Result received:", response)
    else:
        print("Result could not be retrieved. Dispatcher not reachable.")

def simulate():
    """
    Simulates the processing of multiple tasks by reading them from a JSON file, sending them to a dispatcher, 
    and then periodically querying for intermediate and final results.
    This function performs the following operations:
    1. Logs and prints the start of the simulation.
    2. Constructs the path to "tasks.json" (expected to be in the same directory) and checks its existence.
    3. Loads tasks from the JSON file, where each task is defined by a task type and its payload.
    4. Iterates over the tasks:
        - Encodes a POST_TASK message for each task and sends it to the dispatcher.
        - Logs and prints information about the sent task.
        - Extracts and records the task ID from the response if available.
        - Every QUERY_INTERVAL tasks, randomly selects up to 3 recorded task IDs to query for intermediate results.
    5. Waits for a short period to allow processing, then queries the dispatcher for the final results of all tasks.
    6. Outputs the final results or an error if results cannot be retrieved.
    Note:
    - The function relies on external functions and constants such as encode_message, send_with_retry, 
      POST_TASK, GET_RESULT, DISPATCHER_ADDRESS, and standard modules (e.g., os, json, logging, time, random).
    - Ensure that the "tasks.json" file exists in the expected directory, as its absence will lead to an early exit.
    """
    
    print("Simulating multiple tasks...")
    logging.info("Simulating multiple tasks...")
    logging.info("Dispatcher address: %s", DISPATCHER_ADDRESS)

    task_file = os.path.join(os.path.dirname(__file__), "tasks.json")
    if not os.path.isfile(task_file):
        print(f"Task file '{task_file}' not found.")
        return

    with open(task_file, "r") as f:
        tasks = json.load(f)

    ids = []
    QUERY_INTERVAL = 5

    for i, (task_type, payload) in enumerate(tasks):
        msg = encode_message(POST_TASK, {
            "type": task_type,
            "payload": payload
        })
        response = send_with_retry(msg, DISPATCHER_ADDRESS)
        if response:
            print(f"Task '{task_type}' sent with payload: {payload}")
            logging.info(f"Task '{task_type}' sent with payload: {payload}")
            if "message" in response and "ID" in response["message"]:
                try:
                    task_id = int(response["message"].split("=")[-1].strip())
                    ids.append(task_id)
                except Exception:
                    pass
        else:
            logging.error(f"Failed to send task '{task_type}'")

        if (i + 1) % QUERY_INTERVAL == 0 and ids:
            for tid in random.sample(ids, min(3, len(ids))):
                msg = encode_message(GET_RESULT, {"task_id": tid})
                response = send_with_retry(msg, DISPATCHER_ADDRESS)
                if response:
                    print(f"Intermediate result for task {tid}:", response)
                else:
                    print(f"Failed to retrieve result for task {tid}")

        time.sleep(1)

    print("\nWaiting 5 seconds for final processing...\n")
    time.sleep(5)

    print("\nFinal result query:\n")
    for task_id in ids:
        msg = encode_message(GET_RESULT, {"task_id": task_id})
        response = send_with_retry(msg, DISPATCHER_ADDRESS)
        if response:
            print(f"Result for task {task_id}:", response)
        else:
            print(f"Result for task {task_id} could not be retrieved.")

def main():
    """
    Main entry point for the client application.
    Parses command-line arguments to determine the operation mode and execute the corresponding actions:
        - "send": Sends a new task to the dispatcher. Requires two additional arguments: task type and payload.
        - "result": Requests the outcome of a previously sent task. Requires one additional argument: the task ID (an integer).
        - "simulate": Runs the simulation mode.
        - "run": Initiates interactive mode, allowing repeated commands including "send", "result", and "exit".
    The dispatcher IP is determined by the environment variable DISPATCHER_IP if set;
    otherwise, it defaults to the value provided with the --dispatcher-ip argument (default: "127.0.0.1").
    The dispatcher port is fixed at 4000.
    Usage examples:
        New Task:       python client.py send <type> <payload>
        Query Result:   python client.py result <task_id>
        Simulation:     python client.py simulate
        Interactive:    python client.py run
    Handles improper or missing commands and terminates gracefully on a KeyboardInterrupt.
    """
    
    parser = argparse.ArgumentParser(description="Client for the distributed system.")
    parser.add_argument("--dispatcher-ip", default="127.0.0.1", help="Dispatcher IP address (default: 127.0.0.1)")
    parser.add_argument("command", nargs="?", help="Command: send, result, simulate, run")
    parser.add_argument("arg1", nargs="?", help="Additional argument 1")
    parser.add_argument("arg2", nargs="?", help="Additional argument 2")
    args = parser.parse_args()

    global DISPATCHER_ADDRESS
    dispatcher_ip = os.environ.get("DISPATCHER_IP", args.dispatcher_ip)
    DISPATCHER_ADDRESS = (dispatcher_ip, 4000)

    logging.info("Client started!")
    if not args.command:
        logging.error("No command provided.")
        print("Usage:")
        print("  New Task: python client.py send <type> <payload>")
        print("  Query Result: python client.py result <task_id>")
        print("  Simulation: python client.py simulate")
        print("  Run Idle: python client.py run")
        return

    if args.command == "send" and args.arg1 and args.arg2:
        send_task(args.arg1, args.arg2)
    elif args.command == "result" and args.arg1:
        try:
            task_id = int(args.arg1)
            request_result(task_id)
        except ValueError:
            logging.error("Invalid task ID format: not an integer.")
    elif args.command == "simulate":
        simulate()
    elif args.command == "run":
        print("Interactive mode started. Enter commands below.")
        try:
            while True:
                action = input("What do you want to do? [send/result/exit]: ").strip().lower()
                if action == "send":
                    task_type = input("Task type: ").strip()
                    payload = input("Payload: ").strip()
                    send_task(task_type, payload)
                elif action == "result":
                    task_id = input("Task ID: ").strip()
                    try:
                        task_id = int(task_id)
                        request_result(task_id)
                    except ValueError:
                        print("Invalid Task ID.")
                elif action == "exit":
                    print("Exiting client.")
                    break
                else:
                    print("Invalid command.")
        except KeyboardInterrupt:
            print("Client terminated.")
    else:
        logging.error("Invalid arguments provided.")

if __name__ == "__main__":
    main()