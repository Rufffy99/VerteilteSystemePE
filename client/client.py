import socket
import json
import sys
import logging
import os
import random
import argparse

try:
    from shared.protocol import encode_message, decode_message, POST_TASK, GET_RESULT
except ModuleNotFoundError as e:
    print("❌ Fehler beim Import von shared:", e)
    print("Stelle sicher, dass PYTHONPATH korrekt gesetzt ist und der Ordner shared/ vorhanden ist.")
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


def send_task(task_type, payload):
    """
    Send a task to the dispatcher using a UDP socket.
    This function constructs a message containing the task type and payload, 
    encodes it with the POST_TASK operation, and sends it to the dispatcher.
    It then waits for a response from the dispatcher, decodes the response,
    and prints a confirmation message.
    Parameters:
        task_type: The type of the task to be sent.
        payload: The associated data for the task.
    Notes:
        - It uses a UDP socket to handle the communication.
        - The functions 'encode_message' and 'decode_message' are used for 
          message formatting and parsing respectively.
        - The constant 'DISPATCHER_ADDRESS' must be defined to specify the 
          target address for the dispatcher.
    Returns:
        None
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        msg = encode_message(POST_TASK, {
            "type": task_type,
            "payload": payload
        })
        sock.sendto(msg, DISPATCHER_ADDRESS)
        logging.info(f"Sent task to dispatcher: type={task_type}, payload={payload}")

        data, _ = sock.recvfrom(4096)
        _, response = decode_message(data)
        logging.info(f"Dispatcher responded to task submission: {response}")
        print("→ Aufgabe gesendet:", response)


def request_result(task_id):
    """
    Send a GET_RESULT request to the dispatcher to retrieve the result of a task.
    This function creates a UDP socket, encodes a GET_RESULT message with the given task ID,
    and sends it to the dispatcher. It then waits for the dispatcher's response, decodes the
    received message, and prints the result.
    Parameters:
        task_id: The unique identifier of the task whose result is being requested.
    Returns:
        None
    Side Effects:
        Outputs the result of the task to the console.
    Note:
        This function relies on the global variables GET_RESULT and DISPATCHER_ADDRESS,
        as well as the helper functions encode_message() and decode_message().
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        msg = encode_message(GET_RESULT, {
            "task_id": task_id
        })
        sock.sendto(msg, DISPATCHER_ADDRESS)
        logging.info(f"Requested result for task ID: {task_id}")

        data, _ = sock.recvfrom(4096)
        _, response = decode_message(data)
        logging.info(f"Dispatcher returned result: {response}")
        print("→ Ergebnisabfrage:", response)

import time

def simulate():
    """
    Simulates the execution of multiple tasks by sending task requests over UDP and querying for their results.
    Procedure:
        1. Loads the list of tasks from a 'tasks.json' file located in the same directory.
        2. For each task, creates a UDP socket to send a task message (with type and payload) to a dispatcher.
        3. Receives and logs the response for each submitted task, extracting and storing task IDs if available.
        4. After every QUERY_INTERVAL tasks, selects up to 3 random tasks from the list and queries their intermediate results,
           logging the responses.
        5. Waits for a short delay after all tasks have been processed, then performs a final query for the results of all tasks,
           printing the final responses.
    Notes:
        - If the 'tasks.json' file is not found, the function prints an error and exits.
        - Exceptions during socket communication or message processing are caught and logged or printed.
        - The function uses timing delays to simulate processing intervals and final result waiting.
    Returns:
        None
    """
    print("Simuliere mehrere Aufgaben...")
    logging.info("Simulating multiple tasks...")

    task_file = os.path.join(os.path.dirname(__file__), "tasks.json")
    if not os.path.isfile(task_file):
        print(f"❌ Aufgaben-Datei '{task_file}' nicht gefunden.")
        return

    with open(task_file, "r") as f:
        tasks = json.load(f)

    ids = []
    QUERY_INTERVAL = 5  # Alle 5 Tasks zwischendurch Ergebnisse abfragen

    for i, (task_type, payload) in enumerate(tasks):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            msg = encode_message(POST_TASK, {
                "type": task_type,
                "payload": payload
            })
            sock.sendto(msg, DISPATCHER_ADDRESS)
            try:
                data, _ = sock.recvfrom(4096)
                _, response = decode_message(data)
                print(f"→ Aufgabe '{task_type}' gesendet:", response)
                logging.info(f"[SIMULATION] Task '{task_type}' sent with payload: {payload}")
                if "message" in response and "ID" in response["message"]:
                    try:
                        task_id = int(response["message"].split("=")[-1].strip())
                        ids.append(task_id)
                    except Exception:
                        pass
            except Exception as e:
                print("Fehler beim Senden:", e)

        if (i + 1) % QUERY_INTERVAL == 0 and ids:
            logging.info(f"[SIMULATION] Intermediate results after {i + 1} tasks")
            for tid in random.sample(ids, min(3, len(ids))):  # max. 3 zufällige Ergebnisse
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    msg = encode_message(GET_RESULT, {
                        "task_id": tid
                    })
                    sock.sendto(msg, DISPATCHER_ADDRESS)
                    try:
                        data, _ = sock.recvfrom(4096)
                        _, response = decode_message(data)
                        logging.info(f"[SIMULATION] Intermediate result for task {tid}: {response}")
                    except Exception as e:
                        logging.error(f"Fehler beim Abfragen von Task {tid}: {e}")

        time.sleep(1)

    print("\nWarte 5 Sekunden auf finale Verarbeitung...\n")
    time.sleep(5)

    print("\nFinale Ergebnisabfrage:\n")
    for task_id in ids:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            msg = encode_message(GET_RESULT, {
                "task_id": task_id
            })
            sock.sendto(msg, DISPATCHER_ADDRESS)
            try:
                data, _ = sock.recvfrom(4096)
                _, response = decode_message(data)
                print(f"→ Ergebnis für Task {task_id}:", response)
            except Exception as e:
                print("Fehler beim Abfragen:", e)

def main():
    """
    Main entry point of the client application.
    This function processes command line arguments to either send a new task or request
    the result of an existing task.
    Usage:
        python client.py send <type> <payload>
            - Sends a new task with the specified type and payload.
        python client.py result <task_id>
            - Requests the result for the task identified by task_id.
    Behavior:
        - If no or insufficient arguments are provided, it prints the usage instructions.
        - For the "send" command, it expects exactly two additional arguments (task type and payload).
        - For the "result" command, it expects exactly one additional argument (the numeric task ID).
        - Invalid arguments result in an error message indicating the usage format.
    """
    parser = argparse.ArgumentParser(description="Client für das Verteilte-System.")
    parser.add_argument("--dispatcher-ip", default="127.0.0.1", help="IP-Adresse des Dispatchers (Standard: 127.0.0.1)")
    args, unknown = parser.parse_known_args()

    global DISPATCHER_ADDRESS
    DISPATCHER_ADDRESS = (args.dispatcher_ip, 4000)

    logging.info("Client started!")
    if len(sys.argv) < 2:
        logging.error("Invalid arguments provided.")

        print("Usage:")
        print("  New Task: python client.py send <type> <payload>")
        print("  Query Result: python client.py result <task_id>")
        print("  Simulation: python client.py simulate")
        print("  Run Idle: python client.py run")
        return

    command = sys.argv[1]
    if command == "send" and len(sys.argv) == 4:
        send_task(sys.argv[2], sys.argv[3])
    elif command == "result" and len(sys.argv) == 3:
        try:
            task_id = int(sys.argv[2])
            request_result(task_id)
        except ValueError:
            logging.error("Invalid task ID format: not an integer.")
    elif command == "simulate":
        simulate()
    elif command == "run":
        print("Client im Wartezustand. Beende mit STRG+C.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Client beendet.")
    else:
        logging.error("Invalid arguments provided.")
        

if __name__ == "__main__":
    main()