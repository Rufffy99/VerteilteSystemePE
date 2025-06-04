import os
import subprocess
import sys
import platform
import argparse

VENV_DIR = ".venv"
REQUIREMENTS_FILE = "requirements.txt"

def create_virtualenv():
    if not os.path.isdir(VENV_DIR):
        print(f"Erstelle virtuelles Environment in '{VENV_DIR}' ...")
        subprocess.run([sys.executable, "-m", "venv", VENV_DIR], check=True)

def get_venv_python():
    return os.path.join(VENV_DIR, "Scripts" if platform.system() == "Windows" else "bin", "python")

def install_requirements(python_path):
    print("Installiere Abhängigkeiten aus requirements.txt ...")
    
    subprocess.run([
        python_path, "-m", "pip", "install", "--upgrade", "pip",
        "--trusted-host", "pypi.org",
        "--trusted-host", "files.pythonhosted.org",
        "--disable-pip-version-check",
        "--no-cache-dir"
    ], check=True)

    subprocess.run([
        python_path, "-m", "pip", "install", "-r", REQUIREMENTS_FILE,
        "--trusted-host", "pypi.org",
        "--trusted-host", "files.pythonhosted.org",
        "--disable-pip-version-check",
        "--no-cache-dir"
    ], check=True)


def main():
    if "--man" in sys.argv:
        with open("start.man.txt", "r") as f:
            print(f.read())
        sys.exit(0)

    parser = argparse.ArgumentParser(description="Steuere den Entwicklungsstart")
    subparsers = parser.add_subparsers(dest="command")

    # Subcommand: build
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--reset", action="store_true", help="Logs, Volumes und Images löschen")
    build_parser.add_argument("--no-cache", action="store_true")
    build_parser.add_argument("--detach", "-d", action="store_true")

    # Subcommand: run
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--detach", "-d", action="store_true")

    # Subcommand: regen
    subparsers.add_parser("regen-compose")

    # Subcommand: reset
    subparsers.add_parser("reset")

    args = parser.parse_args()

    create_virtualenv()
    python_path = get_venv_python()
    install_requirements(python_path)

    subprocess.run([python_path, "-m", "devtools.runner", args.command] + sys.argv[2:], check=True)

if __name__ == "__main__":
    main()