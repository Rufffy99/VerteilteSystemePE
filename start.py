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
    """
    Clears the terminal screen.
    This function detects the operating system and executes the appropriate command to clear
    the terminal screen. On Windows, it uses the "cls" command; on other operating systems, it uses
    the "clear" command.
    """
    os.system("cls" if platform.system() == "Windows" else "clear")

def create_virtualenv():
    """
    Creates a virtual Python environment if it does not already exist.
    This function checks whether the directory specified by the global variable VENV_DIR exists.
    If the directory is not found, it prints a message indicating that the virtual environment is being created,
    and then uses the system's current Python interpreter to create the environment via the 'venv' module.
    Raises:
        subprocess.CalledProcessError: If the creation of the virtual environment fails.
    """
    if not os.path.isdir(VENV_DIR):
        print(f"Erstelle virtuelles Environment in '{VENV_DIR}' ...")
        subprocess.run([sys.executable, "-m", "venv", VENV_DIR], check=True)

def get_venv_python():
    """
    Return the full path to the Python interpreter in the virtual environment.
    This function constructs the file path to the Python executable based on the operating
    system. It uses the VENV_DIR as the base directory and appends:
        - "Scripts" for Windows platforms.
        - "bin" for non-Windows platforms.
    Returns:
        str: The complete path to the Python executable within the virtual environment.
    """
    return os.path.join(VENV_DIR, "Scripts" if platform.system() == "Windows" else "bin", "python")

def install_requirements(python_path):
    """
    Install dependencies specified in the requirements file.
    This function upgrades the pip tool and subsequently installs all packages listed in the requirements file.
    It uses the given Python executable to invoke pip, ensuring that the installation is managed by the correct Python interpreter.
    Args:
        python_path (str): The full path to the Python executable.
    Raises:
        subprocess.CalledProcessError: If either the pip upgrade or installation command fails.
    """
    print("Installiere Abhängigkeiten aus requirements.txt ...")
    subprocess.run([python_path, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run([python_path, "-m", "pip", "install", "-r", REQUIREMENTS_FILE], check=True)

def interactive_menu():
    """
    Displays an interactive menu with a list of predefined options and returns the user's selected action.
    The menu includes options to:
    - Build everything
    - Start everything
    - Build individual container
    - Start individual container
    - Reset logs, images, and volumes
    - Regenerate the Compose file
    - Cancel the operation
    Returns:
        str: The action chosen by the user. If the user doesn't select any option, "Abbrechen" is returned as the default.
    """
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
    """
    Prompt the user to select one or more containers from a predefined list.
    This function uses an interactive checkbox prompt to let the user choose containers from a list defined by ALL_CONTAINERS. It returns a list of the selected container names. If the prompt is cancelled or no selection is made, an empty list is returned.
    Returns:
        list: A list of the names of the selected containers, or an empty list if no selection was made.
    """
    
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
    """
    Prompts the user for the dispatcher IP address and the client operation mode,
    then writes the corresponding configuration to an environment file.
    Process:
    1. Asks the user to input the dispatcher IP address.
    2. Clears the terminal screen.
    3. If the input is "127.0.0.1", "localhost", or empty, sets the dispatcher IP to a default value ("dispatcher").
    4. Uses an inquirer list prompt to ask the user to select between the "simulate" and "run" client modes.
    5. Defaults to "simulate" if no mode is selected.
    6. Calls the write_env_file function to save the dispatcher IP and client mode configuration.
    """
    
    dispatcher_ip = input("Gib die Dispatcher-IP-Adresse an (z.B. 127.0.0.1): ").strip()
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
    """
    Writes environment configuration values to a .env file.
    This function creates (or overwrites) a file named ".env" in the current working directory and writes
    two lines into it: one for the dispatcher IP and one for the client mode.
    Parameters:
        dispatcher_ip (str): The IP address of the dispatcher.
        client_mode (str): The mode in which the client should operate.
    """
    with open(".env", "w") as f:
        f.write(f"DISPATCHER_IP={dispatcher_ip}\n")
        f.write(f"CLIENT_MODE={client_mode}\n")

def main():
    """
    Main entry point for the application.
    The function performs the following steps:
    1. Setup:
        - Creates a virtual environment.
        - Retrieves the Python interpreter path from the virtual environment.
        - Installs required Python packages.
        - Clears the terminal screen.
    2. User Interaction Loop:
        - Enters an infinite loop displaying an interactive menu with multiple options.
        - Based on the selected choice, it performs one of the following actions:
          a. "Alles bauen":
              - Clears the screen.
              - Deletes the existing Docker Compose file.
              - Prompts for client configuration.
              - Generates a new Docker Compose file.
              - Builds the complete Docker Compose setup.
          b. "Alles starten":
              - Clears the screen.
              - If no Docker Compose file exists, prompts for client configuration, generates and builds the Compose file.
              - Runs the Docker Compose setup (optionally in detached mode).
          c. "Einzelne Container bauen":
              - Clears the screen.
              - Allows selection of individual containers.
              - For the 'client' container, prompts for client configuration.
              - Builds the selected containers.
          d. "Einzelne Container starten":
              - Clears the screen.
              - Allows selection of individual containers.
              - For the 'client' container:
                 - Prompts for client configuration.
                 - If it is the only selected container, runs the client interactively.
              - Starts the selected containers.
          e. "Reset (Logs, Images, Volumes)":
              - Clears the screen.
              - Performs a full reset by clearing logs, images, and volumes.
          f. "Compose neu generieren":
              - Clears the screen.
              - Prompts for client configuration.
              - Deletes the current Docker Compose file.
              - Generates a new Docker Compose file.
          g. "Abbrechen":
              - Clears the screen.
              - Exits the application loop, terminating the program.
    """
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
                    if len(selected) == 1:
                        from devtools.runner import run_client_interactive
                        run_client_interactive()
                        return
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