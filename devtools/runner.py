import subprocess
import sys
from devtools.compose_generator import generate_compose

def run_compose(compose_file="docker-compose.generated.yml"):
    try:
        subprocess.run(["docker-compose", "-f", compose_file, "up", "--build"], check=True)
    except subprocess.CalledProcessError:
        print("❌ Fehler beim Ausführen von docker-compose.")
        sys.exit(1)

def main():
    print("🔧 Generiere docker-compose Datei ...")
    generate_compose()
    print("🚀 Starte docker-compose ...")
    run_compose()


if __name__ == "__main__":
    main()