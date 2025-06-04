import subprocess, sys, os, shutil
from devtools.compose_generator import generate_compose

COMPOSE_FILE = "docker-compose.generated.yml"

def delete_compose_file():
    if os.path.exists(COMPOSE_FILE):
        os.remove(COMPOSE_FILE)

def full_reset():
    print("Vollständiger Reset ...")
    subprocess.run(["docker-compose", "-f", COMPOSE_FILE, "down", "-v"], check=False)
    delete_compose_file()
    if os.path.exists("logs"):
        shutil.rmtree("logs", ignore_errors=True)
        print("Logs gelöscht")
    subprocess.run(["docker", "image", "prune", "-f"], check=False)

def run_compose(detach=False, rebuild=False, no_cache=False):
    cmd = ["docker-compose", "-f", COMPOSE_FILE]
    if rebuild:
        build_cmd = cmd + ["build"]
        if no_cache:
            build_cmd.append("--no-cache")
        subprocess.run(build_cmd, check=True)
    up_cmd = cmd + ["up"]
    if detach:
        up_cmd.append("-d")
    subprocess.run(up_cmd, check=True)

def main():
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
        run_compose(detach="--detach" in flags or "-d" in flags, rebuild=True, no_cache="--no-cache" in flags)
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