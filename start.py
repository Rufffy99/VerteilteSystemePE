import os
import subprocess
import sys
import platform

VENV_DIR = ".venv"
REQUIREMENTS_FILE = "requirements.txt"

def create_virtualenv():
    if not os.path.isdir(VENV_DIR):
        print(f"🐍 Erstelle virtuelles Environment in '{VENV_DIR}' ...")
        subprocess.run([sys.executable, "-m", "venv", VENV_DIR], check=True)

def get_venv_python():
    if platform.system() == "Windows":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    else:
        return os.path.join(VENV_DIR, "bin", "python")

def install_requirements(python_path):
    print("📦 Installiere Abhängigkeiten aus requirements.txt ...")
    subprocess.run([python_path, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run([python_path, "-m", "pip", "install", "-r", REQUIREMENTS_FILE], check=True)

def run_runner(python_path):
    subprocess.run([python_path, "-m", "devtools.runner"], check=True)

def main():
    create_virtualenv()
    python_path = get_venv_python()
    install_requirements(python_path)
    run_runner(python_path)

if __name__ == "__main__":
    main()