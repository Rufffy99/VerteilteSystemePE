from flask import Flask, render_template_string
import socket
import time
from shared.protocol import encode_message, decode_message, LOOKUP_WORKER
import docker

app = Flask(__name__)

NAMESERVICE_ADDRESS = ("nameservice", 5000)
DISPATCHER_ADDRESS = ("dispatcher", 4000)
RECEIVE_BUFFER_SIZE = 4096

def query_nameservice(worker_type):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        msg = encode_message(LOOKUP_WORKER, {"type": worker_type})
        sock.sendto(msg, NAMESERVICE_ADDRESS)
        data, _ = sock.recvfrom(RECEIVE_BUFFER_SIZE)
        _, content = decode_message(data)
        return content.get("address", None)
    except Exception as e:
        return f"Error: {e}"

def query_dispatcher_tasks():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        msg = encode_message("GET_ALL_TASKS", {})
        sock.sendto(msg, DISPATCHER_ADDRESS)
        data, _ = sock.recvfrom(RECEIVE_BUFFER_SIZE)
        _, content = decode_message(data)
        return content.get("tasks", [])
    except Exception as e:
        return f"Error: {e}"

def calculate_stats(tasks):
    total_time = 0
    count_done = 0
    pending = 0

    for task in tasks:
        if task["status"] == "done":
            total_time += task["timestamp_completed"] - task["timestamp_created"]
            count_done += 1
        elif task["status"] == "pending":
            pending += 1

    avg_time = total_time / count_done if count_done else 0
    return {
        "open_tasks": pending,
        "avg_completion_time": round(avg_time, 2),
        "total_tasks": len(tasks),
        "completed_tasks": count_done
    }

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
    </style>
</head>
<body>
    <div class="tab">
        <a href="/" class="{{ 'active' if tab == 'dashboard' else '' }}">📊 Dashboard</a>
        <a href="/logs" class="{{ 'active' if tab == 'logs' else '' }}">📄 Logs</a>
        <a href="/containers" class="{{ 'active' if tab == 'containers' else '' }}">🐳 Docker</a>
    </div>
    {% if tab == 'dashboard' %}
        <h1>📡 Monitoring Dashboard</h1>
        <h2>🔌 Active Workers</h2>
        <ul>
        {% for addr, types in workers %}
            <li>{{ addr }} → {{ types|join(", ") }}</li>
        {% endfor %}
        </ul>

        <h2>📋 Task Stats</h2>
        <ul>
        {% for key, value in stats.items() %}
            <li>{{ key }}: {{ value }}</li>
        {% endfor %}
        </ul>
    {% elif tab == 'logs' %}
        <h1>📄 Log Dateien</h1>
        {% for log_file, content in logs.items() %}
            <h3>{{ log_file }}</h3>
            <pre>{{ content }}</pre>
        {% endfor %}
    {% elif tab == 'containers' %}
        <h1>🐳 Laufende Docker-Container</h1>
        <ul>
        {% for container in containers %}
            <li>
                {% if container.error %}
                    Fehler: {{ container.error }}
                {% else %}
                    {{ container.name }} ({{ container.image }}) – {{ container.status }}
                {% endif %}
            </li>
        {% endfor %}
        </ul>
    {% endif %}
</body>
</html>
"""

@app.route("/")
def dashboard():
    # Fetch all registered workers from nameservice
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        msg = encode_message("LIST_WORKERS", {})
        sock.sendto(msg, NAMESERVICE_ADDRESS)
        data, _ = sock.recvfrom(RECEIVE_BUFFER_SIZE)
        _, content = decode_message(data)
        worker_info = content.get("workers", [])  # Expect list of {"type": str, "address": str}
        workers_by_address = {}
        for entry in worker_info:
            addr = entry["address"]
            if addr not in workers_by_address:
                workers_by_address[addr] = []
            workers_by_address[addr].append(entry["type"])
    except Exception as e:
        workers_by_address = {"Error": [str(e)]}

    result = query_dispatcher_tasks()
    if isinstance(result, str):  # an error string
        stats = {
            "open_tasks": "Unavailable",
            "avg_completion_time": "Unavailable",
            "total_tasks": "Unavailable",
            "completed_tasks": "Unavailable"
        }
    else:
        stats = calculate_stats(result)

    return render_template_string(TEMPLATE, workers=workers_by_address.items(), stats=stats, tab="dashboard")


import os

@app.route("/logs")
def logs():
    log_dir = "/logs"
    logs = {}
    if os.path.isdir(log_dir):
        for filename in os.listdir(log_dir):
            path = os.path.join(log_dir, filename)
            if os.path.isfile(path):
                with open(path, "r") as f:
                    logs[filename] = f.read()
    return render_template_string(TEMPLATE, tab="logs", logs=logs)

@app.route("/containers")
def containers():
    try:
        client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        containers = client.containers.list()
        container_data = [
            {
                "name": c.name,
                "image": c.image.tags[0] if c.image.tags else c.image.short_id,
                "status": c.status,
                "id": c.short_id
            }
            for c in containers
        ]
    except Exception as e:
        container_data = [{"error": str(e)}]

    return render_template_string(TEMPLATE, tab="containers", containers=container_data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)