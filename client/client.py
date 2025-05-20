import socket
import json
import sys
from shared.protocol import encode_message, decode_message, POST_TASK, GET_RESULT

DISPATCHER_ADDRESS = ("dispatcher", 4000)


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
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    msg = encode_message(POST_TASK, {
        "type": task_type,
        "payload": payload
    })
    sock.sendto(msg, DISPATCHER_ADDRESS)

    data, _ = sock.recvfrom(4096)
    _, response = decode_message(data)
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
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    msg = encode_message(GET_RESULT, {
        "task_id": task_id
    })
    sock.sendto(msg, DISPATCHER_ADDRESS)

    data, _ = sock.recvfrom(4096)
    _, response = decode_message(data)
    print("→ Ergebnisabfrage:", response)

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
    if len(sys.argv) < 2:
        print("Verwendung:")
        print("  Neue Aufgabe: python client.py send <type> <payload>")
        print("  Ergebnis abfragen: python client.py result <task_id>")
        return

    command = sys.argv[1]
    if command == "send" and len(sys.argv) == 4:
        send_task(sys.argv[2], sys.argv[3])
    elif command == "result" and len(sys.argv) == 3:
        request_result(int(sys.argv[2]))
    else:
        print("Ungültige Argumente.")

if __name__ == "__main__":
    main()