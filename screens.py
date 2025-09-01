import pygame
import sys
import time
import socket
import threading
from config import colors, game_state, logging, server_running, lock
from pygame_setup import clock, screen, fullscreen, native_width, native_height, background_image
from ui import draw_text, Button, draw_input_box
from server import start_server
from client import run_client
from network import receive_full_message
from game_logic import get_news_text

def show_results_screen(player_id, client):
    results_running = True
    font = pygame.font.Font(None, 36)
    title_font = pygame.font.Font(None, 48)
    result_font = pygame.font.Font(None, 100)
   
    game_duration = int(time.time() - game_state["start_time"]) if game_state["start_time"] else 0
    minutes = game_duration // 60
    seconds = game_duration % 60
   
    players = list(game_state["players"].keys())
    opponent_id = [pid for pid in players if pid != player_id][0] if len(players) == 2 else "Mehrere Gegner"
    player = game_state["players"].get(player_id, {})
   
    mb_sent = player.get("bytes_sent", 0) / (1024 * 1024)
    mb_received = player.get("bytes_received", 0) / (1024 * 1024)
    screen.fill(colors["GRAY"])
    if player.get("lost", False):
        draw_text("LOSE", result_font, colors["BLACK"], screen.get_width() // 2 - 100, screen.get_height() // 2 - 50)
    else:
        draw_text("WIN", result_font, colors["GREEN"], screen.get_width() // 2 - 100, screen.get_height() // 2 - 50)
    pygame.display.flip()
    pygame.time.wait(4000)
    while results_running:
        screen.fill(colors["GRAY"])
        draw_text("Spielergebnisse", title_font, colors["BLACK"], screen.get_width() // 2 - 150, 40)
       
        y_offset = 100
        draw_text(f"Spieler {player_id} gegen {opponent_id}", font, colors["BLACK"], 50, y_offset)
        y_offset += 40
        draw_text(f"Spielzeit: {minutes} Minuten {seconds} Sekunden", font, colors["BLACK"], 50, y_offset)
        y_offset += 40
        draw_text(f"Gekaufte Aktien/Kryptos: {player.get('bought_stocks', 0)}", font, colors["BLACK"], 50, y_offset)
        y_offset += 40
        draw_text(f"Verkaufserlöse: {player.get('sold_money', 0)}$", font, colors["BLACK"], 50, y_offset)
        y_offset += 40
        draw_text(f"Verlorenes Geld: {player.get('lost_money', 0)}$", font, colors["BLACK"], 50, y_offset)
        y_offset += 40
        draw_text(f"Verlorene Aktien: {player.get('lost_stocks', 0)}", font, colors["BLACK"], 50, y_offset)
        y_offset += 40
        draw_text(f"Netzwerkdaten: {mb_sent:.2f} MB gesendet, {mb_received:.2f} MB empfangen", font, colors["BLACK"], 50, y_offset)
        back_button = Button("Zurück zum Hauptmenü", screen.get_width() // 2 - 100, screen.get_height() - 100, colors["BLUE"])
        back_button_rect = back_button.draw()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                results_running = False
                client.close()
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if back_button_rect.collidepoint(event.pos):
                    results_running = False
                    client.close()
                    show_main_menu()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    results_running = False
                    client.close()
                    show_main_menu()
        pygame.display.flip()
        clock.tick(60)

def show_lobby_screen():
    global screen, fullscreen, server_running
    lobby_running = True
    ip_input_text = "127.0.0.1"
    name_input_text = ""
    ip_active = False
    name_active = False
    lobby_players = []
    error_message = ""
    def update_lobby_players():
        nonlocal lobby_players, error_message
        if server_running:
            with lock:
                lobby_players = list(game_state["players"].keys())
        else:
            temp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                temp_client.settimeout(1)
                temp_client.connect((ip_input_text, PORT))
                data = receive_full_message(temp_client)
                if data:
                    temp_state = json.loads(data)
                    lobby_players = list(temp_state["game_state"]["players"].keys())
                else:
                    lobby_players = ["Kein Server aktiv"]
                error_message = ""
            except Exception as e:
                lobby_players = ["Kein Server aktiv"]
                error_message = f"Verbindung fehlgeschlagen: {e}"
                logging.error(f"Verbindung fehlgeschlagen in update_lobby_players: {e}")
            finally:
                temp_client.close()
    while lobby_running:
        screen.fill(colors["GRAY"])
        draw_text("Multiplayer Lobby", pygame.font.Font(None, 48), colors["BLACK"], screen.get_width() // 2 - 130, 40)
       
        mouse_pos = pygame.mouse.get_pos()
        host_button = Button("Host Game", screen.get_width() // 2 - 100, 180, colors["BLUE"], hover=pygame.Rect(screen.get_width() // 2 - 100, 180, 200, 50).collidepoint(mouse_pos))
        join_button = Button("Join Game", screen.get_width() // 2 - 100, 250, colors["YELLOW"], hover=pygame.Rect(screen.get_width() // 2 - 100, 250, 200, 50).collidepoint(mouse_pos))
        back_button = Button("Zurück", screen.get_width() // 2 - 100, 320, colors["ORANGE"], hover=pygame.Rect(screen.get_width() // 2 - 100, 320, 200, 50).collidepoint(mouse_pos))
       
        host_button_rect = host_button.draw()
        join_button_rect = join_button.draw()
        back_button_rect = back_button.draw()
        ip_input_box = draw_input_box(screen.get_width() // 2 - 100, 400, ip_input_text, ip_active)
        draw_text("Server IP:", pygame.font.Font(None, 36), colors["BLACK"], screen.get_width() // 2 - 100, 360)
        name_input_box = draw_input_box(screen.get_width() // 2 - 100, 470, name_input_text if name_input_text else "Dein Name", name_active)
        draw_text("Spielername:", pygame.font.Font(None, 36), colors["BLACK"], screen.get_width() // 2 - 100, 430)
        draw_text("Verbundene Spieler:", pygame.font.Font(None, 36), colors["BLACK"], screen.get_width() // 2 - 100, 540)
        for i, player in enumerate(lobby_players):
            draw_text(player, pygame.font.Font(None, 28), colors["BLACK"], screen.get_width() // 2 - 100, 580 + i * 30)
        if error_message:
            draw_text(error_message, pygame.font.Font(None, 36), colors["RED"], screen.get_width() // 2 - 150, screen.get_height() - 50)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                lobby_running = False
                server_running = False
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if ip_input_box.collidepoint(event.pos):
                    ip_active = True
                    name_active = False
                elif name_input_box.collidepoint(event.pos):
                    name_active = True
                    ip_active = False
                else:
                    ip_active = name_active = False
                if back_button_rect.collidepoint(event.pos):
                    lobby_running = False
                    server_running = False
                    show_main_menu()
                elif host_button_rect.collidepoint(event.pos) or join_button_rect.collidepoint(event.pos):
                    if not name_input_text:
                        error_message = "Bitte einen Namen eingeben!"
                    else:
                        if not server_running and host_button_rect.collidepoint(event.pos):
                            try:
                                threading.Thread(target=start_server, daemon=True).start()
                                pygame.time.wait(200)
                                logging.info("Serverstart initiiert")
                            except Exception as e:
                                error_message = f"Serverstart fehlgeschlagen: {e}"
                                logging.error(f"Serverstart fehlgeschlagen: {e}")
                                continue
                        success = run_client(ip_input_text, is_host=host_button_rect.collidepoint(event.pos), player_name=name_input_text)
                        if not success:
                            error_message = "Verbindung fehlgeschlagen!"
                            logging.error("Verbindung fehlgeschlagen in show_lobby_screen")
                        else:
                            lobby_running = False
            elif event.type == pygame.KEYDOWN:
                if ip_active:
                    if event.key == pygame.K_RETURN:
                        ip_active = False
                        update_lobby_players()
                    elif event.key == pygame.K_BACKSPACE:
                        ip_input_text = ip_input_text[:-1]
                    elif event.unicode.isalnum() or event.unicode == '.':
                        ip_input_text += event.unicode
                elif name_active:
                    if event.key == pygame.K_RETURN:
                        name_active = False
                    elif event.key == pygame.K_BACKSPACE:
                        name_input_text = name_input_text[:-1]
                    elif event.unicode.isalnum() or event.unicode in ['_','-']:
                        name_input_text += event.unicode
        if server_running and lobby_players != list(game_state["players"].keys()):
            update_lobby_players()
        pygame.display.flip()
        clock.tick(60)

def show_main_menu():
    global server_running
    menu_running = True
    while menu_running:
        screen.fill(colors["GRAY"])
        draw_text("Hauptmenü", pygame.font.Font(None, 48), colors["BLACK"], screen.get_width() // 2 - 110, 40)
       
        mouse_pos = pygame.mouse.get_pos()
        multiplayer_button = Button("Multiplayer", screen.get_width() // 2 - 100, 140, colors["BLUE"], hover=pygame.Rect(screen.get_width() // 2 - 100, 140, 200, 50).collidepoint(mouse_pos))
        quit_button = Button("Beenden", screen.get_width() // 2 - 100, 210, colors["ORANGE"], hover=pygame.Rect(screen.get_width() // 2 - 100, 210, 200, 50).collidepoint(mouse_pos))
       
        multiplayer_button_rect = multiplayer_button.draw()
        quit_button_rect = quit_button.draw()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                menu_running = False
                server_running = False
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if quit_button_rect.collidepoint(event.pos):
                    menu_running = False
                    server_running = False
                    pygame.quit()
                    sys.exit()
                elif multiplayer_button_rect.collidepoint(event.pos):
                    menu_running = False
                    show_lobby_screen()
        pygame.display.flip()
        clock.tick(60)

def show_news_screen(player_id, client):
    news_running = True
    while news_running:
        screen.fill(colors["GRAY"])
        draw_text("Zeitungsseite", pygame.font.Font(None, 48), colors["BLACK"], screen.get_width() // 2 - 110, 40)
        back_button = Button("Zurück", 50, 50, colors["BLUE"])
        back_button_rect = back_button.draw()
        y_offset = 140
        if game_state["last_event_text"]:
            draw_text(game_state["last_event_text"], pygame.font.Font(None, 24), colors["BLACK"], 100, y_offset)
            y_offset += 40
       
        for stock, value in game_state["drawn_values"].items():
            if value and value != "0":
                operator, val = value.split()
                val = int(val)
                change = val if operator == "+" else -val
                news_text = get_news_text(stock, change)
                draw_text(f"{news_text}", pygame.font.Font(None, 24), colors["BLACK"], 100, y_offset)
                y_offset += 40
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_state["players"][player_id]["running"] = False
                client.close()
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if back_button_rect.collidepoint(event.pos):
                    news_running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    news_running = False
        pygame.display.flip()
        clock.tick(60)

def show_shop_screen(player_id, client):
    shop_running = True
    player = game_state["players"].get(player_id, {})
    while shop_running:
        screen.fill(colors["WHITE"])
        draw_text("Shop", pygame.font.Font(None, 48), colors["BLACK"], screen.get_width() // 2 - 50, 40)
        back_button = Button("Zurück", 50, 50, colors["BLUE"])
        back_button_rect = back_button.draw()
        font = pygame.font.Font(None, 36)
        text_surface = font.render(f"Kaufe 10 Runden ({player.get('buy_rounds', 0)}$)", True, colors["WHITE"])
        text_width = text_surface.get_width() + 20
        buy_rounds_button_rect = pygame.Rect(screen.get_width() // 2 - text_width // 2, 200, text_width, 50)
        pygame.draw.rect(screen, colors["GREEN"], buy_rounds_button_rect, border_radius=15)
        screen.blit(text_surface, text_surface.get_rect(center=buy_rounds_button_rect.center))
        text_surface = font.render("Krypto Markt Freischalten (10000$)", True, colors["WHITE"])
        text_width = text_surface.get_width() + 20
        buy_crypto_button_rect = pygame.Rect(screen.get_width() // 2 - text_width // 2, 300, text_width, 50)
        pygame.draw.rect(screen, colors["GREEN"] if not player.get("krypto", False) else colors["GRAY"], buy_crypto_button_rect, border_radius=15)
        screen.blit(text_surface, text_surface.get_rect(center=buy_crypto_button_rect.center))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_state["players"][player_id]["running"] = False
                client.close()
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if back_button_rect.collidepoint(event.pos):
                    shop_running = False
                elif buy_rounds_button_rect.collidepoint(event.pos):
                    send_request("buy_rounds")
                elif buy_crypto_button_rect.collidepoint(event.pos) and not player.get("krypto", False):
                    send_request("unlock_crypto")
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    shop_running = False
        pygame.display.flip()
        clock.tick(60)

def display_resolution_settings():
    global screen, fullscreen
    resolution_running = True
    while resolution_running:
        screen.fill(colors["GRAY"])
        draw_text("Auflösung", pygame.font.Font(None, 48), colors["BLACK"], screen.get_width() // 2 - 110, 40)
        back_button = Button("Zurück", 50, 50, colors["BLUE"])
        back_button_rect = back_button.draw()
       
        a2560_1600_button = Button("2560x1600", screen.get_width() // 2 - 100, 210, colors["BLUE"])
        a1920_1080_button = Button("1920x1080", screen.get_width() // 2 - 100, 280, colors["BLUE"])
        a1280_720_button = Button("1280x720", screen.get_width() // 2 - 100, 350, colors["BLUE"])
        window_mode_button = Button("Fenstermodus" if not fullscreen else "Vollbildmodus", screen.get_width() // 2 - 100, 420, colors["BLUE"])
       
        a2560_1600_button_rect = a2560_1600_button.draw()
        a1920_1080_button_rect = a1920_1080_button.draw()
        a1280_720_button_rect = a1280_720_button.draw()
        window_mode_button_rect = window_mode_button.draw()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if back_button_rect.collidepoint(event.pos):
                    resolution_running = False
                elif a2560_1600_button_rect.collidepoint(event.pos):
                    screen = pygame.display.set_mode((2560, 1600), pygame.FULLSCREEN)
                    fullscreen = True
                elif a1920_1080_button_rect.collidepoint(event.pos):
                    screen = pygame.display.set_mode((1920, 1080), pygame.FULLSCREEN)
                    fullscreen = True
                elif a1280_720_button_rect.collidepoint(event.pos):
                    screen = pygame.display.set_mode((1280, 720), pygame.FULLSCREEN)
                    fullscreen = True
                elif window_mode_button_rect.collidepoint(event.pos):
                    fullscreen = not fullscreen
                    screen = pygame.display.set_mode((native_width, native_height), pygame.FULLSCREEN if fullscreen else pygame.RESIZABLE)
        pygame.display.flip()
        clock.tick(60)

def show_settings_screen(client, player_id):
    settings_running = True
    player = game_state["players"].get(player_id, {})
    while settings_running:
        if background_image:
            screen.blit(background_image, (0, 0))
        else:
            screen.fill(colors["GRAY"])
        draw_text("Einstellungen", pygame.font.Font(None, 48), colors["BLACK"], screen.get_width() // 2 - 110, 40)
        mouse_pos = pygame.mouse.get_pos()
        back_button = Button("Zurück", screen.get_width() // 2 - 100, 140, colors["BLUE"], hover=pygame.Rect(screen.get_width() // 2 - 100, 140, 200, 50).collidepoint(mouse_pos))
        quit_button = Button("Beenden", screen.get_width() // 2 - 100, 210, colors["ORANGE"], hover=pygame.Rect(screen.get_width() // 2 - 100, 210, 200, 50).collidepoint(mouse_pos))
        main_menu_button = Button("Hauptmenü", screen.get_width() // 2 - 100, 280, colors["RED"], hover=pygame.Rect(screen.get_width() // 2 - 100, 280, 200, 50).collidepoint(mouse_pos))
        resolution_button = Button("Auflösung", screen.get_width() // 2 - 100, 350, colors["RED"], hover=pygame.Rect(screen.get_width() // 2 - 100, 350, 200, 50).collidepoint(mouse_pos))
       
        back_button_rect = back_button.draw()
        quit_button_rect = quit_button.draw()
        main_menu_button_rect = main_menu_button.draw()
        resolution_button_rect = resolution_button.draw()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                player["running"] = False
                client.close()
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if back_button_rect.collidepoint(event.pos):
                    settings_running = False
                elif quit_button_rect.collidepoint(event.pos):
                    settings_running = False
                    player["running"] = False
                    client.close()
                    pygame.quit()
                    sys.exit()
                elif main_menu_button_rect.collidepoint(event.pos):
                    settings_running = False
                    client.close()
                    show_main_menu()
                elif resolution_button_rect.collidepoint(event.pos):
                    display_resolution_settings()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    settings_running = False
        pygame.display.flip()
        clock.tick(60)