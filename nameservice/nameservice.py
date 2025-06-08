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
    Handles an incoming network request for worker registration, lookup, or deregistration.
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
        port = 6000  # assuming all workers use this port
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
    Run the name service by binding a UDP socket to the configured HOST and PORT.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((HOST, PORT))
        logging.info(f"[NameService] Listening on {HOST}:{PORT}")
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
