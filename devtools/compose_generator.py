import json
import yaml

def generate_compose(workers_file="workers.json", output_file="docker-compose.generated.yml"):
    """
    Generates a Docker Compose YAML configuration based on worker settings.
    This function reads a JSON file specified by `workers_file` to acquire
    the worker configuration. It filters out only the active workers and assigns
    a unique service for each, mapping them to consecutive ports beginning at 6001.
    Additionally, it defines services for nameservice, dispatcher, monitoring, and client,
    each with their respective build contexts, dependencies, mounts, ports, and network settings.
    The final configuration is then written to the file specified by `output_file`.
    Parameters:
        workers_file (str): Path to the JSON file containing the worker configuration.
                            Default is "workers.json".
        output_file (str): Path where the generated Docker Compose YAML configuration
                           will be written. Default is "docker-compose.generated.yml".
    Returns:
        None
    Side Effects:
        Writes the Docker Compose configuration to the specified output file.
    """
    with open(workers_file) as f:
        worker_config = json.load(f)

    # Only include active workers
    active_workers = [w["name"] for w in worker_config.get("workers", []) if w.get("active") is True]
    BASE_PORT = 6001

    services = {
        "nameservice": {
            "build": {"context": ".", "dockerfile": "nameservice/Dockerfile"},
            "volumes": ["logs:/logs"],
            "environment": ["LOG_DIR=/logs"],
            "ports": ["5001:5001"],
            "networks": ["tasknet"]
        },
        "dispatcher": {
            "build": {"context": ".", "dockerfile": "dispatcher/Dockerfile"},
            "ports": ["4000:4000"],
            "depends_on": ["nameservice"],
            "volumes": ["logs:/logs"],
            "environment": ["LOG_DIR=/logs"],
            "networks": ["tasknet"]
        },
        "monitoring": {
            "build": {"context": ".", "dockerfile": "monitoring/Dockerfile"},
            "ports": ["8080:8080"],
            "depends_on": ["dispatcher", "nameservice"],
            "volumes": [
                "logs:/logs",
                "/var/run/docker.sock:/var/run/docker.sock",
                "./workers.json:/app/workers.json"
            ],
            "environment": ["LOG_DIR=/logs"],
            "networks": ["tasknet"]
        },
        "client": {
            "build": {"context": ".", "dockerfile": "client/Dockerfile"},
            "stdin_open": True,
            "tty": True,
            "depends_on": ["dispatcher", "nameservice"],
            "volumes": ["logs:/logs"],
            "environment": ["LOG_DIR=/logs"],
            "networks": ["tasknet"]
        }
    }

    for i, name in enumerate(active_workers):
        services[f"worker-{name}"] = {
            "build": {"context": ".", "dockerfile": "worker/Dockerfile"},
            "entrypoint": ["python", "worker.py", name],
            "ports": [f"{BASE_PORT + i}:6000"],
            "depends_on": ["dispatcher", "nameservice"],
            "volumes": ["logs:/logs"],
            "environment": ["LOG_DIR=/logs"],
            "networks": ["tasknet"]
        }

    compose_config = {
        "services": services,
        "volumes": {"logs": {}},
        "networks": {"tasknet": {}}
    }

    with open(output_file, "w") as out:
        yaml.dump(compose_config, out, sort_keys=False)

    print(f"Compose-Datei '{output_file}' erfolgreich erstellt.")