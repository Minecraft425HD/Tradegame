import threading
import time
import socket
import json
from config import server_running, lock, clients, game_state, initial_variables, DEFAULT_HOST, PORT, logging
from game_logic import draw_card_multiplayer, buy_stock_multiplayer, sell_stock_multiplayer, buy_rounds_multiplayer, unlock_crypto_multiplayer
from network import broadcast_game_state, receive_full_message

def start_server():
    global server_running
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.settimeout(5)
    try:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((DEFAULT_HOST, PORT))
        server.listen(5)
        server_running = True
        logging.info(f"Server erfolgreich gestartet auf {DEFAULT_HOST}:{PORT}")
        print(f"Server erfolgreich gestartet auf {DEFAULT_HOST}:{PORT}")
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
        server.close()
        logging.info("Server geschlossen")
        print("Server geschlossen")

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
        with lock:
            if player_id in game_state["players"]:
                del game_state["players"][player_id]
            if conn in clients:
                clients.remove(conn)
        conn.close()
        return
    try:
        conn.setblocking(False)
        last_heartbeat = time.time()  # Für Heartbeat-Broadcasts
        while server_running and conn.fileno() != -1:
            try:
                data = receive_full_message(conn)
                if data is None:
                    # Heartbeat: Broadcast alle 1 Sekunde, wenn keine Aktion läuft
                    current_time = time.time()
                    if current_time - last_heartbeat >= 1.0:
                        threading.Thread(target=broadcast_game_state, daemon=True).start()
                        last_heartbeat = current_time
                    time.sleep(0.1)  # 100ms Sleep für geringe CPU-Last
                    continue
                if data.strip():
                    try:
                        request = json.loads(data)
                        with lock:
                            game_state["players"][player_id]["bytes_received"] += len(data.encode('utf-8'))
                        logging.info(f"Empfangene Anfrage von {player_id}: {request}")
                        print(f"Empfangene Anfrage von {player_id}: {request}")
                        with lock:
                            if "name" in request:
                                new_name = request["name"]
                                if new_name and new_name not in game_state["players"]:
                                    old_id = player_id
                                    game_state["players"][new_name] = game_state["players"].pop(old_id)
                                    if game_state["current_player"] == old_id:
                                        game_state["current_player"] = new_name
                                    logging.info(f"Spieler {old_id} hat Namen zu {new_name} geändert")
                                    print(f"Spieler {old_id} hat Namen zu {new_name} geändert")
                                    player_id = new_name
                                    confirmation = {"action": "name_changed", "new_name": new_name}
                                    data_str = json.dumps(confirmation, ensure_ascii=False)
                                    data_bytes = data_str.encode('utf-8')
                                    length_prefix = len(data_bytes).to_bytes(4, byteorder='big')
                                    conn.send(length_prefix + data_bytes)
                                    game_state["players"][player_id]["bytes_sent"] += len(length_prefix + data_bytes)
                                    threading.Thread(target=broadcast_game_state, daemon=True).start()
                           
                            if request["action"] == "draw_card" and game_state["current_player"] == player_id:
                                draw_card_multiplayer(player_id)
                                player_ids = list(game_state["players"].keys())
                                current_idx = player_ids.index(player_id)
                                next_idx = (current_idx + 1) % len(player_ids)
                                game_state["current_player"] = player_ids[next_idx]
                                logging.info(f"Nächster Spieler: {game_state['current_player']}")
                                print(f"Nächster Spieler: {game_state['current_player']}")
                                threading.Thread(target=broadcast_game_state, daemon=True).start()
                            elif request["action"] == "buy" and game_state["current_player"] == player_id:
                                buy_stock_multiplayer(player_id, request["stock"], request["quantity"])
                                threading.Thread(target=broadcast_game_state, daemon=True).start()
                            elif request["action"] == "sell" and game_state["current_player"] == player_id:
                                sell_stock_multiplayer(player_id, request["stock"], request["quantity"])
                                threading.Thread(target=broadcast_game_state, daemon=True).start()
                            elif request["action"] == "buy_rounds" and game_state["current_player"] == player_id:
                                buy_rounds_multiplayer(player_id)
                                threading.Thread(target=broadcast_game_state, daemon=True).start()
                            elif request["action"] == "unlock_crypto" and game_state["current_player"] == player_id:
                                unlock_crypto_multiplayer(player_id)
                                threading.Thread(target=broadcast_game_state, daemon=True).start()
                    except json.JSONDecodeError as e:
                        logging.error(f"Ungültige Nachricht von {player_id}: {e} (Daten: {data[:100]}...)")
                        print(f"Ungültige Nachricht von {player_id}: {e} (Daten: {data[:100]}...)")
                        continue
            except ConnectionResetError:
                logging.warning(f"Verbindung zu {addr} wurde vom Client geschlossen")
                print(f"Verbindung zu {addr} wurde vom Client geschlossen")
                break
            except Exception as e:
                logging.error(f"Fehler bei Spieler {player_id} ({addr}): {e}")
                print(f"Fehler bei Spieler {player_id} ({addr}): {e}")
                break
    finally:
        with lock:
            if player_id in game_state["players"]:
                del game_state["players"][player_id]
            if conn in clients:
                clients.remove(conn)
            if game_state["current_player"] == player_id and game_state["players"]:
                player_ids = list(game_state["players"].keys())
                game_state["current_player"] = player_ids[0] if player_ids else None
            logging.info(f"Spieler {player_id} entfernt. Verbleibende Clients: {[c.getpeername() for c in clients if c.fileno() != -1]}")
            print(f"Spieler {player_id} entfernt. Verbleibende Clients: {[c.getpeername() for c in clients if c.fileno() != -1]}")
            threading.Thread(target=broadcast_game_state, daemon=True).start()
        try:
            conn.close()
        except:
            pass  # Socket may already be closed