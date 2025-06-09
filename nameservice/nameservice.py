import socket
import threading
import json
import logging
import os
import time
from shared.protocol import decode_message, encode_message, REGISTER_WORKER, LOOKUP_WORKER, DEREGISTER_WORKER, HEARTBEAT

PORT = 5001
HOST = "0.0.0.0"

HEARTBEAT_TIMEOUT = 30  # seconds

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
    Handle an incoming request by decoding the message, performing the appropriate registry operations based on its type,
    and sending a response back to the originating address.
    Parameters:
        data (bytes): The raw data received from the network.
        addr (tuple): A tuple containing the sender's address information, where the first element is the IP address.
        sock (socket.socket): The UDP socket used for sending the response.
    The function processes various message types:
        - REGISTER_WORKER: Registers a new worker by storing its type, address (derived from IP and a fixed port), and current time.
        - LOOKUP_WORKER: Looks up an active worker entry for the given type, ensuring that the last seen timestamp meets the heartbeat timeout criteria.
        - DEREGISTER_WORKER: Removes registry entries corresponding to the sender's address.
        - HEARTBEAT: Updates the last seen timestamp for worker entries matching the sender's address.
        - LIST_WORKERS: Returns a list of active workers (those whose last seen timestamp is within the heartbeat timeout).
        - Any other message type results in an error message being returned.
    The function uses global/shared variables such as:
        - registry: A dictionary mapping worker types to their registration details (address and last seen timestamp).
        - registry_lock: A lock to ensure thread-safe updates to the registry.
        - HEARTBEAT_TIMEOUT: A threshold that determines whether a registered worker is still active.
    Exceptions:
        - If the incoming message cannot be decoded, an error is logged and no action is taken.
        - If there is an error while sending the response, an error is logged.
    Returns:
        None: The response is sent directly over the provided socket.
    """
    logging.info(f"Received data from {addr}")
    try:
        msg_type, content = decode_message(data)
        logging.info(f"Decoded message type: {msg_type} with content: {content} from {addr}")
    except Exception as e:
        logging.error(f"Failed to decode message from {addr}: {e}")
        return

    if msg_type == REGISTER_WORKER:
        wtype = content.get("type")
        ip = addr[0]
        port = 6000
        address = f"{ip}:{port}"
        with registry_lock:
            registry[wtype] = {"address": address, "last_seen": time.time()}
        response = {"message": f"Registered {wtype} at {address}"}
        logging.info(f"Registered worker '{wtype}' at address {address}")

    elif msg_type == LOOKUP_WORKER:
        wtype = content.get("type")
        with registry_lock:
            entry = registry.get(wtype)
            if entry and time.time() - entry["last_seen"] <= HEARTBEAT_TIMEOUT:
                response = {"address": entry["address"]}
                logging.info(f"Lookup for worker type '{wtype}' succeeded: {entry['address']}")
            else:
                response = {"error": f"No active worker found for type '{wtype}'"}
                logging.warning(f"Lookup for worker type '{wtype}' failed: no active entry found")

    elif msg_type == DEREGISTER_WORKER:
        ip = addr[0]
        port = 6000
        address = f"{ip}:{port}"
        with registry_lock:
            to_remove = [k for k, v in registry.items() if v["address"] == address]
            for k in to_remove:
                del registry[k]
        response = {"message": f"Deregistered {len(to_remove)} entries"}
        logging.info(f"Deregistered {len(to_remove)} entries for address {address}")

    elif msg_type == HEARTBEAT:
        ip = addr[0]
        port = 6000
        address = f"{ip}:{port}"
        updated = 0
        with registry_lock:
            for entry in registry.values():
                if entry["address"] == address:
                    entry["last_seen"] = time.time()
                    updated += 1
        response = {"message": f"Heartbeat received, updated {updated} entries"}
        logging.info(f"Heartbeat received from {address}, updated {updated} entries")

    elif msg_type == "LIST_WORKERS":
        with registry_lock:
            worker_list = [
                {"type": wtype, "address": entry["address"]}
                for wtype, entry in registry.items()
                if time.time() - entry["last_seen"] <= HEARTBEAT_TIMEOUT
            ]
        response = {"workers": worker_list}
        logging.info(f"LIST_WORKERS responded with {len(worker_list)} active workers")

    else:
        response = {"error": "Unknown message type"}
        logging.warning(f"Received unknown message type: {msg_type}")

    try:
        sock.sendto(encode_message("RESPONSE", response), addr)
        logging.info(f"Sent response to {addr}: {response}")
    except Exception as e:
        logging.error(f"Failed to send response to {addr}: {e}")

def run_nameservice():
    """
    Run the NameService to listen for incoming UDP requests.
    This function creates and binds a UDP socket to the specified HOST and PORT,
    logging a critical error and exiting if the binding fails. Once the socket is
    successfully bound, the function enters an infinite loop to wait for incoming
    data. For each received UDP packet, it logs the source address, spawns a new
    thread to handle the request via the handle_request function, and logs the thread
    creation. Any exceptions or errors encountered while receiving data are logged
    appropriately.
    Returns:
        None
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((HOST, PORT))
        logging.info(f"NameService listening on {HOST}:{PORT}")
    except Exception as e:
        logging.critical(f"Failed to bind socket on {HOST}:{PORT}: {e}")
        return

    while True:
        try:
            data, addr = sock.recvfrom(4096)
            logging.info(f"Incoming connection from {addr}")
            thread = threading.Thread(target=handle_request, args=(data, addr, sock))
            thread.start()
            logging.info(f"Spawned thread {thread.name} to handle request from {addr}")
        except Exception as e:
            logging.error(f"Exception occurred while receiving data: {e}")

if __name__ == "__main__":
    logging.info("Starting nameservice...")
    run_nameservice()