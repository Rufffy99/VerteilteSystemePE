import subprocess, sys, os, shutil
from devtools.compose_generator import generate_compose

COMPOSE_FILE = "docker-compose.generated.yml"

def delete_compose_file():
    """
    Deletes the compose file specified by the global variable COMPOSE_FILE if it exists.
    This function checks whether the file indicated by COMPOSE_FILE exists in the filesystem
    and removes it if found.
    Raises:
        OSError: If the file exists but cannot be removed due to an OS-related error.
    """
    
    if os.path.exists(COMPOSE_FILE):
        os.remove(COMPOSE_FILE)

def full_reset():
    """
    Performs a full reset of the application's runtime environment.
    This function carries out the following actions:
    1. Prints a message indicating that a full reset is in progress.
    2. Stops and removes Docker containers and their associated volumes using docker-compose.
    3. Deletes the generated Docker Compose file by calling the delete_compose_file function.
    4. Removes the 'logs' directory (if it exists), ensuring that all log files are deleted.
    5. Executes a Docker image prune to clean up unused Docker images.
    Note:
    - The function does not return any value.
    - subprocess.run is invoked with check=False, meaning that failures in these subprocess calls
        will not raise an exception.
    """
    
    print("Full reset ...")
    subprocess.run(["docker-compose", "-f", COMPOSE_FILE, "down", "-v"], check=False)
    delete_compose_file()
    if os.path.exists("logs"):
        shutil.rmtree("logs", ignore_errors=True)
        print("Logs gelöscht")
    subprocess.run(["docker", "image", "prune", "-f"], check=False)

def run_compose(detach=False):
    """
    Runs Docker Compose to start services defined by the compose configuration file.
    Args:
        detach (bool, optional): If True, runs services in detached mode using the '-d' flag.
            Defaults to False.
    Raises:
        subprocess.CalledProcessError: If the docker-compose command exits with a non-zero status.
    """
    
    cmd = ["docker-compose", "-f", COMPOSE_FILE, "up"]
    if detach:
        cmd.append("-d")
    subprocess.run(cmd, check=True)

def build_compose():
    """
    Builds Docker images using docker-compose.
    This function constructs a command to build images defined in the docker-compose file (specified
    by the COMPOSE_FILE variable) by executing "docker-compose -f <COMPOSE_FILE> build". If the build process
    fails (i.e., if docker-compose returns a non-zero exit status), a subprocess.CalledProcessError is raised.
    Raises:
        subprocess.CalledProcessError: If the docker-compose build command fails.
    """
    
    cmd = ["docker-compose", "-f", COMPOSE_FILE, "build"]
    subprocess.run(cmd, check=True)

def run_selected_containers(containers):
    """
    Run selected containers using docker-compose.
    This function checks if the docker-compose file exists and, if it does not, generates it.
    It then constructs the docker-compose command with the specified containers and runs the command as a subprocess.
    Args:
        containers (list): A list of container names to bring up.
    Raises:
        subprocess.CalledProcessError: If the docker-compose command fails.
    """
    
    if not os.path.exists(COMPOSE_FILE):
        generate_compose()
    cmd = ["docker-compose", "-f", COMPOSE_FILE, "up"] + containers
    subprocess.run(cmd, check=True)

def build_selected_containers(containers):
    """
    Build selected Docker containers using docker-compose.
    This function checks if the Docker Compose file specified by COMPOSE_FILE exists.
    If it does not exist, it calls generate_compose() to create it.
    Then, it constructs and executes a docker-compose build command with the provided container names.
    The subprocess.run() call is executed with check=True, so a non-zero exit status will raise a CalledProcessError.
    Parameters:
        containers (list): A list of container names (as strings) to be built.
    Raises:
        subprocess.CalledProcessError: If the docker-compose build command fails.
    """
    
    if not os.path.exists(COMPOSE_FILE):
        generate_compose()
    cmd = ["docker-compose", "-f", COMPOSE_FILE, "build"] + containers
    subprocess.run(cmd, check=True)
    
def run_client_interactive():
    """
    Executes an interactive Docker client container using docker-compose.
    This function constructs and runs a docker-compose command to start the 'client' service interactively.
    It ensures that the container is removed after execution and that the service ports are exposed.
    Raises:
        subprocess.CalledProcessError: If the docker-compose command returns a non-zero exit code.
    """
    
    cmd = ["docker-compose", "-f", COMPOSE_FILE, "run", "--rm", "--service-ports", "client"]
    subprocess.run(cmd, check=True)

def main():
    """
    Entry point for the command-line interface that manages various system operations.
    This function parses command-line arguments to determine the action to be performed:
        - "reset": Calls full_reset() to perform a complete reset.
        - "regen-compose": Deletes the existing compose file and regenerates it.
        - "build": Optionally performs a full reset if the '--reset' flag is present,
                   then deletes the current compose file, regenerates it, and builds the compose configuration.
        - "run": Checks for the existence of the compose file, generates it if missing, and runs the compose configuration.
                 A detach mode is enabled if '--detach' or '-d' flag is provided.
    If no command is provided or an unknown command is specified, the function prints an error message and exits with a status code of 1.
    """
    
    args = sys.argv[1:]
    if not args:
        print("Kein Befehl angegeben (z. B. build, run, regen-compose)")
        sys.exit(1)

    cmd = args[0]
    flags = args[1:]

    if cmd == "reset":
        full_reset()
        return

    if cmd == "regen-compose":
        delete_compose_file()
        generate_compose()
        return

    if cmd == "build":
        if "--reset" in flags:
            full_reset()
        delete_compose_file()
        generate_compose()
        build_compose()
        return

    if cmd == "run":
        if not os.path.isfile(COMPOSE_FILE):
            generate_compose()
        run_compose(detach="--detach" in flags or "-d" in flags)
        return

    print(f"Unbekannter Befehl: {cmd}")
    sys.exit(1)

if __name__ == "__main__":
    main()