import socket
import threading
import json
import logging
import os
from shared.protocol import decode_message, encode_message, REGISTER_WORKER, LOOKUP_WORKER, DEREGISTER_WORKER

PORT = 5000
HOST = "0.0.0.0"

registry = {}
registry_lock = threading.Lock()

# Logging setup
LOG_DIR = os.environ.get("LOG_DIR", ".")
LOG_PATH = os.path.join(LOG_DIR, "nameservice.log")
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def handle_request(data, addr, sock):
    """
    Handles an incoming network request for worker registration, lookup, or deregistration.
    Parameters:
        data (bytes): The raw incoming message data to be decoded.
        addr (tuple): The address (IP, port) of the client that sent the request.
        sock (socket.socket): The socket object used to send the response back to the client.
    Behavior:
        - Decodes the incoming data to determine the message type and its associated content.
        - For a REGISTER_WORKER message:
              * Extracts the worker type and address from the content.
              * Registers the worker by adding an entry to the global registry.
              * Sends a confirmation response indicating successful registration.
        - For a LOOKUP_WORKER message:
              * Looks up the worker address in the registry based on the provided worker type.
              * Sends the worker’s address if found, otherwise sends an error indicating that no worker was found.
        - For a DEREGISTER_WORKER message:
              * Finds and removes all registry entries matching the provided worker address.
              * Sends a response indicating how many entries were deregistered.
        - For any other message types:
              * Sends an error response indicating an unknown message type.
    Side Effects:
        - Modifies the global registry in the case of registration and deregistration requests.
        - Sends a response message to the client using sock.sendto().
    """
    
    msg_type, content = decode_message(data)
    
    if msg_type == REGISTER_WORKER:
        wtype = content.get("type")
        address = content.get("address")
        with registry_lock:
            registry[wtype] = address
        response = {"message": f"Registered {wtype} at {address}"}
        logging.info(f"Registered worker '{wtype}' at address {address}")
    
    elif msg_type == LOOKUP_WORKER:
        wtype = content.get("type")
        with registry_lock:
            address = registry.get(wtype)
        if address:
            response = {"address": address}
            logging.info(f"Lookup for worker type '{wtype}' succeeded: {address}")
        else:
            response = {"error": f"No worker found for type '{wtype}'"}
            logging.warning(f"Lookup for worker type '{wtype}' failed: no entry found")

    elif msg_type == DEREGISTER_WORKER:
        address = content.get("address")
        to_remove = [k for k, v in registry.items() if v == address]
        for k in to_remove:
            del registry[k]
        response = {"message": f"Deregistered {len(to_remove)} entries"}
        logging.info(f"Deregistered {len(to_remove)} entries for address {address}")
    
    else:
        response = {"error": "Unknown message type"}
        logging.warning(f"Received unknown message type: {msg_type}")

    sock.sendto(encode_message("RESPONSE", response), addr)


def run_nameservice():
    """
    Run the name service by binding a UDP socket to the configured HOST and PORT and listening for incoming requests.
    This function performs the following steps:
        1. Creates a UDP socket.
        2. Binds the socket to the host and port specified by the global variables HOST and PORT.
        3. Enters an infinite loop to listen for data on the socket.
        4. For each incoming request, spawns a new thread to handle the request by calling the handle_request function.
    Notes:
        - The run_nameservice function assumes that the variables HOST and PORT are defined externally.
        - The handle_request function should be implemented to process each request appropriately.
    """
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    logging.info(f"[NameService] Listening on {HOST}:{PORT}")
    
    while True:
        data, addr = sock.recvfrom(4096)
        threading.Thread(target=handle_request, args=(data, addr, sock)).start()


if __name__ == "__main__":
    run_nameservice()
