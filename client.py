import socket
import json
import time
import pygame
from config import server_running, game_state, lock, logging, colors
from constants import (
    PORT, MAX_CONNECT_ATTEMPTS, CONNECT_DELAY, SOCKET_TIMEOUT,
    NETWORK_CHECK_INTERVAL, MAX_CHAT_MESSAGE_LENGTH, HEARTBEAT_INTERVAL,
    MAX_STOCK_PRICE, MAX_BAR_LENGTH, MAX_CRYPTO_DISPLAY_VALUE,
    FPS, PULSE_SPEED, MAX_PULSE_SIZE, CHAT_FADE_START, CHAT_FADE_END,
    NORMAL_STOCKS, CRYPTO_STOCKS, STOCK_COLORS
)
from pygame_setup import screen, fullscreen, clock, background_image
from ui import draw_text, Button, draw_input_box, draw_stock_label
from game_logic import get_news_text
from network import receive_full_message

def validate_quantity(quantity):
    """Validates quantity is within acceptable range."""
    return -10000 <= quantity <= 10000

def run_client(host, is_host=False, player_name=None):
    from screens import show_news_screen, show_shop_screen, show_settings_screen, show_results_screen
    global screen, fullscreen, server_running

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(SOCKET_TIMEOUT)
    chat_active = False
    chat_input_text = ""
    chat_font = pygame.font.Font(None, 28)
    last_heartbeat = 0

    # Connection attempts
    for attempt in range(MAX_CONNECT_ATTEMPTS):
        try:
            client.connect((host, PORT))
            logging.info(f"Erfolgreich verbunden mit {host}:{PORT}, Versuch {attempt + 1}/{MAX_CONNECT_ATTEMPTS}")
            print(f"Erfolgreich verbunden mit {host}:{PORT}, Versuch {attempt + 1}/{MAX_CONNECT_ATTEMPTS}")
            break
        except Exception as e:
            logging.error(f"Verbindung fehlgeschlagen zu {host}:{PORT}: {e}, Versuch {attempt + 1}/{MAX_CONNECT_ATTEMPTS}")
            print(f"Verbindung fehlgeschlagen zu {host}:{PORT}: {e}, Versuch {attempt + 1}/{MAX_CONNECT_ATTEMPTS}")
            if attempt < MAX_CONNECT_ATTEMPTS - 1:
                time.sleep(CONNECT_DELAY)
            else:
                return False

    client.setblocking(False)
    player_id = None
    last_timestamp = 0
    last_state_version = 0

    # Receive initial data
    for attempt in range(MAX_CONNECT_ATTEMPTS):
        data = receive_full_message(client)
        if data:
            try:
                initial_data = json.loads(data)
                player_id = initial_data["player_id"]
                with lock:
                    game_state.update(initial_data["game_state"])
                    last_timestamp = initial_data["timestamp"]
                    last_state_version = game_state.get("state_version", 0)
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
                logging.error(f"Fehler beim Parsen der initialen Daten: {e}, Versuch {attempt + 1}/{MAX_CONNECT_ATTEMPTS}")
                print(f"Fehler beim Parsen der initialen Daten: {e}, Versuch {attempt + 1}/{MAX_CONNECT_ATTEMPTS}")
                if attempt < MAX_CONNECT_ATTEMPTS - 1:
                    time.sleep(CONNECT_DELAY)
                else:
                    client.close()
                    return False
        else:
            logging.error(f"Konnte keine initialen Daten empfangen, Versuch {attempt + 1}/{MAX_CONNECT_ATTEMPTS}!")
            print(f"Konnte keine initialen Daten empfangen, Versuch {attempt + 1}/{MAX_CONNECT_ATTEMPTS}!")
            if attempt < MAX_CONNECT_ATTEMPTS - 1:
                time.sleep(CONNECT_DELAY)
            else:
                client.close()
                return False

    if player_id is None:
        logging.error("Konnte keine Player-ID erhalten!")
        print("Konnte keine Player-ID erhalten!")
        client.close()
        return False

    def send_request(action, stock=None, quantity=None, name=None, message=None):
        nonlocal player_id
        # buy_rounds and unlock_crypto are allowed any time (shop purchases)
        unrestricted = ["set_name", "chat", "heartbeat", "buy_rounds", "unlock_crypto"]
        if game_state["current_player"] != player_id and action not in unrestricted:
            logging.info(f"Nicht dran! Aktueller Spieler: {game_state['current_player']}")
            return False

        request = {"action": action}
        if stock:
            request["stock"] = stock
        if quantity is not None and validate_quantity(quantity):
            request["quantity"] = abs(quantity)  # Always send positive quantity
        if name:
            request["name"] = name
        if message:
            # Sanitize message on client side too
            request["message"] = message[:MAX_CHAT_MESSAGE_LENGTH]

        data_str = json.dumps(request, ensure_ascii=False)
        data_bytes = data_str.encode('utf-8')
        length_prefix = len(data_bytes).to_bytes(4, byteorder='big')

        try:
            client.send(length_prefix + data_bytes)
            with lock:
                if player_id in game_state["players"]:
                    game_state["players"][player_id]["bytes_sent"] += len(length_prefix + data_bytes)
            logging.info(f"Nachricht gesendet: {data_str}")
            print(f"Nachricht gesendet: {data_str}")
            return True
        except (ConnectionResetError, BrokenPipeError):
            logging.warning("Verbindung zu Server geschlossen beim Senden")
            print("Verbindung zu Server geschlossen beim Senden")
            return False
        except Exception as e:
            logging.error(f"Fehler beim Senden der Nachricht: {e}")
            print(f"Fehler beim Senden der Nachricht: {e}")
            return False

    def send_heartbeat():
        """Sends heartbeat to server."""
        nonlocal last_heartbeat
        current_time = time.time()
        if current_time - last_heartbeat >= HEARTBEAT_INTERVAL:
            try:
                request = {"action": "heartbeat"}
                data_str = json.dumps(request, ensure_ascii=False)
                data_bytes = data_str.encode('utf-8')
                length_prefix = len(data_bytes).to_bytes(4, byteorder='big')
                client.send(length_prefix + data_bytes)
                last_heartbeat = current_time
            except Exception:
                pass  # Heartbeat failure is not critical

    # Set player name if provided
    if player_name:
        if send_request("set_name", name=player_name):
            start_time = time.time()
            while time.time() - start_time < 5:
                data = receive_full_message(client)
                if data:
                    try:
                        response = json.loads(data)
                        if response.get("action") == "name_changed":
                            new_name = response.get("new_name")
                            logging.info(f"Namenswechsel bestätigt: {player_id} zu {new_name}")
                            print(f"Namenswechsel bestätigt: {player_id} zu {new_name}")
                            player_id = new_name
                            break
                    except json.JSONDecodeError:
                        pass
                pygame.time.wait(10)

    quantity = 0
    selected_stock = None
    persistent_error_message = ""
    save_message = ""
    running = True
    pulse_size = 0
    pulse_direction = 1
    last_network_check = 0

    # Initialize button rects to avoid reference before assignment
    minus_10_rect = pygame.Rect(0, 0, 0, 0)
    minus_1_rect = pygame.Rect(0, 0, 0, 0)
    plus_1_rect = pygame.Rect(0, 0, 0, 0)
    plus_10_rect = pygame.Rect(0, 0, 0, 0)
    news_button_rect = pygame.Rect(0, 0, 0, 0)
    shop_button_rect = pygame.Rect(0, 0, 0, 0)
    card_button_rect = pygame.Rect(0, 0, 0, 0)
    end_button_rect = None
    stock_labels = {}

    while running and client.fileno() != -1:
        # Process Pygame events first for responsive UI
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                if is_host:
                    server_running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if minus_10_rect.collidepoint(event.pos):
                    quantity = max(-10000, quantity - 10)
                elif minus_1_rect.collidepoint(event.pos):
                    quantity = max(-10000, quantity - 1)
                elif plus_1_rect.collidepoint(event.pos):
                    quantity = min(10000, quantity + 1)
                elif plus_10_rect.collidepoint(event.pos):
                    quantity = min(10000, quantity + 10)
                elif news_button_rect.collidepoint(event.pos):
                    show_news_screen(player_id, client)
                elif shop_button_rect.collidepoint(event.pos):
                    show_shop_screen(player_id, client, send_request)
                elif card_button_rect.collidepoint(event.pos):
                    if game_state["current_player"] == player_id:
                        send_request("draw_card")
                    else:
                        persistent_error_message = f"Warte auf {game_state['current_player']}!"
                elif end_button_rect and end_button_rect.collidepoint(event.pos):
                    running = False
                    show_results_screen(player_id, client)
                else:
                    for stock, label in stock_labels.items():
                        if label.collidepoint(event.pos):
                            selected_stock = stock
                            break
            elif event.type == pygame.KEYDOWN:
                if chat_active:
                    if event.key == pygame.K_RETURN:
                        if chat_input_text.strip():
                            if send_request("chat", message=chat_input_text):
                                chat_input_text = ""
                            else:
                                persistent_error_message = "Fehler beim Senden der Nachricht!"
                        chat_active = False
                    elif event.key == pygame.K_BACKSPACE:
                        chat_input_text = chat_input_text[:-1]
                    elif event.key == pygame.K_ESCAPE:
                        chat_active = False
                    else:
                        if len(chat_input_text) < MAX_CHAT_MESSAGE_LENGTH and event.unicode.isprintable():
                            chat_input_text += event.unicode
                else:
                    if event.key == pygame.K_t:
                        chat_active = True
                        chat_input_text = ""
                    elif event.key == pygame.K_ESCAPE:
                        show_settings_screen(client, player_id)
                        if not running:
                            break
                    elif event.key == pygame.K_RETURN and selected_stock:
                        if game_state["current_player"] != player_id:
                            persistent_error_message = f"Warte auf {game_state['current_player']}!"
                        else:
                            player = game_state["players"].get(player_id, {})
                            if quantity > 0:
                                cost = quantity * game_state["stocks"].get(selected_stock, 0)
                                if player.get("konto", 0) >= cost:
                                    send_request("buy", selected_stock, quantity)
                                    quantity = 0
                                    persistent_error_message = ""
                                else:
                                    persistent_error_message = "Nicht genügend Geld zum Kauf!"
                            elif quantity < 0:
                                stock_key = f"A{selected_stock.lower()}"
                                if player.get(stock_key, 0) >= abs(quantity):
                                    send_request("sell", selected_stock, abs(quantity))
                                    quantity = 0
                                    persistent_error_message = ""
                                else:
                                    persistent_error_message = "Nicht genügend Aktien zum Verkauf!"

        # Network check with throttling
        current_time = time.time()
        if current_time - last_network_check >= NETWORK_CHECK_INTERVAL:
            # Send heartbeat
            send_heartbeat()

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
                            new_version = new_state.get("state_version", 0)
                            if new_version > last_state_version:
                                with lock:
                                    game_state.update(new_state["game_state"])
                                    last_timestamp = new_state["timestamp"]
                                    last_state_version = new_version
                                    if player_id in game_state["players"]:
                                        game_state["players"][player_id]["bytes_received"] += len(data.encode('utf-8'))
                                        logging.info(f"Game State aktualisiert: v{new_version}, stocks={game_state['stocks']}")
                                        print(f"Game State aktualisiert: v{new_version}")
                                    else:
                                        logging.error(f"Fehler: {player_id} nicht in game_state['players']")
                                        print(f"Fehler: {player_id} nicht in game_state['players']")
                                        running = False
                    except json.JSONDecodeError as e:
                        logging.error(f"Fehler beim Parsen: {e}")
                last_network_check = current_time
            except BlockingIOError:
                pass
            except ConnectionResetError:
                logging.warning("Verbindung zum Server wurde geschlossen")
                print("Verbindung zum Server wurde geschlossen")
                running = False
            except Exception as e:
                logging.error(f"Fehler in Hauptschleife: {e}, Typ: {type(e).__name__}")
                print(f"Fehler in Hauptschleife: {e}, Typ: {type(e).__name__}")
                running = False

        if player_id not in game_state.get("players", {}):
            logging.error(f"Spieler {player_id} nicht mehr im Spiel!")
            print(f"Spieler {player_id} nicht mehr im Spiel!")
            running = False
            continue

        player = game_state["players"].get(player_id, {})

        if len(game_state["players"]) == 2 and player.get("game_over", False):
            running = False
            show_results_screen(player_id, client)
        if player.get("lost", False):
            running = False
            show_results_screen(player_id, client)

        # Render
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

        # Stock display
        all_stocks_display = list(NORMAL_STOCKS)
        if player.get("krypto", False):
            all_stocks_display.extend(CRYPTO_STOCKS)
        longest_name_width = max([small_font.render(stock, True, colors["BLACK"]).get_width() for stock in all_stocks_display])
        bar_start_x = 50 + longest_name_width + 10

        draw_text("Aktienkurse:", font, colors["BLACK"], 50, 140)
        stock_colors_list = [colors["BLUE"], colors["RED"], colors["GREEN"], colors["YELLOW"]]

        for i, stock in enumerate(NORMAL_STOCKS):
            value = game_state["stocks"].get(stock, 0)
            bar_length = (value / MAX_STOCK_PRICE) * MAX_BAR_LENGTH
            y_position = 180 + i * 40
            draw_text(stock, small_font, colors["BLACK"], 50, y_position - 10)
            pygame.draw.rect(screen, colors["GRAY"], (bar_start_x, y_position, MAX_BAR_LENGTH, 20))
            pygame.draw.rect(screen, stock_colors_list[i], (bar_start_x, y_position, bar_length, 20))
            draw_text(f"{value}$", small_font, colors["BLACK"], bar_start_x + MAX_BAR_LENGTH + 10, y_position - 10)

        if player.get("krypto", False):
            draw_text("Kryptowährungen:", font, colors["BLACK"], 50, 340)
            crypto_colors_list = [STOCK_COLORS["Bitcoin"], STOCK_COLORS["Ethereum"], STOCK_COLORS["Litecoin"], STOCK_COLORS["Dogecoin"]]
            for i, stock in enumerate(CRYPTO_STOCKS):
                value = game_state["stocks"].get(stock, 0)
                bar_length = (value / MAX_CRYPTO_DISPLAY_VALUE) * MAX_BAR_LENGTH
                y_position = 380 + i * 40
                draw_text(stock, small_font, colors["BLACK"], 50, y_position - 10)
                pygame.draw.rect(screen, colors["GRAY"], (bar_start_x, y_position, MAX_BAR_LENGTH, 20))
                pygame.draw.rect(screen, crypto_colors_list[i], (bar_start_x, y_position, bar_length, 20))
                draw_text(f"{value}$", small_font, colors["BLACK"], bar_start_x + MAX_BAR_LENGTH + 10, y_position - 10)

        mouse_pos = pygame.mouse.get_pos()
        news_button = Button("News", screen.get_width() - 180, 10, colors["BLUE"], hover=pygame.Rect(screen.get_width() - 180, 10, 200, 50).collidepoint(mouse_pos))
        shop_button = Button("Shop", screen.get_width() - 180, 70, colors["YELLOW"], hover=pygame.Rect(screen.get_width() - 180, 70, 200, 50).collidepoint(mouse_pos))
        news_button_rect = news_button.draw()
        shop_button_rect = shop_button.draw()

        draw_text("Dein Kontostand:", font, colors["BLACK"], 50, screen.get_height() - 350)
        draw_text(f"Kontostand: {player.get('konto', 0)}$", small_font, colors["BLACK"], 50, screen.get_height() - 320)

        total_value = 0
        for i, stock in enumerate(NORMAL_STOCKS):
            qty = player.get(f"A{stock.lower()}", 0)
            value = qty * game_state["stocks"].get(stock, 0)
            total_value += value
            draw_text(f"{stock}: {qty} Aktien Wert: {value}$", small_font, colors["BLACK"], 50, screen.get_height() - 290 + i * 20)

        if player.get("krypto", False):
            for i, stock in enumerate(CRYPTO_STOCKS):
                qty = player.get(f"A{stock.lower()}", 0)
                value = qty * game_state["stocks"].get(stock, 0)
                total_value += value
                draw_text(f"{stock}: {qty} Aktien Wert: {value}$", small_font, colors["BLACK"], 50, screen.get_height() - 290 + (len(NORMAL_STOCKS) + i) * 20)

        crypto_count = len(CRYPTO_STOCKS) if player.get("krypto", False) else 0
        draw_text(f"Gesamtwert der Aktien: {total_value}$", small_font, colors["BLACK"], 50, screen.get_height() - 290 + (len(NORMAL_STOCKS) + crypto_count) * 20)

        # Stock selection labels
        stock_labels = {}
        crypto_stocks_list = list(CRYPTO_STOCKS) if player.get("krypto", False) else []
        all_stocks_selection = list(NORMAL_STOCKS) + crypto_stocks_list
        stocks_y = screen.get_height() - 240
        for i, stock in enumerate(all_stocks_selection):
            x = screen.get_width() - 420 if i < 4 else screen.get_width() - 210
            y = stocks_y + (i % 4) * 30
            stock_labels[stock] = draw_stock_label(stock, x, y, selected_stock == stock)

        # Quantity buttons
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

        is_my_turn = game_state["current_player"] == player_id

        # Card display
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
            card_color = colors["BLUE"] if is_my_turn else colors["GRAY"]
            card_button = Button("Karte ziehen", x_margin + (card_width // 2) - 100, y_margin + card_height + 20, card_color)
        else:
            card_color = colors["BLUE"] if is_my_turn else colors["GRAY"]
            card_button = Button("Karte ziehen", screen.get_width() // 2 - 100, screen.get_height() // 2 + 50, card_color)
            if current_round >= max_rounds:
                draw_text("Sie befinden sich in der letzten Runde. Gehen Sie in den Shop, um weitere Runden zu kaufen", font, colors["RED"], screen.get_width() // 2 - 300, screen.get_height() // 2 - 80)

        if not is_my_turn:
            draw_text(f"KI ({game_state['current_player']}) ist am Zug ...", font, colors["RED"],
                      screen.get_width() // 2 - 120, screen.get_height() // 2 - 20)

        # Pulse animation for active player
        if is_my_turn and not game_state["drawn_values"]:
            pulse_size += pulse_direction * PULSE_SPEED
            if pulse_size >= MAX_PULSE_SIZE or pulse_size <= 0:
                pulse_direction *= -1
            pulse_rect = pygame.Rect(card_button.x - pulse_size, card_button.y - pulse_size,
                                     card_button.width + 2 * pulse_size, card_button.height + 2 * pulse_size)
            pygame.draw.rect(screen, colors["YELLOW"], pulse_rect, 4, border_radius=15)

        card_button_rect = card_button.draw()

        if current_round >= max_rounds:
            end_button = Button("Beenden", screen.get_width() // 2 - 100, screen.get_height() - 60, colors["ORANGE"])
            end_button_rect = end_button.draw()
        else:
            end_button_rect = None

        # Chat display
        chat_y = screen.get_height() - 100
        with lock:
            history = game_state.get("chat_history", [])[-10:]

        for i, msg in enumerate(history):
            player_name = msg["player"]
            text = f"{player_name}: {msg['message']}"
            alpha = 255
            if not chat_active:
                time_since_msg = time.time() - msg["timestamp"]
                if time_since_msg > CHAT_FADE_END:
                    continue
                elif time_since_msg > CHAT_FADE_START:
                    alpha = int(255 * (CHAT_FADE_END - time_since_msg))

            text_surface = chat_font.render(text, True, colors["WHITE"])
            text_width = text_surface.get_width()
            x = (screen.get_width() - text_width) // 2
            y = chat_y - (len(history) - i) * 25

            bg_surface = pygame.Surface((text_surface.get_width() + 10, 25), pygame.SRCALPHA)
            bg_surface.fill((0, 0, 0, int(alpha * 0.7)))
            screen.blit(bg_surface, (x - 5, y))
            text_surface.set_alpha(alpha)
            screen.blit(text_surface, (x, y + 2))

        # Chat input
        if chat_active:
            input_text = "> " + chat_input_text + "|"
            input_surface = chat_font.render(input_text, True, colors["WHITE"])
            input_rect = pygame.Rect(10, screen.get_height() - 30, screen.get_width() - 20, 30)
            pygame.draw.rect(screen, (0, 0, 0, 180), input_rect, 0)
            screen.blit(input_surface, (15, screen.get_height() - 28))

        if persistent_error_message:
            draw_text(persistent_error_message, pygame.font.Font(None, 36), colors["RED"], screen.get_width() // 2 - 200, card_button_rect.y + 70)
        if save_message:
            draw_text(save_message, pygame.font.Font(None, 36), colors["BLACK"], screen.get_width() // 2 - 200, screen.get_height() // 2)

        pygame.display.flip()
        clock.tick(FPS)

    client.close()
    if is_host:
        server_running = False
    return True
