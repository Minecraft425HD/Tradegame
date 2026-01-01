import json
import time
from config import game_state, lock, clients, logging
from constants import MAX_MESSAGE_SIZE

def broadcast_game_state():
    """Broadcasts the current game state to all connected clients."""
    with lock:
        state_data = {
            "game_state": game_state,
            "timestamp": time.time(),
            "state_version": game_state.get("state_version", 0)
        }
        state_json = json.dumps(state_data, ensure_ascii=False)
        data_bytes = state_json.encode('utf-8')
        length_prefix = len(data_bytes).to_bytes(4, byteorder='big')
        clients_to_send = [c for c in clients if c.fileno() != -1]

    if not clients_to_send:
        logging.debug("Keine Clients zum Senden des game_state.")
        return

    bytes_per_message = len(length_prefix + data_bytes)

    for client in clients_to_send:
        try:
            client.send(length_prefix + data_bytes)

            # Track bytes sent per player using client socket mapping
            try:
                client_addr = client.getpeername()
                logging.debug(f"Sende game_state an {client_addr}")
            except Exception:
                pass

            # Update bytes_sent for all players (broadcast goes to everyone)
            with lock:
                for pid, p in game_state["players"].items():
                    p["bytes_sent"] = p.get("bytes_sent", 0) + bytes_per_message

        except (ConnectionResetError, BrokenPipeError) as e:
            try:
                addr = client.getpeername()
            except Exception:
                addr = "unknown"
            logging.warning(f"Verbindung zu {addr} wurde geschlossen: {e}")
            print(f"Verbindung zu {addr} wurde geschlossen")
            with lock:
                if client in clients:
                    clients.remove(client)
        except OSError as e:
            # Socket already closed
            logging.debug(f"Socket bereits geschlossen: {e}")
            with lock:
                if client in clients:
                    clients.remove(client)
        except Exception as e:
            try:
                addr = client.getpeername()
            except Exception:
                addr = "unknown"
            logging.error(f"Fehler beim Senden an Client {addr}: {e}")
            print(f"Fehler beim Senden an Client {addr}: {e}")
            with lock:
                if client in clients:
                    clients.remove(client)

def receive_full_message(client):
    """
    Receives a complete message from the client using length-prefix protocol.
    Returns the decoded message string or None if no data/error.
    """
    try:
        # Read 4-byte length prefix
        length_data = b""
        while len(length_data) < 4:
            chunk = client.recv(4 - len(length_data))
            if not chunk:
                return None
            length_data += chunk

        msg_length = int.from_bytes(length_data, byteorder='big')

        # Validate message length
        if msg_length <= 0:
            logging.warning(f"Ungültige Nachrichtenlänge: {msg_length}")
            return None

        if msg_length > MAX_MESSAGE_SIZE:
            logging.error(f"Nachricht zu groß: {msg_length} bytes (max: {MAX_MESSAGE_SIZE})")
            print(f"Nachricht zu groß: {msg_length} bytes")
            return None

        # Read message data
        data = b""
        while len(data) < msg_length:
            remaining = msg_length - len(data)
            chunk_size = min(4096, remaining)  # Increased buffer size
            chunk = client.recv(chunk_size)
            if not chunk:
                return None
            data += chunk

        decoded_data = data.decode('utf-8')
        logging.debug(f"Empfangene Daten: {decoded_data[:100]}...")
        return decoded_data

    except BlockingIOError:
        return None
    except ConnectionResetError:
        logging.debug("Verbindung vom Client zurückgesetzt")
        return None
    except OSError as e:
        # Socket operation on closed socket
        logging.debug(f"Socket-Fehler: {e}")
        return None
    except Exception as e:
        try:
            addr = client.getpeername() if hasattr(client, 'getpeername') else 'unknown'
        except Exception:
            addr = 'unknown'
        logging.error(f"Fehler beim Empfangen von {addr}: {e}, Typ: {type(e).__name__}")
        return None

def send_message(client, data_dict):
    """
    Sends a message to a specific client.
    Returns True on success, False on failure.
    """
    try:
        data_str = json.dumps(data_dict, ensure_ascii=False)
        data_bytes = data_str.encode('utf-8')
        length_prefix = len(data_bytes).to_bytes(4, byteorder='big')
        client.send(length_prefix + data_bytes)
        return True
    except Exception as e:
        logging.error(f"Fehler beim Senden der Nachricht: {e}")
        return False
