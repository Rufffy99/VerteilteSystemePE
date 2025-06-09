from flask import Flask, render_template_string, request, Response
from template import TEMPLATE
import socket
import time
from shared.protocol import encode_message, decode_message, LOOKUP_WORKER
import docker
import logging
import os
import json
import threading


LOG_DIR = os.environ.get("LOG_DIR", ".")
LOG_PATH = os.path.join(LOG_DIR, "monitor.log")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

WORKERS_JSON_PATH = "/app/workers.json"
logging.info(f"Looking for workers.json at: {WORKERS_JSON_PATH}")
def load_worker_config():
    """
    Retrieves worker configuration from a JSON file.
    This function tries to load worker configuration data from the JSON file specified by WORKERS_JSON_PATH.
    If the file is read and parsed successfully, it returns the list of workers found under the "workers" key.
    In case of any error during file access or JSON parsing, the error is logged, and an empty list is returned.
    Returns:
        list: A list of worker configurations if the file exists and is properly formatted, otherwise an empty list.
    """
    
    try:
        with open(WORKERS_JSON_PATH, "r") as f:
            data = json.load(f)
            return data.get("workers", [])
    except Exception as e:
        logging.error(f"Could not load worker config: {e}")
        return []

def load_worker_types():
    """
    Retrieve the names of active worker types from the worker configuration.
    This function loads the worker configuration data using the load_worker_config()
    function and filters the workers to include only those with an 'active' status of True.
    It then returns a list of the names of these active workers.
    Returns:
        list: A list of strings representing the names of active worker types.
    """
    
    workers = load_worker_config()
    return [w["name"] for w in workers if w.get("active") is True]

app = Flask(__name__)

NAMESERVICE_ADDRESS = ("nameservice", 5001)
DISPATCHER_ADDRESS = ("dispatcher", 4000)
RECEIVE_BUFFER_SIZE = 4096

latest_stats = {}
latest_pending_tasks = []


def query_dispatcher_stats():
    """
    Queries the dispatcher for statistics.
    This function sends a "GET_STATS" UDP message to a predefined dispatcher address (DISPATCHER_ADDRESS)
    using a timeout of 1 second. It encodes the request message and sends it over the socket, then waits
    for a response. When a response is received, it decodes the message into a type and content. The function
    verifies that the response type is "RESPONSE" and that the content is a dictionary. If these conditions are met,
    the function returns a tuple containing:
        - A list of pending items (from the "pending" key in the response dictionary).
        - A dictionary of statistics (from the "stats" key in the response dictionary).
    In case of an exception or an invalid response (wrong message type or improperly formatted content),
    the function returns an empty list and an empty dictionary.
    Returns:
        tuple: A tuple containing:
            - list: The list of pending items from the dispatcher, or an empty list if an error occurs.
            - dict: The dictionary of statistics from the dispatcher, or an empty dictionary if an error occurs.
    """
    
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        msg = encode_message("GET_STATS", {})
        sock.sendto(msg, DISPATCHER_ADDRESS)
        data, _ = sock.recvfrom(RECEIVE_BUFFER_SIZE)
        msg_type, content = decode_message(data)
        if msg_type != "RESPONSE" or not isinstance(content, dict):
            return [], {}
        return content.get("pending", []), content.get("stats", {})
    except Exception as e:
        return [], {}

def stats_updater():
    """
    Continuously updates global statistics and pending task counts.
    This function enters an infinite loop, querying the dispatcher for current statistics
    and pending tasks using `query_dispatcher_stats()`. If statistics are returned, it updates
    the global variables `latest_stats` and `latest_pending_tasks` accordingly. The function
    sleeps for 1 second between each iteration to prevent excessive resource usage.
    Global Variables:
        latest_stats: Holds the most recent statistics from the dispatcher.
        latest_pending_tasks: Holds the most recent count of pending tasks.
    Notes:
        - This function is designed to run indefinitely until explicitly interrupted.
        - It assumes that the functions `query_dispatcher_stats()` and `time.sleep()` are
          defined elsewhere in the codebase.
    """
    
    global latest_stats, latest_pending_tasks
    while True:
        pending, stats = query_dispatcher_stats()
        if stats:
            latest_stats = stats
            latest_pending_tasks = pending
        time.sleep(1)

@app.route("/events")
def sse_stream():
    """
    Generates a Server-Sent Events (SSE) stream response.
    This function defines an inner generator function `event_stream` that continuously monitors for updates
    to the latest statistics and pending tasks. It constructs a combined JSON object from these values and compares
    it to the previously sent data. If the data has changed, the new data is formatted as an SSE-compatible message
    and yielded. The generator pauses for one second between each check to control the update frequency.
    Returns:
        Response: A Flask Response object with MIME type "text/event-stream" that streams the event data.
    """
    
    def event_stream():
        last_data = ""
        while True:
            combined = {
                "stats": latest_stats,
                "pending": latest_pending_tasks
            }
            data = json.dumps(combined)
            if data != last_data:
                yield f"data: {data}\n\n"
                last_data = data
            time.sleep(1)
    return Response(event_stream(), mimetype="text/event-stream")


@app.route("/")
def dashboard():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        msg = encode_message("LIST_WORKERS", {})
        sock.sendto(msg, NAMESERVICE_ADDRESS)
        data, _ = sock.recvfrom(RECEIVE_BUFFER_SIZE)
        _, content = decode_message(data)
        worker_info = content.get("workers", [])
        workers_by_address = {}
        for entry in worker_info:
            addr = entry["address"]
            if addr not in workers_by_address:
                workers_by_address[addr] = []
            workers_by_address[addr].append(entry["type"])
    except Exception as e:
        workers_by_address = {"Error": [str(e)]}

    worker_config = load_worker_config()

    worker_address_map = {}
    for addr, types in workers_by_address.items():
        for t in types:
            if t not in worker_address_map:
                worker_address_map[t.strip().lower()] = addr

    for w in worker_config:
        w['address'] = worker_address_map.get(w['name'].strip().lower(), None)

    logging.info(f"Worker info: {worker_info}")

    return render_template_string(
        TEMPLATE,
        workers=workers_by_address.items(),
        stats=latest_stats or {},
        pending_tasks=latest_pending_tasks or [],
        tab="dashboard",
        all_workers=worker_config
    )


@app.route("/logs")
def logs():
    """
    Retrieve log files from the "/logs" directory and render them using a template.
    This function checks if the "/logs" directory exists and iterates through its
    contents to find files. If specific filenames are provided via the "file" query 
    parameter (obtained from request.args), only those files are processed; otherwise,
    all files in the directory are used. For each valid file, the function reads its
    content and stores it in a dictionary keyed by the filename.
    Returns:
        A rendered template string that includes:
            - "tab": a string indicating the current tab (set to "logs"),
            - "logs": a dictionary mapping each filename to its corresponding content,
            - "selected_file": the list of filenames that were specified in the query parameters.
    Notes:
        - This function assumes that the environment provides access to the `request`
          object (e.g., from Flask) and that `render_template_string` and a TEMPLATE are defined.
        - File system operations are performed using modules like `os`, which should be imported.
    """
    log_dir = "/logs"
    logs = {}
    
    selected_files = request.args.getlist("file")
    if os.path.isdir(log_dir):
        for filename in os.listdir(log_dir):
            path = os.path.join(log_dir, filename)
            if os.path.isfile(path):
                if not selected_files or filename in selected_files:
                    with open(path, "r") as f:
                        logs[filename] = f.read()
    return render_template_string(TEMPLATE, tab="logs", logs=logs, selected_file=selected_files)

@app.route("/containers")
def containers():
    """
    Retrieves information about Docker containers and renders an HTML template with the container status.
    This function performs the following steps:
    1. Loads available worker types by invoking `load_worker_types()`.
    2. Constructs a list of expected Docker Compose service names, which includes fixed services
        (e.g., "nameservice", "dispatcher", "monitoring", "client") as well as dynamically generated
        worker services in the form "worker-<worker_type>".
    3. Establishes a connection to the Docker daemon using the Unix socket at "/var/run/docker.sock".
    4. Retrieves all Docker containers (both running and stopped) and filters them based on the
        Docker Compose service label ("com.docker.compose.service") to match the expected services.
    5. For each expected service:
        - If corresponding containers are found, appends their details (name, image tag or short ID,
          status, container ID, and a boolean flag indicating if it is running) to a list.
        - If no matching container exists, appends a default entry indicating that the service is not running.
    6. Catches and logs any exceptions during Docker access, returning an error entry if needed.
    7. Finally, returns an HTML string rendered with a provided Jinja2 template (`TEMPLATE`), passing
        the container information and setting the active tab to "containers".
    Returns:
         str: An HTML string generated by rendering the `TEMPLATE` with the container data.
    """
    worker_types = load_worker_types()
    logging.info(f"Detected worker types: {worker_types}")
    expected_services = ["nameservice", "dispatcher", "monitoring", "client"] + [f"worker-{name}" for name in worker_types]
    logging.info(f"Expected Compose services: {expected_services}")

    docker_base_url = "unix:///var/run/docker.sock"

    container_data = []
    try:
        client = docker.DockerClient(base_url=docker_base_url)
        containers = client.containers.list(all=True)

        for service in expected_services:
            matched = [c for c in containers if c.labels.get("com.docker.compose.service") == service]
            if matched:
                for c in matched:
                    container_data.append({
                        "name": c.name,
                        "image": c.image.tags[0] if c.image.tags else c.image.short_id,
                        "status": c.status,
                        "id": c.short_id,
                        "running": c.status == "running"
                    })
            else:
                container_data.append({
                    "name": service,
                    "image": "-",
                    "status": "not running",
                    "id": "-",
                    "running": False
                })

    except Exception as e:
        logging.error(f"Error accessing Docker: {e}")
        container_data = [{"error": str(e)}]

    return render_template_string(TEMPLATE, tab="containers", containers=container_data)


if __name__ == "__main__":
    threading.Thread(target=stats_updater, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)
    print("Monitoring service started on port 8080")