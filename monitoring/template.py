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