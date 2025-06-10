import os
import sys
import platform
import json
import inquirer
from devtools.runner import (
    full_reset, run_compose, delete_compose_file,
    run_selected_containers, build_selected_containers, build_compose
)
from devtools.compose_generator import generate_compose

STATIC_CONTAINERS = ["nameservice", "dispatcher", "monitoring", "client"]


def get_active_worker_containers():
    workers_file = "workers.json"
    if not os.path.exists(workers_file):
        return []
    try:
        with open(workers_file, "r") as f:
            data = json.load(f)
            return [f"worker-{w['name']}" for w in data.get("workers", []) if w.get("active")]
    except Exception:
        return []

def get_all_containers():
    return STATIC_CONTAINERS + get_active_worker_containers()

def clear_screen():
    os.system("cls" if platform.system() == "Windows" else "clear")

def interactive_menu():
    choices = [
        "Build everything",
        "Start everything",
        "Build selected containers",
        "Start selected containers",
        "Reset (Logs, Images, Volumes)",
        "Regenerate Compose file",
        "Cancel"
    ]
    question = [inquirer.List("action", message="What would you like to do?", choices=choices)]
    answer = inquirer.prompt(question)
    return answer["action"] if answer else "Cancel"

def select_containers():
    containers = get_all_containers()
    question = [
        inquirer.Checkbox(
            "containers",
            message="Select containers to operate on (use SPACE to select, ENTER to confirm):",
            choices=containers
        )
    ]
    answer = inquirer.prompt(question)
    return answer["containers"] if answer else []

def ask_client_config():
    dispatcher_ip = input("Enter the dispatcher IP address (e.g., 127.0.0.1): ").strip()
    clear_screen()
    if dispatcher_ip in ("127.0.0.1", "localhost") or not dispatcher_ip:
        dispatcher_ip = "dispatcher"
    mode_question = [
        inquirer.List(
            "client_mode",
            message="Which mode should the client use?",
            choices=["simulate", "run"]
        )
    ]
    mode_answer = inquirer.prompt(mode_question)
    client_mode = mode_answer["client_mode"] if mode_answer else "simulate"
    write_env_file(dispatcher_ip, client_mode)

def write_env_file(dispatcher_ip, client_mode):
    with open(".env", "w") as f:
        f.write(f"DISPATCHER_IP={dispatcher_ip}\n")
        f.write(f"CLIENT_MODE={client_mode}\n")

def main():
    clear_screen()

    while True:
        clear_screen()
        choice = interactive_menu()

        if choice == "Build everything":
            clear_screen()
            delete_compose_file()
            ask_client_config()
            generate_compose()
            build_compose()

        elif choice == "Start everything":
            clear_screen()
            if not os.path.exists("docker-compose.generated.yml"):
                ask_client_config()
                generate_compose()
                build_compose()
            run_compose(detach=False)

        elif choice == "Build selected containers":
            clear_screen()
            selected = select_containers()
            if selected:
                if "client" in selected:
                    ask_client_config()
                build_selected_containers(selected)

        elif choice == "Start selected containers":
            clear_screen()
            selected = select_containers()
            if selected:
                if "client" in selected:
                    ask_client_config()
                    if len(selected) == 1:
                        from devtools.runner import run_client_interactive
                        run_client_interactive()
                        return
                run_selected_containers(selected)

        elif choice == "Reset (Logs, Images, Volumes)":
            clear_screen()
            full_reset()

        elif choice == "Regenerate Compose file":
            clear_screen()
            ask_client_config()
            delete_compose_file()
            generate_compose()

        elif choice == "Cancel":
            clear_screen()
            print("Exited.")
            break

if __name__ == "__main__":
    main()