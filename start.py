import os
import subprocess
import sys
import platform
import inquirer
from devtools.runner import (
    full_reset, run_compose, delete_compose_file,
    run_selected_containers, build_selected_containers, build_compose
)
from devtools.compose_generator import generate_compose

VENV_DIR = ".venv"
REQUIREMENTS_FILE = "requirements.txt"

ALL_CONTAINERS = [
    "nameservice", "dispatcher", "monitoring", "client",
    "worker-hash", "worker-reverse", "worker-upper",
    "worker-random_fact", "worker-sum", "worker-wait"
]

def clear_screen():
    os.system("cls" if platform.system() == "Windows" else "clear")

def create_virtualenv():
    if not os.path.isdir(VENV_DIR):
        print(f"Erstelle virtuelles Environment in '{VENV_DIR}' ...")
        subprocess.run([sys.executable, "-m", "venv", VENV_DIR], check=True)

def get_venv_python():
    return os.path.join(VENV_DIR, "Scripts" if platform.system() == "Windows" else "bin", "python")

def install_requirements(python_path):
    print("Installiere Abhängigkeiten aus requirements.txt ...")
    subprocess.run([python_path, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run([python_path, "-m", "pip", "install", "-r", REQUIREMENTS_FILE], check=True)

def interactive_menu():
    choices = [
        "Alles bauen",
        "Alles starten",
        "Einzelne Container bauen",
        "Einzelne Container starten",
        "Reset (Logs, Images, Volumes)",
        "Compose neu generieren",
        "Abbrechen"
    ]
    question = [inquirer.List("action", message="Was möchtest du tun?", choices=choices)]
    answer = inquirer.prompt(question)
    return answer["action"] if answer else "Abbrechen"

def select_containers():
    question = [
        inquirer.Checkbox(
            "containers",
            message="Welche Container möchtest du auswählen?",
            choices=ALL_CONTAINERS
        )
    ]
    answer = inquirer.prompt(question)
    return answer["containers"] if answer else []

def ask_client_config():
    dispatcher_ip = input("Gib die Dispatcher-IP-Adresse an (z. B. 127.0.0.1): ").strip()
    clear_screen()
    if dispatcher_ip in ("127.0.0.1", "localhost") or not dispatcher_ip:
        dispatcher_ip = "dispatcher"
    mode_question = [
        inquirer.List(
            "client_mode",
            message="Welchen Modus soll der Client verwenden?",
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
    create_virtualenv()
    python_path = get_venv_python()
    install_requirements(python_path)
    clear_screen()

    while True:
        clear_screen()
        choice = interactive_menu()

        if choice == "Alles bauen":
            clear_screen()
            delete_compose_file()
            ask_client_config()
            generate_compose()
            build_compose()

        elif choice == "Alles starten":
            clear_screen()
            if not os.path.exists("docker-compose.generated.yml"):
                ask_client_config()
                generate_compose()
                build_compose()
            run_compose(detach=False)

        elif choice == "Einzelne Container bauen":
            clear_screen()
            selected = select_containers()
            if selected:
                if "client" in selected:
                    ask_client_config()
                build_selected_containers(selected)

        elif choice == "Einzelne Container starten":
            clear_screen()
            selected = select_containers()
            if selected:
                if "client" in selected:
                    ask_client_config()
                run_selected_containers(selected)

        elif choice == "Reset (Logs, Images, Volumes)":
            clear_screen()
            full_reset()

        elif choice == "Compose neu generieren":
            clear_screen()
            ask_client_config()
            delete_compose_file()
            generate_compose()

        elif choice == "Abbrechen":
            clear_screen()
            print("Beendet.")
            break

if __name__ == "__main__":
    main()