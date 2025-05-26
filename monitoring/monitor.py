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
            {% endfor %}
            </tbody>
        </table>
    {% endif %}
</body>
</html>
"""

def query_dispatcher_stats():
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
    global latest_stats, latest_pending_tasks
    while True:
        pending, stats = query_dispatcher_stats()
        if stats:
            latest_stats = stats
            latest_pending_tasks = pending
        time.sleep(1)

@app.route("/events")
def sse_stream():
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
    worker_types = load_worker_types()
    logging.info(f"Detected worker types: {worker_types}")
    expected_containers = [
        "programmentwurf-nameservice-1",
        "programmentwurf-dispatcher-1",
        "programmentwurf-monitoring-1",
        "programmentwurf-client-1",
    ] + [f"programmentwurf-worker-{name}-1" for name in worker_types]
    logging.info(f"Expected containers: {expected_containers}")
    try:
        client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        running_containers = client.containers.list()
        running_names = {c.name: c for c in running_containers}
        container_data = []
        for name in expected_containers:
            if name in running_names:
                c = running_names[name]
                container_data.append({
                    "name": c.name,
                    "image": c.image.tags[0] if c.image.tags else c.image.short_id,
                    "status": c.status,
                    "id": c.short_id,
                    "running": True
                })
            else:
                container_data.append({
                    "name": name,
                    "image": "-",
                    "status": "not running",
                    "id": "-",
                    "running": False
                })
    except Exception as e:
        container_data = [{"error": str(e)}]

    return render_template_string(TEMPLATE, tab="containers", containers=container_data)


if __name__ == "__main__":
    threading.Thread(target=stats_updater, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)