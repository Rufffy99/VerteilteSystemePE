from flask import Flask, render_template_string, request, Response
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
    Load worker configuration from a JSON file.
    This function attempts to read and load worker configurations from a JSON file defined by the global variable WORKERS_JSON_PATH.
    It expects the JSON to contain a "workers" key whose value is a list of worker configurations.
    If the file is read and parsed successfully, the function returns the list associated with the "workers" key.
    In case of any errors during file reading or JSON parsing, it logs an error message and returns an empty list.
    Returns:
        list: A list of worker configurations if successfully loaded, otherwise an empty list.
    """
    try:
        with open(WORKERS_JSON_PATH, "r") as f:
            data = json.load(f)
            return data.get("workers", [])
    except Exception as e:
        logging.error(f"Could not load worker config: {e}")
        return []

def load_worker_types():
    workers = load_worker_config()
    return [w["name"] for w in workers if w.get("active") is True]

app = Flask(__name__)

NAMESERVICE_ADDRESS = ("nameservice", 5001)
DISPATCHER_ADDRESS = ("dispatcher", 4000)
RECEIVE_BUFFER_SIZE = 4096

latest_stats = {}
latest_pending_tasks = []

TEMPLATE = """
<html>
<head>
    <title>Monitoring</title>
    <style>
        body { font-family: sans-serif; }
        .tab { margin-bottom: 1em; }
        .tab a {
            margin-right: 10px;
            text-decoration: none;
            font-weight: bold;
        }
        .tab a.active { color: green; }
        pre { background: #eee; padding: 1em; overflow: auto; }
        .active-btn {
            background-color: #cce5ff;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            max-width: 800px;
        }
        th, td {
            border: 1px solid #999;
            padding: 0.5em 1em;
            text-align: left;
        }
        th {
            background-color: #ddd;
        }
        .active-btn {
            background-color: #cce5ff;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            max-width: 800px;
        }
        th, td {
            border: 1px solid #999;
            padding: 0.5em 1em;
            text-align: left;
        }
        th {
            background-color: #ddd;
        }
    </style>
    <script>
        const evtSource = new EventSource("/events");
        evtSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            const stats = data.stats;
            const pending = data.pending;

            // Stats HTML
            let statsHtml = "<ul>";
            statsHtml += `<li>Total Tasks: ${stats.total_tasks}</li>`;
            statsHtml += `<li>Completed Tasks: ${stats.completed_tasks}</li>`;
            statsHtml += `<li>Open Tasks: ${stats.open_tasks}</li>`;
            statsHtml += `<li>Average Completion Time: ${stats.avg_completion_time} s</li>`;
            statsHtml += `<li>Average Completion by Worker:<ul>`;
            for (const [worker, time] of Object.entries(stats.avg_completion_by_worker || {})) {
                statsHtml += `<li>${worker}: ${time} s</li>`;
            }
            statsHtml += "</ul></li></ul>";
            document.getElementById("live-stats").innerHTML = statsHtml;

            // Queue HTML
            let queueHtml = "<ul>";
            for (const task of pending) {
                queueHtml += `<li>ID ${task.id} | Type: ${task.type} | Payload: ${task.payload}</li>`;
            }
            queueHtml += "</ul>";
            document.getElementById("live-queue").innerHTML = queueHtml;
        };
    </script>
</head>
<body>
    <div class="tab">
        <a href="/" class="{{ 'active' if tab == 'dashboard' else '' }}">📊 Dashboard</a>
        <a href="/logs" class="{{ 'active' if tab == 'logs' else '' }}">📄 Logs</a>
        <a href="/containers" class="{{ 'active' if tab == 'containers' else '' }}">🐳 Docker</a>
    </div>
    {% if tab == 'dashboard' %}
        <h1>📡 Monitoring Dashboard</h1>
        <h2>🔌 Workers Übersicht</h2>
        <table>
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Status</th>
                    <th>Adresse</th>
                </tr>
            </thead>
            <tbody>
            {% for worker in all_workers %}
                <tr>
                    <td>{{ worker.name }}</td>
                    <td style="font-weight: bold; color: {{ 'green' if worker.active else 'red' }}">
                        {{ 'Aktiv' if worker.active else 'Inaktiv' }}
                    </td>
                    <td>
                        {% if worker.address %}
                            {{ worker.address }}
                        {% elif worker.active %}
                            ❌ Nicht registriert
                        {% else %}
                            -
                        {% endif %}
                    </td>
                </tr>
            {% endfor %}
            </tbody>
        </table>

        <h2>📋 Task Stats (Live)</h2>
        <div id="live-stats">
            <ul><li>Loading stats...</li></ul>
        </div>

        <h2>🕓 Pending Task Queue (Live)</h2>
        <div id="live-queue">
            <ul><li>Loading pending tasks...</li></ul>
        </div>

    {% elif tab == 'logs' %}
        <h1>📄 Log Dateien</h1>
        
        {% for log_file, content in logs.items() %}
            <h3>{{ log_file }}</h3>
            <pre>{{ content }}</pre>
        {% endfor %}
    {% elif tab == 'containers' %}
    <h1>🐳 Laufende Docker-Container</h1>
    <table>
        <thead>
            <tr>
                <th>Container</th>
                <th>Image</th>
                <th>Status</th>
                <th>Running</th>
            </tr>
        </thead>
        <tbody>
        {% for container in containers %}
            {% if container.error %}
                <tr><td colspan="4">Fehler: {{ container.error }}</td></tr>
            {% else %}
                <tr>
                    <td>{{ container.name }}</td>
                    <td>{{ container.image }}</td>
                    <td>{{ container.status }}</td>
                    <td style="font-size: 1.2em; text-align: center;">{{ "✅" if container.running else "❌" }}</td>
                </tr>
            {% endif %}
        {% endfor %}
        </tbody>
    </table>
{% endif %}
</body>
</html>
"""

def query_dispatcher_stats():
    """
    Sends a UDP request to the dispatcher to retrieve statistics and a list of pending items.
    This function creates a UDP socket, sets a timeout, and encodes a "GET_STATS" request. It then sends
    this message to the dispatcher defined by DISPATCHER_ADDRESS. The function waits for a reply and
    attempts to decode it. If the received message is of type "RESPONSE" and its content is a dictionary,
    it extracts and returns the "pending" list and "stats" dictionary from the content. In case of any error,
    a timeout, or if the message format does not match the expected structure, it returns an empty list and dictionary.
    Returns:
        tuple: A tuple where the first element is a list of pending items (or an empty list) and the second element
               is a dictionary containing statistics (or an empty dictionary).
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
    Continuously updates global state with dispatcher statistics.
    In an infinite loop, this function queries dispatcher statistics using the
    query_dispatcher_stats() function. If valid statistics are returned, it updates
    the global variables 'latest_stats' and 'latest_pending_tasks' accordingly.
    The loop pauses for one second between successive queries to throttle the
    update frequency.
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
    Provides a Server-Sent Events (SSE) stream for real-time updates.
    This function constructs an inner generator function, event_stream, which continuously monitors
    the global variables 'latest_stats' and 'latest_pending_tasks'. It serializes these values into JSON
    and, if the new state differs from the previous one, yields a properly formatted SSE message. The
    function then returns a Flask Response object configured with the "text/event-stream" mimetype to
    enable streaming of events to connected clients.
    Returns:
        Response: A Flask Response object streaming real-time JSON updates following the SSE protocol.
    Note:
        The function assumes that 'latest_stats' and 'latest_pending_tasks' are defined in the outer scope.
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
                worker_address_map[t] = addr

    for w in worker_config:
        w['address'] = worker_address_map.get(w['name'], None)

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