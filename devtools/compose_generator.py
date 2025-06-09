import json
import yaml
import os

def generate_compose(workers_file="workers.json", output_file="docker-compose.generated.yml"):
    """
    Generate a docker-compose configuration file based on active worker settings.
    This function reads the worker configuration from a JSON file (workers_file), extracts the names of the active workers,
    and dynamically creates a docker-compose configuration. It defines services including nameservice, dispatcher, monitoring,
    client, and a worker service for each active worker. Each worker service is assigned a unique UDP port starting from 6001.
    The resulting docker-compose configuration includes predefined volumes and network settings, and is written to the specified
    YAML file (output_file).
    Parameters:
        workers_file (str): The path to the JSON file containing worker configurations. Defaults to "workers.json".
        output_file (str): The path where the generated docker-compose YAML file will be saved.
                           Defaults to "docker-compose.generated.yml".
    Raises:
        FileNotFoundError: If the specified workers_file cannot be found.
        json.JSONDecodeError: If the workers_file contains invalid JSON.
        yaml.YAMLError: If an error occurs while dumping the configuration to YAML.
    """
    
    with open(workers_file) as f:
        worker_config = json.load(f)

    active_workers = [w["name"] for w in worker_config.get("workers", []) if w.get("active") is True]
    BASE_PORT = 6001

    services = {
        "nameservice": {
            "build": {"context": ".", "dockerfile": "nameservice/Dockerfile"},
            "volumes": ["logs:/logs"],
            "environment": ["LOG_DIR=/logs"],
            "ports": ["5001:5001/udp"],
            "networks": ["tasknet"]
        },
        "dispatcher": {
            "build": {"context": ".", "dockerfile": "dispatcher/Dockerfile"},
            "ports": ["4000:4000/udp"],
            "volumes": ["logs:/logs"],
            "environment": ["LOG_DIR=/logs"],
            "networks": ["tasknet"]
        },
        "monitoring": {
            "build": {"context": ".", "dockerfile": "monitoring/Dockerfile"},
            "ports": ["8080:8080"],
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
            "volumes": ["logs:/logs"],
            "env_file": [".env"],
            "environment": ["LOG_DIR=/logs"],
            "networks": ["tasknet"],
            "command": "python client.py --dispatcher-ip ${DISPATCHER_IP} ${CLIENT_MODE}"
        }
    }

    for i, name in enumerate(active_workers):
        services[f"worker-{name}"] = {
            "build": {"context": ".", "dockerfile": "worker/Dockerfile"},
            "entrypoint": ["python", "worker.py", name],
            "ports": [f"{BASE_PORT + i}:6000/udp"],
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