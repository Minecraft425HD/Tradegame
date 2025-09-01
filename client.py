import socket
import json
import time
import pygame
from config import server_running, game_state, lock, logging, colors, PORT
from pygame_setup import screen, fullscreen, clock, background_image
from pygame_setup import clock, background_image
from ui import draw_text, Button, draw_input_box, draw_stock_label
from game_logic import get_news_text
from network import receive_full_message

def run_client(host, is_host=False, player_name=None):
    from screens import show_news_screen, show_shop_screen, show_settings_screen, show_results_screen
    global screen, fullscreen, server_running
    max_connect_attempts = 3
    connect_delay = 2 # seconds
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(5)
    last_wait_message = 0
  
    for attempt in range(max_connect_attempts):
        try:
            client.connect((host, PORT))
            logging.info(f"Erfolgreich verbunden mit {host}:{PORT}, Versuch {attempt + 1}/{max_connect_attempts}")
            print(f"Erfolgreich verbunden mit {host}:{PORT}, Versuch {attempt + 1}/{max_connect_attempts}")
            break
        except Exception as e:
            logging.error(f"Verbindung fehlgeschlagen zu {host}:{PORT}: {e}, Versuch {attempt + 1}/{max_connect_attempts}")
            print(f"Verbindung fehlgeschlagen zu {host}:{PORT}: {e}, Versuch {attempt + 1}/{max_connect_attempts}")
            if attempt < max_connect_attempts - 1:
                time.sleep(connect_delay)
            else:
                return False
    client.setblocking(False)
    player_id = None
    last_timestamp = 0
    # Receive initial data
    for attempt in range(max_connect_attempts):
        data = receive_full_message(client)
        if data:
            try:
                initial_data = json.loads(data)
                player_id = initial_data["player_id"]
                with lock:
                    game_state.update(initial_data["game_state"])
                    last_timestamp = initial_data["timestamp"]
                    if player_id not in game_state["players"]:
                        logging.error(f"Fehler: {player_id} nicht in game_state['players'] gefunden!")
                        print(f"Fehler: {player_id} nicht in game_state['players'] gefunden!")
                        client.close()
                        return False
                    game_state["players"][player_id]["bytes_received"] += len(data.encode('utf-8'))
                logging.info(f"Player-ID erhalten: {player_id}, Initialer Zustand: stocks={game_state['stocks']}")
                print(f"Player-ID erhalten: {player_id}, Initialer Zustand: stocks={game_state['stocks']}")
                break
            except json.JSONDecodeError as e:
                logging.error(f"Fehler beim Parsen der initialen Daten: {e}, Versuch {attempt + 1}/{max_connect_attempts}")
                print(f"Fehler beim Parsen der initialen Daten: {e}, Versuch {attempt + 1}/{max_connect_attempts}")
                if attempt < max_connect_attempts - 1:
                    time.sleep(connect_delay)
                else:
                    client.close()
                    return False
        else:
            logging.error(f"Konnte keine initialen Daten empfangen, Versuch {attempt + 1}/{max_connect_attempts}!")
            print(f"Konnte keine initialen Daten empfangen, Versuch {attempt + 1}/{max_connect_attempts}!")
            if attempt < max_connect_attempts - 1:
                time.sleep(connect_delay)
            else:
                client.close()
                return False
    if player_id is None:
        logging.error("Konnte keine Player-ID erhalten!")
        print("Konnte keine Player-ID erhalten!")
        client.close()
        return False
    def send_request(action, stock=None, quantity=None, name=None):
        nonlocal player_id
        if game_state["current_player"] != player_id and action != "set_name":
            logging.info(f"Nicht dran! Aktueller Spieler: {game_state['current_player']}")
            print(f"Nicht dran! Aktueller Spieler: {game_state['current_player']}")
            return False
        request = {"action": action}
        if stock:
            request["stock"] = stock
        if quantity:
            request["quantity"] = quantity
        if name:
            request["name"] = name
        data_str = json.dumps(request, ensure_ascii=False)
        data_bytes = data_str.encode('utf-8')
        length_prefix = len(data_bytes).to_bytes(4, byteorder='big')
        try:
            client.send(length_prefix + data_bytes)
            with lock:
                game_state["players"][player_id]["bytes_sent"] += len(length_prefix + data_bytes)
            logging.info(f"Nachricht gesendet: {data_str}")
            print(f"Nachricht gesendet: {data_str}")
            return True
        except (ConnectionResetError, BrokenPipeError):
            logging.warning(f"Verbindung zu Server geschlossen beim Senden")
            print(f"Verbindung zu Server geschlossen beim Senden")
            return False
        except Exception as e:
            logging.error(f"Fehler beim Senden der Nachricht: {e}")
            print(f"Fehler beim Senden der Nachricht: {e}")
            return False
    if player_name:
        if send_request("set_name", name=player_name):
            start_time = time.time()
            while time.time() - start_time < 5:
                data = receive_full_message(client)
                if data and "action" in data and json.loads(data).get("action") == "name_changed":
                    new_name = json.loads(data).get("new_name")
                    logging.info(f"Namenswechsel bestätigt: {player_id} zu {new_name}")
                    print(f"Namenswechsel bestätigt: {player_id} zu {new_name}")
                    player_id = new_name
                    break
                pygame.time.wait(10)
    quantity = 0
    selected_stock = None
    persistent_error_message = ""
    save_message = ""
    running = True
    pulse_size = 0
    pulse_direction = 1
    while running and client.fileno() != -1:
        # Verarbeite Pygame-Events zuerst, um UI reaktionsfähig zu halten
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                if is_host:
                    server_running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if minus_10_rect.collidepoint(event.pos):
                    quantity -= 10
                elif minus_1_rect.collidepoint(event.pos):
                    quantity -= 1
                elif plus_1_rect.collidepoint(event.pos):
                    quantity += 1
                elif plus_10_rect.collidepoint(event.pos):
                    quantity += 10
                elif news_button_rect.collidepoint(event.pos):
                    show_news_screen(player_id, client)
                elif shop_button_rect.collidepoint(event.pos):
                    show_shop_screen(player_id, client, send_request)
                for stock, label in stock_labels.items():
                    if label.collidepoint(event.pos):
                        selected_stock = stock
                if card_button_rect.collidepoint(event.pos):
                    send_request("draw_card")
                elif end_button_rect and end_button_rect.collidepoint(event.pos):
                    running = False
                    show_results_screen(player_id, client)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    show_settings_screen(client, player_id)
                    if not running:
                        break
                elif event.key == pygame.K_RETURN and selected_stock:
                    if quantity > 0:
                        cost = quantity * game_state["stocks"].get(selected_stock, 0)
                        if player.get("konto", 0) >= cost:
                            send_request("buy", selected_stock, quantity)
                            quantity = 0
                            persistent_error_message = ""
                        else:
                            persistent_error_message = "Nicht genügend Geld zum Kauf!"
                    elif quantity < 0:
                        if player.get(f"A{selected_stock.lower()}", 0) >= abs(quantity):
                            send_request("sell", selected_stock, abs(quantity))
                            quantity = 0
                            persistent_error_message = ""
                        else:
                            persistent_error_message = "Nicht genügend Aktien zum Verkauf!"
        
        # Netzwerk-Check nach Events
        try:
            data = receive_full_message(client)
            if data:
                try:
                    new_state = json.loads(data)
                    if new_state.get("action") == "name_changed":
                        new_name = new_state.get("new_name")
                        if new_name and new_name != player_id:
                            logging.info(f"Spieler-ID aktualisiert: {player_id} zu {new_name}")
                            print(f"Spieler-ID aktualisiert: {player_id} zu {new_name}")
                            player_id = new_name
                    elif new_state.get("timestamp", 0) > last_timestamp:
                        with lock:
                            game_state.update(new_state["game_state"])
                            last_timestamp = new_state["timestamp"]
                            if player_id in game_state["players"]:
                                game_state["players"][player_id]["bytes_received"] += len(data.encode('utf-8'))
                                logging.info(f"Game State aktualisiert: stocks={game_state['stocks']}, timestamp={last_timestamp}")
                                print(f"Game State aktualisiert: stocks={game_state['stocks']}, timestamp={last_timestamp}")
                            else:
                                logging.error(f"Fehler: {player_id} nicht in game_state['players']")
                                print(f"Fehler: {player_id} nicht in game_state['players']")
                                running = False
                except json.JSONDecodeError as e:
                    logging.error(f"Fehler beim Parsen der empfangenen Daten: {e} (Daten: {data[:100]}...)")
                    print(f"Fehler beim Parsen der empfangenen Daten: {e} (Daten: {data[:100]}...)")
            # Entferne periodischen wait und Logging
        except BlockingIOError:
            pass  # Keine Daten, normal weiter
        except ConnectionResetError:
            logging.warning(f"Verbindung zum Server wurde geschlossen")
            print(f"Verbindung zum Server wurde geschlossen")
            running = False
        except Exception as e:
            logging.error(f"Fehler in Hauptschleife: {e}, Typ: {type(e).__name__}")
            print(f"Fehler in Hauptschleife: {e}, Typ: {type(e).__name__}")
            running = False
        
        if player_id not in game_state.get("players", {}):
            logging.error(f"Spieler {player_id} nicht mehr im Spiel!")
            print(f"Spieler {player_id} nicht mehr im Spiel!")
            running = False
        
        player = game_state["players"].get(player_id, {})
      
        if len(game_state["players"]) == 2 and player.get("game_over", False):
            running = False
            show_results_screen(player_id, client)
        if player.get("lost", False):
            running = False
            show_results_screen(player_id, client)
        
        if background_image:
            screen.blit(background_image, (0, 0))
        else:
            screen.fill(colors["GRAY"])
        title_font = pygame.font.Font(None, 48)
        font = pygame.font.Font(None, 24)
        big_font = pygame.font.Font(None, 48)
        small_font = pygame.font.Font(None, 24)
        draw_text("Multiplayer Börsenspiel", title_font, colors["BLACK"], screen.get_width() // 2 - 150, 40)
        draw_text(f"Spieler: {player_id}", font, colors["BLACK"], 10, 10)
        draw_text(f"Aktueller Spieler: {game_state['current_player']}", font, colors["BLACK"], screen.get_width() // 2 - 100, 80)
      
        current_round = player.get("game_round", 0)
        max_rounds = player.get("max_rounds", 50)
        remaining_rounds = max_rounds - current_round
        draw_text(f"Runde: {current_round}/{max_rounds} (Übrig: {remaining_rounds})", font, colors["BLACK"], screen.get_width() // 2 - 100, 110)
        all_stocks = ["Beyer", "BMW", "BP", "Commerzbank"]
        if player.get("krypto", False):
            all_stocks.extend(["Bitcoin", "Ethereum", "Litecoin", "Dogecoin"])
        longest_name_width = max([small_font.render(stock, True, colors["BLACK"]).get_width() for stock in all_stocks])
        bar_start_x = 50 + longest_name_width + 10
        draw_text("Aktienkurse:", font, colors["BLACK"], 50, 140)
        normal_stocks = ["Beyer", "BMW", "BP", "Commerzbank"]
        stock_colors = [colors["BLUE"], colors["RED"], colors["GREEN"], colors["YELLOW"]]
        max_stock_value = 250
        max_bar_length = 300
        for i, stock in enumerate(normal_stocks):
            value = game_state["stocks"].get(stock, 0)
            bar_length = (value / max_stock_value) * max_bar_length
            y_position = 180 + i * 40
            draw_text(stock, small_font, colors["BLACK"], 50, y_position - 10)
            pygame.draw.rect(screen, colors["GRAY"], (bar_start_x, y_position, max_bar_length, 20))
            pygame.draw.rect(screen, stock_colors[i], (bar_start_x, y_position, bar_length, 20))
            draw_text(f"{value}$", small_font, colors["BLACK"], bar_start_x + max_bar_length + 10, y_position - 10)
        if player.get("krypto", False):
            draw_text("Kryptowährungen:", font, colors["BLACK"], 50, 340)
            crypto_stocks = ["Bitcoin", "Ethereum", "Litecoin", "Dogecoin"]
            crypto_colors = [(255, 165, 0), (128, 0, 128), (0, 255, 255), (255, 105, 180)]
            max_crypto_value = 100000
            for i, stock in enumerate(crypto_stocks):
                value = game_state["stocks"].get(stock, 0)
                bar_length = (value / max_crypto_value) * max_bar_length
                y_position = 380 + i * 40
                draw_text(stock, small_font, colors["BLACK"], 50, y_position - 10)
                pygame.draw.rect(screen, colors["GRAY"], (bar_start_x, y_position, max_bar_length, 20))
                pygame.draw.rect(screen, crypto_colors[i], (bar_start_x, y_position, bar_length, 20))
                draw_text(f"{value}$", small_font, colors["BLACK"], bar_start_x + max_bar_length + 10, y_position - 10)
        mouse_pos = pygame.mouse.get_pos()
        news_button = Button("News", screen.get_width() - 180, 10, colors["BLUE"], hover=pygame.Rect(screen.get_width() - 180, 10, 200, 50).collidepoint(mouse_pos))
        shop_button = Button("Shop", screen.get_width() - 180, 70, colors["YELLOW"], hover=pygame.Rect(screen.get_width() - 180, 70, 200, 50).collidepoint(mouse_pos))
        news_button_rect = news_button.draw()
        shop_button_rect = shop_button.draw()
        draw_text("Dein Kontostand:", font, colors["BLACK"], 50, screen.get_height() - 350)
        draw_text(f"Kontostand: {player.get('konto', 0)}$", small_font, colors["BLACK"], 50, screen.get_height() - 320)
        total_value = 0
        for i, stock in enumerate(normal_stocks):
            qty = player.get(f"A{stock.lower()}", 0)
            value = qty * game_state["stocks"].get(stock, 0)
            total_value += value
            draw_text(f"{stock}: {qty} Aktien Wert: {value}$", small_font, colors["BLACK"], 50, screen.get_height() - 290 + i * 20)
        if player.get("krypto", False):
            crypto_stocks = ["Bitcoin", "Ethereum", "Litecoin", "Dogecoin"]
            for i, stock in enumerate(crypto_stocks):
                qty = player.get(f"A{stock.lower()}", 0)
                value = qty * game_state["stocks"].get(stock, 0)
                total_value += value
                draw_text(f"{stock}: {qty} Aktien Wert: {value}$", small_font, colors["BLACK"], 50, screen.get_height() - 290 + (len(normal_stocks) + i) * 20)
        draw_text(f"Gesamtwert der Aktien: {total_value}$", small_font, colors["BLACK"], 50, screen.get_height() - 290 + (len(normal_stocks) + (len(crypto_stocks) if player.get("krypto", False) else 0)) * 20)
        stock_labels = {}
        normal_stocks_list = ["Beyer", "BMW", "BP", "Commerzbank"]
        crypto_stocks_list = ["Bitcoin", "Ethereum", "Litecoin", "Dogecoin"] if player.get("krypto", False) else []
        all_stocks = normal_stocks_list + crypto_stocks_list
        stocks_y = screen.get_height() - 240
        for i, stock in enumerate(all_stocks):
            x = screen.get_width() - 420 if i < 4 else screen.get_width() - 210
            y = stocks_y + (i % 4) * 30
            stock_labels[stock] = draw_stock_label(stock, x, y, selected_stock == stock)
        quantity_y = screen.get_height() - 90
        button_width = 60
        button_height = 50
        total_width = (button_width * 2 + 10) + 100 + (button_width * 2 + 10)
        start_x = screen.get_width() - total_width - 20
        minus_10_button = Button("-10", start_x, quantity_y, colors["RED"], width=button_width, height=button_height)
        minus_1_button = Button("-1", start_x + 70, quantity_y, colors["RED"], width=button_width, height=button_height)
        plus_1_button = Button("+1", start_x + 180, quantity_y, colors["GREEN"], width=button_width, height=button_height)
        plus_10_button = Button("+10", start_x + 250, quantity_y, colors["GREEN"], width=button_width, height=button_height)
      
        minus_10_rect = minus_10_button.draw()
        minus_1_rect = minus_1_button.draw()
        minus_1_right = start_x + 70 + button_width
        plus_1_left = start_x + 180
        quantity_center = (minus_1_right + plus_1_left) // 2
        quantity_width = big_font.render(str(quantity), True, colors["BLACK"]).get_width()
        quantity_x = quantity_center - quantity_width // 2
        draw_text(str(quantity), big_font, colors["BLACK"], quantity_x, quantity_y + 5)
        plus_1_rect = plus_1_button.draw()
        plus_10_rect = plus_10_button.draw()
        if game_state["drawn_values"]:
            card_width = 300
            card_height = 150
            x_margin = (screen.get_width() - card_width) // 2
            y_margin = (screen.get_height() - card_height) // 2 - 50
            if current_round >= max_rounds:
                draw_text("Sie befinden sich in der letzten Runde. Gehen Sie in den Shop, um weitere Runden zu kaufen", font, colors["RED"], x_margin - 150, y_margin - 30)
            pygame.draw.rect(screen, colors["BLACK"], (x_margin, y_margin, card_width, card_height), 2)
            draw_text("Karte", small_font, colors["BLACK"], x_margin + (card_width // 2) - 30, y_margin + 10)
            for i, (stock, value) in enumerate(game_state["drawn_values"].items()):
                draw_text(f"{stock}: {value}", small_font, colors["BLACK"], x_margin + 20, y_margin + 40 + i * 30)
            card_button = Button("Karte ziehen", x_margin + (card_width // 2) - 100, y_margin + card_height + 20, colors["BLUE"])
        else:
            card_button = Button("Karte ziehen", screen.get_width() // 2 - 100, screen.get_height() // 2 + 50, colors["BLUE"])
            if current_round >= max_rounds:
                draw_text("Sie befinden sich in der letzten Runde. Gehen Sie in den Shop, um weitere Runden zu kaufen", font, colors["RED"], screen.get_width() // 2 - 300, screen.get_height() // 2 - 80)
      
        if game_state["current_player"] == player_id and not game_state["drawn_values"]:
            pulse_size += pulse_direction * 2
            if pulse_size >= 20 or pulse_size <= 0:
                pulse_direction *= -1
            card_button_rect = pygame.Rect(card_button.x - pulse_size, card_button.y - pulse_size,
                                          card_button.width + 2 * pulse_size, card_button.height + 2 * pulse_size)
            pygame.draw.rect(screen, colors["YELLOW"], card_button_rect, 4, border_radius=15)
      
        card_button_rect = card_button.draw()
        if current_round >= max_rounds:
            end_button = Button("Beenden", screen.get_width() // 2 - 100, screen.get_height() - 60, colors["ORANGE"])
            end_button_rect = end_button.draw()
        else:
            end_button_rect = None
        if persistent_error_message:
            draw_text(persistent_error_message, pygame.font.Font(None, 36), colors["RED"], screen.get_width() // 2 - 200, card_button_rect.y + 70)
        if save_message:
            draw_text(save_message, pygame.font.Font(None, 36), colors["BLACK"], screen.get_width() // 2 - 200, screen.get_height() // 2)
        
        pygame.display.flip()
        clock.tick(60)
    client.close()
    if is_host:
        server_running = False
    return True