import threading
import time
import socket
import json
import re
import html
from config import server_running, lock, clients, game_state, initial_variables, client_heartbeats, logging, increment_state_version, save_game_state
from constants import (
    DEFAULT_HOST, PORT, SOCKET_TIMEOUT, BROADCAST_INTERVAL,
    NETWORK_CHECK_INTERVAL, MAX_CHAT_MESSAGE_LENGTH, MAX_CHAT_HISTORY,
    HEARTBEAT_INTERVAL, HEARTBEAT_TIMEOUT, NORMAL_STOCKS, CRYPTO_STOCKS
)
from game_logic import draw_card_multiplayer, buy_stock_multiplayer, sell_stock_multiplayer, buy_rounds_multiplayer, unlock_crypto_multiplayer
from network import broadcast_game_state, receive_full_message

# AI players registry (player_id -> ai_instance)
ai_players = {}

# Input validation functions
def sanitize_string(text, max_length=100):
    """Sanitizes input string to prevent injection attacks."""
    if not isinstance(text, str):
        return ""
    # Remove HTML tags and escape special characters
    text = html.escape(text.strip())
    # Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    return text[:max_length]

def validate_player_name(name):
    """Validates player name format."""
    if not name or not isinstance(name, str):
        return False
    # Only allow alphanumeric, underscore, hyphen
    if not re.match(r'^[a-zA-Z0-9_-]{1,20}$', name):
        return False
    return True

def validate_stock_name(stock):
    """Validates that stock name is valid."""
    valid_stocks = NORMAL_STOCKS + CRYPTO_STOCKS
    return stock in valid_stocks

def validate_quantity(quantity):
    """Validates quantity is a positive integer."""
    if not isinstance(quantity, int):
        return False
    return 1 <= quantity <= 10000  # Reasonable limits

def validate_action(action):
    """Validates action type."""
    valid_actions = ["draw_card", "buy", "sell", "buy_rounds", "unlock_crypto", "chat", "set_name", "heartbeat"]
    return action in valid_actions


def register_ai_player(player_id, ai_instance):
    """Register an AI player with the server."""
    global ai_players
    ai_players[player_id] = ai_instance
    logging.info(f"AI player registered: {player_id}")


def is_ai_player(player_id):
    """Check if a player is an AI."""
    return player_id in ai_players


def process_ai_turn():
    """Process AI turn if current player is AI."""
    global ai_players

    with lock:
        current = game_state.get("current_player")
        if not current or current not in ai_players:
            return False

        ai = ai_players[current]
        if current not in game_state["players"]:
            return False

        # Get AI decision
        decision = ai.make_decision()

        # Handle None decision
        if decision is None:
            decision = {"action": "hold"}

        decision = ai.apply_difficulty_modifier(decision)
        ai.update_price_history()

        if not decision or decision.get("action") == "hold":
            # AI passes - draw card and end turn
            draw_card_multiplayer(current)
            advance_to_next_player(current)
            return True

        action = decision.get("action")

        # Process AI action
        if action == "buy" and "stock" in decision and "quantity" in decision:
            buy_stock_multiplayer(current, decision["stock"], decision["quantity"])
            logging.info(f"AI {current} buys {decision['quantity']}x {decision['stock']}")
        elif action == "sell" and "stock" in decision and "quantity" in decision:
            sell_stock_multiplayer(current, decision["stock"], decision["quantity"])
            logging.info(f"AI {current} sells {decision['quantity']}x {decision['stock']}")
        elif action == "buy_rounds":
            buy_rounds_multiplayer(current)
            logging.info(f"AI {current} buys rounds")
        elif action == "unlock_crypto":
            unlock_crypto_multiplayer(current)
            logging.info(f"AI {current} unlocks crypto")

        # Draw card and advance turn
        draw_card_multiplayer(current)
        advance_to_next_player(current)

        increment_state_version()
        threading.Thread(target=broadcast_game_state, daemon=True).start()
        return True


def advance_to_next_player(current_player):
    """Advance to the next player in turn order."""
    player_ids = list(game_state["players"].keys())
    if current_player in player_ids:
        current_idx = player_ids.index(current_player)
        next_idx = (current_idx + 1) % len(player_ids)
        game_state["current_player"] = player_ids[next_idx]
        increment_state_version()


def ai_turn_loop():
    """Background thread to process AI turns."""
    global server_running
    while server_running:
        time.sleep(1.0)  # Check every second
        try:
            if is_ai_player(game_state.get("current_player")):
                time.sleep(0.5)  # Small delay for realism
                process_ai_turn()
        except Exception as e:
            logging.error(f"Error in AI turn loop: {e}")


def start_server():
    global server_running
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.settimeout(SOCKET_TIMEOUT)
    try:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((DEFAULT_HOST, PORT))
        server.listen(5)
        server_running = True
        logging.info(f"Server erfolgreich gestartet auf {DEFAULT_HOST}:{PORT}")
        print(f"Server erfolgreich gestartet auf {DEFAULT_HOST}:{PORT}")

        # Start heartbeat checker thread
        heartbeat_thread = threading.Thread(target=check_heartbeats, daemon=True)
        heartbeat_thread.start()

        # Start AI turn processing thread
        ai_thread = threading.Thread(target=ai_turn_loop, daemon=True)
        ai_thread.start()

        # Start auto-save thread
        autosave_thread = threading.Thread(target=auto_save_loop, daemon=True)
        autosave_thread.start()

        while server_running:
            try:
                conn, addr = server.accept()
                logging.info(f"Neuer Client verbunden: {addr}")
                print(f"Neuer Client verbunden: {addr}")
                thread = threading.Thread(target=handle_client, args=(conn, addr))
                thread.daemon = True
                thread.start()
            except socket.timeout:
                continue
            except Exception as e:
                logging.error(f"Fehler beim Akzeptieren neuer Verbindungen: {e}")
                print(f"Fehler beim Akzeptieren neuer Verbindungen: {e}")
                break
    except OSError as e:
        logging.error(f"Server konnte nicht gestartet werden: {e}")
        print(f"Server konnte nicht gestartet werden: {e}")
    finally:
        server_running = False
        save_game_state()  # Save on shutdown
        server.close()
        logging.info("Server geschlossen")
        print("Server geschlossen")

def check_heartbeats():
    """Checks for dead clients based on heartbeat timeout."""
    global server_running
    while server_running:
        current_time = time.time()
        with lock:
            dead_clients = []
            for client_addr, last_heartbeat in list(client_heartbeats.items()):
                if current_time - last_heartbeat > HEARTBEAT_TIMEOUT:
                    dead_clients.append(client_addr)
                    logging.warning(f"Client {client_addr} Heartbeat Timeout")

            for client_addr in dead_clients:
                del client_heartbeats[client_addr]

        time.sleep(HEARTBEAT_INTERVAL)

def auto_save_loop():
    """Auto-saves game state periodically."""
    global server_running
    while server_running:
        time.sleep(60)  # Save every minute
        if game_state["players"]:  # Only save if there are players
            save_game_state()

def handle_client(conn, addr):
    player_id = f"player_{len(clients)}"

    with lock:
        player_data = initial_variables.copy()
        player_data["krypto"] = False
        player_data["lost"] = False
        player_data["game_over"] = False
        player_data["bought_stocks"] = 0
        player_data["sold_money"] = 0
        player_data["lost_money"] = 0
        player_data["lost_stocks"] = 0
        player_data["bytes_sent"] = 0
        player_data["bytes_received"] = 0
        if game_state["start_time"] is None:
            game_state["start_time"] = time.time()
        game_state["players"][player_id] = player_data
        game_state["players"][player_id]["running"] = True
        if game_state["current_player"] is None:
            game_state["current_player"] = player_id
        clients.append(conn)
        client_heartbeats[str(addr)] = time.time()
        increment_state_version()

    initial_data = {"player_id": player_id, "game_state": game_state, "timestamp": time.time()}
    data_str = json.dumps(initial_data, ensure_ascii=False)
    data_bytes = data_str.encode('utf-8')
    length_prefix = len(data_bytes).to_bytes(4, byteorder='big')

    try:
        conn.send(length_prefix + data_bytes)
        with lock:
            game_state["players"][player_id]["bytes_sent"] += len(length_prefix + data_bytes)
        logging.info(f"Initiale Daten an {player_id} ({addr}) gesendet: stocks={game_state['stocks']}")
        print(f"Initiale Daten an {player_id} ({addr}) gesendet: stocks={game_state['stocks']}")
    except Exception as e:
        logging.error(f"Fehler beim Senden der initialen Daten an {player_id}: {e}")
        print(f"Fehler beim Senden der initialen Daten an {player_id}: {e}")
        cleanup_client(conn, player_id, addr)
        return

    try:
        conn.setblocking(False)
        last_broadcast = 0

        while server_running and conn.fileno() != -1:
            try:
                data = receive_full_message(conn)

                if data is None:
                    current_time = time.time()
                    if current_time - last_broadcast >= BROADCAST_INTERVAL:
                        threading.Thread(target=broadcast_game_state, daemon=True).start()
                        last_broadcast = current_time
                    time.sleep(NETWORK_CHECK_INTERVAL)
                    continue

                if data.strip():
                    try:
                        request = json.loads(data)

                        # Validate action
                        action = request.get("action", "")
                        if not validate_action(action) and "name" not in request:
                            logging.warning(f"Ungültige Aktion von {player_id}: {action}")
                            continue

                        with lock:
                            if player_id in game_state["players"]:
                                game_state["players"][player_id]["bytes_received"] += len(data.encode('utf-8'))
                            else:
                                logging.error(f"Spieler {player_id} nicht mehr vorhanden")
                                break

                        logging.info(f"Empfangene Anfrage von {player_id}: {request}")
                        print(f"Empfangene Anfrage von {player_id}: {request}")

                        with lock:
                            # Update heartbeat
                            client_heartbeats[str(addr)] = time.time()

                            # Handle heartbeat action
                            if action == "heartbeat":
                                continue

                            # Handle name change
                            if "name" in request:
                                new_name = sanitize_string(request["name"], 20)
                                if validate_player_name(new_name) and new_name not in game_state["players"]:
                                    old_id = player_id
                                    game_state["players"][new_name] = game_state["players"].pop(old_id)
                                    if game_state["current_player"] == old_id:
                                        game_state["current_player"] = new_name
                                    logging.info(f"Spieler {old_id} hat Namen zu {new_name} geändert")
                                    print(f"Spieler {old_id} hat Namen zu {new_name} geändert")
                                    player_id = new_name
                                    increment_state_version()

                                    confirmation = {"action": "name_changed", "new_name": new_name}
                                    send_to_client(conn, confirmation, player_id)
                                    threading.Thread(target=broadcast_game_state, daemon=True).start()
                                else:
                                    logging.warning(f"Ungültiger Name von {player_id}: {request.get('name')}")

                            # Handle chat
                            elif action == "chat" and "message" in request:
                                message = sanitize_string(request["message"], MAX_CHAT_MESSAGE_LENGTH)
                                if message:
                                    game_state["chat_history"].append({
                                        "player": player_id,
                                        "message": message,
                                        "timestamp": time.time()
                                    })
                                    if len(game_state["chat_history"]) > MAX_CHAT_HISTORY:
                                        game_state["chat_history"] = game_state["chat_history"][-MAX_CHAT_HISTORY:]
                                    increment_state_version()
                                    logging.info(f"Chat-Nachricht von {player_id}: {message}")
                                    print(f"Chat-Nachricht von {player_id}: {message}")
                                    threading.Thread(target=broadcast_game_state, daemon=True).start()

                            # Handle draw_card
                            elif action == "draw_card":
                                if game_state["current_player"] == player_id:
                                    if player_id in game_state["players"]:
                                        draw_card_multiplayer(player_id)
                                        player_ids = list(game_state["players"].keys())
                                        if player_id in player_ids:
                                            current_idx = player_ids.index(player_id)
                                            next_idx = (current_idx + 1) % len(player_ids)
                                            game_state["current_player"] = player_ids[next_idx]
                                        increment_state_version()
                                        logging.info(f"Nächster Spieler: {game_state['current_player']}")
                                        print(f"Nächster Spieler: {game_state['current_player']}")
                                        threading.Thread(target=broadcast_game_state, daemon=True).start()

                            # Handle buy
                            elif action == "buy":
                                if game_state["current_player"] == player_id:
                                    stock = request.get("stock", "")
                                    quantity = request.get("quantity", 0)
                                    if validate_stock_name(stock) and validate_quantity(quantity):
                                        buy_stock_multiplayer(player_id, stock, quantity)
                                        increment_state_version()
                                        threading.Thread(target=broadcast_game_state, daemon=True).start()
                                    else:
                                        logging.warning(f"Ungültige Kaufanfrage von {player_id}: stock={stock}, qty={quantity}")

                            # Handle sell
                            elif action == "sell":
                                if game_state["current_player"] == player_id:
                                    stock = request.get("stock", "")
                                    quantity = request.get("quantity", 0)
                                    if validate_stock_name(stock) and validate_quantity(quantity):
                                        sell_stock_multiplayer(player_id, stock, quantity)
                                        increment_state_version()
                                        threading.Thread(target=broadcast_game_state, daemon=True).start()
                                    else:
                                        logging.warning(f"Ungültige Verkaufsanfrage von {player_id}: stock={stock}, qty={quantity}")

                            # Handle buy_rounds
                            elif action == "buy_rounds":
                                if game_state["current_player"] == player_id:
                                    buy_rounds_multiplayer(player_id)
                                    increment_state_version()
                                    threading.Thread(target=broadcast_game_state, daemon=True).start()

                            # Handle unlock_crypto
                            elif action == "unlock_crypto":
                                if game_state["current_player"] == player_id:
                                    unlock_crypto_multiplayer(player_id)
                                    increment_state_version()
                                    threading.Thread(target=broadcast_game_state, daemon=True).start()

                    except json.JSONDecodeError as e:
                        logging.error(f"Ungültige JSON von {player_id}: {e} (Daten: {data[:100]}...)")
                        print(f"Ungültige JSON von {player_id}: {e} (Daten: {data[:100]}...)")
                        continue
                    except KeyError as e:
                        logging.error(f"Fehlender Schlüssel in Anfrage von {player_id}: {e}")
                        print(f"Fehlender Schlüssel in Anfrage von {player_id}: {e}")
                        continue

            except ConnectionResetError:
                logging.warning(f"Verbindung zu {addr} wurde vom Client geschlossen")
                print(f"Verbindung zu {addr} wurde vom Client geschlossen")
                break
            except BrokenPipeError:
                logging.warning(f"Broken Pipe zu {addr}")
                print(f"Broken Pipe zu {addr}")
                break
            except Exception as e:
                logging.error(f"Fehler bei Spieler {player_id} ({addr}): {e}, Typ: {type(e).__name__}")
                print(f"Fehler bei Spieler {player_id} ({addr}): {e}, Typ: {type(e).__name__}")
                break

    finally:
        cleanup_client(conn, player_id, addr)

def send_to_client(conn, data_dict, player_id):
    """Sends data to a specific client with error handling."""
    try:
        data_str = json.dumps(data_dict, ensure_ascii=False)
        data_bytes = data_str.encode('utf-8')
        length_prefix = len(data_bytes).to_bytes(4, byteorder='big')
        conn.send(length_prefix + data_bytes)
        with lock:
            if player_id in game_state["players"]:
                game_state["players"][player_id]["bytes_sent"] += len(length_prefix + data_bytes)
        return True
    except Exception as e:
        logging.error(f"Fehler beim Senden an {player_id}: {e}")
        return False

def cleanup_client(conn, player_id, addr):
    """Cleans up client resources on disconnect."""
    with lock:
        if player_id in game_state["players"]:
            del game_state["players"][player_id]
        if conn in clients:
            clients.remove(conn)
        if str(addr) in client_heartbeats:
            del client_heartbeats[str(addr)]
        if game_state["current_player"] == player_id and game_state["players"]:
            player_ids = list(game_state["players"].keys())
            game_state["current_player"] = player_ids[0] if player_ids else None
        increment_state_version()

        try:
            remaining = [c.getpeername() for c in clients if c.fileno() != -1]
        except Exception:
            remaining = []

        logging.info(f"Spieler {player_id} entfernt. Verbleibende Clients: {remaining}")
        print(f"Spieler {player_id} entfernt. Verbleibende Clients: {remaining}")
        threading.Thread(target=broadcast_game_state, daemon=True).start()

    try:
        conn.close()
    except Exception as e:
        logging.debug(f"Fehler beim Schließen der Verbindung: {e}")
