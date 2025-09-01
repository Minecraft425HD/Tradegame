import json
import time
from config import game_state, lock, clients, DEFAULT_HOST, logging

def broadcast_game_state():
    with lock:  # Lock während Dump für konsistenten Snapshot
        state_json = json.dumps({"game_state": game_state, "timestamp": time.time()}, ensure_ascii=False)
        data_bytes = state_json.encode('utf-8')
        length_prefix = len(data_bytes).to_bytes(4, byteorder='big')
        clients_to_send = [c for c in clients if c.fileno() != -1]
    if not clients_to_send:
        logging.info("Keine Clients zum Senden des game_state.")
        print("Keine Clients zum Senden des game_state.")
        return
    for client in clients_to_send:
        try:
            client.send(length_prefix + data_bytes)
            logging.info(f"Sende game_state an {client.getpeername()}: stocks={game_state['stocks']}")
            print(f"Sende game_state an {client.getpeername()}: stocks={game_state['stocks']}")
            with lock:
                for pid, p in game_state["players"].items():
                    if client.getpeername()[0] == DEFAULT_HOST:
                        p["bytes_sent"] = p.get("bytes_sent", 0) + len(length_prefix + data_bytes)
        except (ConnectionResetError, BrokenPipeError):
            logging.warning(f"Verbindung zu {client.getpeername()} wurde geschlossen, Client wird entfernt")
            print(f"Verbindung zu {client.getpeername()} wurde geschlossen, Client wird entfernt")
            with lock:
                if client in clients:
                    clients.remove(client)
        except Exception as e:
            logging.error(f"Fehler beim Senden an Client {client.getpeername()}: {e}")
            print(f"Fehler beim Senden an Client {client.getpeername()}: {e}")
            with lock:
                if client in clients:
                    clients.remove(client)
                    logging.info(f"Client {client.getpeername()} entfernt")
                    print(f"Client {client.getpeername()} entfernt")

def receive_full_message(client):
    try:
        length_data = b""
        while len(length_data) < 4:
            chunk = client.recv(4 - len(length_data))
            if not chunk:
                return None
            length_data += chunk
        msg_length = int.from_bytes(length_data, byteorder='big')
        if msg_length > 1024 * 1024:
            logging.error(f"Ungültige Nachrichtenlänge: {msg_length}")
            print(f"Ungültige Nachrichtenlänge: {msg_length}")
            return None
        data = b""
        while len(data) < msg_length:
            chunk = client.recv(min(1024, msg_length - len(data)))
            if not chunk:
                return None
            data += chunk
        decoded_data = data.decode('utf-8')
        logging.info(f"Empfangene Daten: {decoded_data[:100]}...")
        print(f"Empfangene Daten: {decoded_data[:100]}...")
        return decoded_data
    except BlockingIOError:
        return None
    except Exception as e:
        logging.error(f"Fehler beim Empfangen der Nachricht von {client.getpeername() if hasattr(client, 'getpeername') else 'unknown'}: {e}, Typ: {type(e).__name__}")
        print(f"Fehler beim Empfangen der Nachricht von {client.getpeername() if hasattr(client, 'getpeername') else 'unknown'}: {e}, Typ: {type(e).__name__}")
        return None