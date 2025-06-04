import socket
import time
from shared.protocol import encode_message, decode_message, POST_TASK, GET_RESULT

DISPATCHER_ADDRESS = ("dispatcher", 4000)
RECEIVE_BUFFER_SIZE = 4096

# Aufgaben, die wir testen wollen
tasks = [
    {"type": "reverse", "payload": "hallo"},
    {"type": "upper", "payload": "welt"},
    {"type": "sum", "payload": [1, 2, 3]},
    {"type": "hash", "payload": "geheim"},
    {"type": "wait", "payload": 3}
]

def send_task(task):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        msg = encode_message(POST_TASK, task)
        sock.sendto(msg, DISPATCHER_ADDRESS)
        sock.settimeout(2)
        try:
            data, _ = sock.recvfrom(RECEIVE_BUFFER_SIZE)
            _, response = decode_message(data)
            print(f"[Gesendet] {task} → Antwort: {response}")
            return response.get("message").split("=")[-1].strip()  # ID extrahieren
        except Exception as e:
            print(f"Fehler beim Senden der Aufgabe: {e}")
            return None

def get_result(task_id):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        msg = encode_message(GET_RESULT, {"task_id": int(task_id)})
        sock.sendto(msg, DISPATCHER_ADDRESS)
        sock.settimeout(2)
        try:
            data, _ = sock.recvfrom(RECEIVE_BUFFER_SIZE)
            _, response = decode_message(data)
            return response
        except Exception as e:
            return {"error": str(e)}

def main():
    task_ids = []

    # Schritt 1: Aufgaben senden
    for task in tasks:
        task_id = send_task(task)
        if task_id:
            task_ids.append(task_id)

    # Schritt 2: Kurz warten, damit Tasks bearbeitet werden
    print("\nWarte auf Ergebnisse...")
    time.sleep(5)

    # Schritt 3: Ergebnisse abrufen
    for task_id in task_ids:
        result = get_result(task_id)
        print(f"[Ergebnis] Task ID {task_id}: {result}")

if __name__ == "__main__":
    main()