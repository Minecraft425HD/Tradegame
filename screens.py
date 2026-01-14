import pygame
import sys
import time
import socket
import threading
import json
from config import colors, game_state, logging, server_running, lock, initial_variables, increment_state_version
from pygame_setup import clock, screen, fullscreen, native_width, native_height, background_image
from ui import draw_text, Button, draw_input_box
from server import start_server, register_ai_player, ai_players
from client import run_client
from network import receive_full_message
from game_logic import get_news_text
from constants import PORT, MAX_PLAYERS

# Import new systems
from sound_system import sound_system
from stock_charts import chart_system
from ai_player import AIPlayer, ai_manager
from highscores import highscore_system
from game_modes import game_mode_manager
from economy_system import dividend_system, loan_system, short_selling_system
from theme_system import theme_manager
from tutorial_system import tutorial_system
from avatar_system import avatar_manager
from pause_system import pause_system, PauseMenu
from lobby_system import lobby_manager, LobbyBrowser

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

    # Calculate final balance for highscore
    final_balance = player.get("konto", 0)
    is_winner = not player.get("lost", False)

    # Save to highscores
    highscore_system.add_score(
        player_name=player_id,
        final_balance=final_balance,
        rounds_played=game_state.get("round", 0),
        game_mode=game_mode_manager.get_mode().name if game_mode_manager.current_mode else "Klassisch",
        won=is_winner
    )

    # Play result sound
    if is_winner:
        sound_system.play("win")
    else:
        sound_system.play("lose")

    bg_color = theme_manager.get_color("background")
    text_color = theme_manager.get_color("text")

    screen.fill(bg_color)
    if player.get("lost", False):
        draw_text("VERLOREN", result_font, colors["RED"], screen.get_width() // 2 - 180, screen.get_height() // 2 - 50)
    else:
        draw_text("GEWONNEN!", result_font, colors["GREEN"], screen.get_width() // 2 - 200, screen.get_height() // 2 - 50)
    pygame.display.flip()
    pygame.time.wait(4000)

    while results_running:
        screen.fill(bg_color)
        draw_text("Spielergebnisse", title_font, text_color, screen.get_width() // 2 - 150, 40)

        y_offset = 100
        draw_text(f"Spieler {player_id} gegen {opponent_id}", font, text_color, 50, y_offset)
        y_offset += 40
        draw_text(f"Spielzeit: {minutes} Minuten {seconds} Sekunden", font, text_color, 50, y_offset)
        y_offset += 40
        draw_text(f"Endguthaben: {final_balance:,}$", font, colors["GREEN"] if is_winner else colors["RED"], 50, y_offset)
        y_offset += 40
        draw_text(f"Gekaufte Aktien/Kryptos: {player.get('bought_stocks', 0)}", font, text_color, 50, y_offset)
        y_offset += 40
        draw_text(f"Verkaufserlöse: {player.get('sold_money', 0):,}$", font, text_color, 50, y_offset)
        y_offset += 40
        draw_text(f"Verlorenes Geld: {player.get('lost_money', 0):,}$", font, text_color, 50, y_offset)
        y_offset += 40
        draw_text(f"Verlorene Aktien: {player.get('lost_stocks', 0)}", font, text_color, 50, y_offset)
        y_offset += 40
        draw_text(f"Netzwerkdaten: {mb_sent:.2f} MB gesendet, {mb_received:.2f} MB empfangen", font, text_color, 50, y_offset)

        # Check highscore ranking
        rank = highscore_system.get_rank(final_balance)
        if rank is not None and rank <= 10:
            y_offset += 50
            draw_text(f"Neuer Highscore! Platz {rank}", pygame.font.Font(None, 42), colors["YELLOW"], 50, y_offset)

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
                    sound_system.play("click")
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

    # Play menu music
    sound_system.play_music("menu_music.mp3")

    while menu_running:
        # Apply current theme
        bg_color = theme_manager.get_color("background")
        text_color = theme_manager.get_color("text")

        screen.fill(bg_color)
        draw_text("Multiplayer Börsenspiel", pygame.font.Font(None, 56), text_color, screen.get_width() // 2 - 200, 30)
        draw_text("Hauptmenü", pygame.font.Font(None, 42), text_color, screen.get_width() // 2 - 80, 80)

        mouse_pos = pygame.mouse.get_pos()

        # Menu buttons
        button_x = screen.get_width() // 2 - 100
        button_y_start = 140
        button_spacing = 55

        singleplayer_button = Button("Einzelspieler (KI)", button_x, button_y_start, colors["GREEN"],
                                     hover=pygame.Rect(button_x, button_y_start, 200, 50).collidepoint(mouse_pos))
        multiplayer_button = Button("Multiplayer", button_x, button_y_start + button_spacing, colors["BLUE"],
                                    hover=pygame.Rect(button_x, button_y_start + button_spacing, 200, 50).collidepoint(mouse_pos))
        highscores_button = Button("Bestenliste", button_x, button_y_start + button_spacing * 2, colors["YELLOW"],
                                   hover=pygame.Rect(button_x, button_y_start + button_spacing * 2, 200, 50).collidepoint(mouse_pos))
        tutorial_button = Button("Tutorial", button_x, button_y_start + button_spacing * 3, colors["PURPLE"] if "PURPLE" in colors else (128, 0, 128),
                                 hover=pygame.Rect(button_x, button_y_start + button_spacing * 3, 200, 50).collidepoint(mouse_pos))
        settings_button = Button("Einstellungen", button_x, button_y_start + button_spacing * 4, colors["ORANGE"],
                                 hover=pygame.Rect(button_x, button_y_start + button_spacing * 4, 200, 50).collidepoint(mouse_pos))
        quit_button = Button("Beenden", button_x, button_y_start + button_spacing * 5, colors["RED"],
                             hover=pygame.Rect(button_x, button_y_start + button_spacing * 5, 200, 50).collidepoint(mouse_pos))

        singleplayer_button_rect = singleplayer_button.draw()
        multiplayer_button_rect = multiplayer_button.draw()
        highscores_button_rect = highscores_button.draw()
        tutorial_button_rect = tutorial_button.draw()
        settings_button_rect = settings_button.draw()
        quit_button_rect = quit_button.draw()

        # Version info
        version_font = pygame.font.Font(None, 22)
        draw_text("v2.0 - Mit allen Features!", version_font, (150, 150, 150), 10, screen.get_height() - 25)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                menu_running = False
                server_running = False
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                sound_system.play("click")
                if quit_button_rect.collidepoint(event.pos):
                    menu_running = False
                    server_running = False
                    pygame.quit()
                    sys.exit()
                elif singleplayer_button_rect.collidepoint(event.pos):
                    menu_running = False
                    show_singleplayer_menu()
                elif multiplayer_button_rect.collidepoint(event.pos):
                    menu_running = False
                    show_lobby_screen()
                elif highscores_button_rect.collidepoint(event.pos):
                    show_highscores_screen()
                elif tutorial_button_rect.collidepoint(event.pos):
                    show_tutorial_menu()
                elif settings_button_rect.collidepoint(event.pos):
                    show_main_settings_screen()

        pygame.display.flip()
        clock.tick(60)


def show_singleplayer_menu():
    """Show singleplayer mode selection menu."""
    global server_running
    menu_running = True
    selected_difficulty = "medium"
    selected_mode = "classic"

    difficulties = [
        ("easy", "Leicht", "KI macht oft Fehler"),
        ("medium", "Mittel", "Ausgewogene KI"),
        ("hard", "Schwer", "KI spielt optimal")
    ]

    modes = [
        ("classic", "Klassisch", "Standard Regeln"),
        ("target", "Zielvermögen", "Erster mit 5 Mio$ gewinnt"),
        ("survival", "Überleben", "Wer zuletzt pleite geht")
    ]

    while menu_running:
        bg_color = theme_manager.get_color("background")
        text_color = theme_manager.get_color("text")

        screen.fill(bg_color)
        draw_text("Einzelspieler", pygame.font.Font(None, 48), text_color, screen.get_width() // 2 - 100, 30)

        mouse_pos = pygame.mouse.get_pos()

        # Difficulty selection
        draw_text("Schwierigkeit:", pygame.font.Font(None, 32), text_color, 100, 100)
        diff_buttons = []
        for i, (diff_id, diff_name, diff_desc) in enumerate(difficulties):
            is_selected = diff_id == selected_difficulty
            color = colors["GREEN"] if is_selected else colors["GRAY"]
            btn = Button(diff_name, 100 + i * 150, 140, color)
            rect = btn.draw()
            diff_buttons.append((rect, diff_id))
            # Description
            desc_font = pygame.font.Font(None, 20)
            draw_text(diff_desc, desc_font, (150, 150, 150), 100 + i * 150, 195)

        # Mode selection
        draw_text("Spielmodus:", pygame.font.Font(None, 32), text_color, 100, 240)
        mode_buttons = []
        for i, (mode_id, mode_name, mode_desc) in enumerate(modes):
            is_selected = mode_id == selected_mode
            color = colors["BLUE"] if is_selected else colors["GRAY"]
            btn = Button(mode_name, 100 + i * 180, 280, color)
            rect = btn.draw()
            mode_buttons.append((rect, mode_id))
            # Description
            desc_font = pygame.font.Font(None, 20)
            draw_text(mode_desc, desc_font, (150, 150, 150), 100 + i * 180, 335)

        # Start and Back buttons
        start_button = Button("Spiel starten", screen.get_width() // 2 - 100, 400, colors["GREEN"],
                             hover=pygame.Rect(screen.get_width() // 2 - 100, 400, 200, 50).collidepoint(mouse_pos))
        back_button = Button("Zurück", screen.get_width() // 2 - 100, 470, colors["ORANGE"],
                            hover=pygame.Rect(screen.get_width() // 2 - 100, 470, 200, 50).collidepoint(mouse_pos))

        start_rect = start_button.draw()
        back_rect = back_button.draw()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                sound_system.play("click")
                # Check difficulty buttons
                for rect, diff_id in diff_buttons:
                    if rect.collidepoint(event.pos):
                        selected_difficulty = diff_id
                # Check mode buttons
                for rect, mode_id in mode_buttons:
                    if rect.collidepoint(event.pos):
                        selected_mode = mode_id
                # Start game
                if start_rect.collidepoint(event.pos):
                    menu_running = False
                    start_singleplayer_game(selected_difficulty, selected_mode)
                elif back_rect.collidepoint(event.pos):
                    menu_running = False
                    show_main_menu()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    menu_running = False
                    show_main_menu()

        pygame.display.flip()
        clock.tick(60)


def start_singleplayer_game(difficulty, mode):
    """Start a singleplayer game against AI."""
    global server_running

    print(f"[DEBUG] Starting singleplayer: {difficulty}, {mode}")

    # Set game mode
    game_mode_manager.set_mode(mode)

    # Create AI player
    print("[DEBUG] Creating AI player...")
    ai_player = ai_manager.create_ai("KI_Gegner", difficulty)
    print(f"[DEBUG] AI player created")

    # Start local server
    try:
        # Start server in background
        print("[DEBUG] Starting server thread...")
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()

        # Wait for server to be ready
        print("[DEBUG] Waiting 1 second for server...")
        pygame.time.wait(1000)
        server_running = True
        print("[DEBUG] Server should be ready")

        # Register AI player with the server
        print("[DEBUG] Registering AI player...")
        register_ai_player("KI_Gegner", ai_player)

        # Add AI player to game_state
        print("[DEBUG] Adding AI to game_state...")
        with lock:
            ai_data = initial_variables.copy()
            ai_data["krypto"] = False
            ai_data["lost"] = False
            ai_data["game_over"] = False
            ai_data["bought_stocks"] = 0
            ai_data["sold_money"] = 0
            ai_data["lost_money"] = 0
            ai_data["lost_stocks"] = 0
            ai_data["bytes_sent"] = 0
            ai_data["bytes_received"] = 0
            ai_data["running"] = True
            ai_data["is_ai"] = True
            game_state["players"]["KI_Gegner"] = ai_data
            if game_state["start_time"] is None:
                game_state["start_time"] = time.time()
            increment_state_version()

        print("[DEBUG] AI added, starting client...")
        logging.info(f"Singleplayer started: {difficulty} difficulty, {mode} mode")

        # Start client for human player
        result = run_client("127.0.0.1", is_host=True, player_name="Spieler")
        print(f"[DEBUG] Client returned: {result}")

        # Return to main menu after game ends
        if result is False:
            print("[DEBUG] Client connection FAILED")
            logging.warning("Client connection failed, returning to main menu")

    except Exception as e:
        print(f"[DEBUG] EXCEPTION: {e}")
        logging.error(f"Failed to start singleplayer: {e}")
        import traceback
        traceback.print_exc()

    # Always return to main menu after singleplayer
    print("[DEBUG] Returning to main menu...")
    show_main_menu()


def show_highscores_screen():
    """Show the highscores screen."""
    running = True

    while running:
        bg_color = theme_manager.get_color("background")

        screen.fill(bg_color)

        # Draw highscore table
        highscore_system.draw_highscore_table(screen, 50, 50, screen.get_width() - 100, screen.get_height() - 150)

        # Back button
        back_button = Button("Zurück", screen.get_width() // 2 - 100, screen.get_height() - 80, colors["BLUE"])
        back_rect = back_button.draw()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if back_rect.collidepoint(event.pos):
                    sound_system.play("click")
                    running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        pygame.display.flip()
        clock.tick(60)


def show_tutorial_menu():
    """Show tutorial selection menu."""
    running = True
    tutorials = tutorial_system.get_available_tutorials()

    while running:
        bg_color = theme_manager.get_color("background")
        text_color = theme_manager.get_color("text")

        screen.fill(bg_color)
        draw_text("Tutorial auswählen", pygame.font.Font(None, 48), text_color, screen.get_width() // 2 - 150, 30)

        tutorial_buttons = []
        for i, tutorial in enumerate(tutorials):
            color = colors["GREEN"] if tutorial["completed"] else colors["BLUE"]
            status = " ✓" if tutorial["completed"] else ""
            btn = Button(f"{tutorial['name']}{status}", screen.get_width() // 2 - 100, 120 + i * 70, color)
            rect = btn.draw()
            tutorial_buttons.append((rect, tutorial["id"]))

        back_button = Button("Zurück", screen.get_width() // 2 - 100, screen.get_height() - 100, colors["ORANGE"])
        back_rect = back_button.draw()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                sound_system.play("click")
                for rect, tut_id in tutorial_buttons:
                    if rect.collidepoint(event.pos):
                        tutorial_system.start_tutorial(tut_id)
                        show_tutorial_screen()
                if back_rect.collidepoint(event.pos):
                    running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        pygame.display.flip()
        clock.tick(60)


def show_tutorial_screen():
    """Show active tutorial."""
    running = True

    while running and tutorial_system.is_tutorial_active():
        bg_color = theme_manager.get_color("background")
        screen.fill(bg_color)

        # Draw tutorial overlay
        button_rects = tutorial_system.draw_tutorial_overlay(screen, screen.get_width(), screen.get_height())

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if button_rects:
                    if button_rects.get("skip_rect") and button_rects["skip_rect"].collidepoint(event.pos):
                        sound_system.play("click")
                        tutorial_system.skip_tutorial()
                        running = False
                    elif button_rects.get("prev_rect") and button_rects["prev_rect"].collidepoint(event.pos):
                        sound_system.play("click")
                        tutorial_system.previous_step()
                    elif button_rects.get("next_rect") and button_rects["next_rect"].collidepoint(event.pos):
                        sound_system.play("click")
                        tutorial_system.next_step()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    tutorial_system.skip_tutorial()
                    running = False
                elif event.key == pygame.K_RIGHT or event.key == pygame.K_RETURN:
                    tutorial_system.next_step()
                elif event.key == pygame.K_LEFT:
                    tutorial_system.previous_step()

        pygame.display.flip()
        clock.tick(60)


def show_main_settings_screen():
    """Show main settings screen."""
    running = True

    while running:
        bg_color = theme_manager.get_color("background")
        text_color = theme_manager.get_color("text")

        screen.fill(bg_color)
        draw_text("Einstellungen", pygame.font.Font(None, 48), text_color, screen.get_width() // 2 - 100, 30)

        mouse_pos = pygame.mouse.get_pos()

        # Settings buttons
        button_x = screen.get_width() // 2 - 100

        # Sound settings
        sfx_status = "An" if sound_system.sfx_enabled else "Aus"
        music_status = "An" if sound_system.music_enabled else "Aus"

        sound_button = Button(f"Sound-Effekte: {sfx_status}", button_x, 120, colors["BLUE"],
                             hover=pygame.Rect(button_x, 120, 200, 50).collidepoint(mouse_pos))
        music_button = Button(f"Musik: {music_status}", button_x, 180, colors["BLUE"],
                             hover=pygame.Rect(button_x, 180, 200, 50).collidepoint(mouse_pos))

        # Theme settings
        current_theme = theme_manager.current_theme_name
        theme_button = Button(f"Theme: {current_theme.title()}", button_x, 240, colors["PURPLE"] if "PURPLE" in colors else (128, 0, 128),
                             hover=pygame.Rect(button_x, 240, 200, 50).collidepoint(mouse_pos))

        # Resolution
        resolution_button = Button("Auflösung", button_x, 300, colors["ORANGE"],
                                  hover=pygame.Rect(button_x, 300, 200, 50).collidepoint(mouse_pos))

        # Back
        back_button = Button("Zurück", button_x, 400, colors["GRAY"],
                            hover=pygame.Rect(button_x, 400, 200, 50).collidepoint(mouse_pos))

        sound_rect = sound_button.draw()
        music_rect = music_button.draw()
        theme_rect = theme_button.draw()
        resolution_rect = resolution_button.draw()
        back_rect = back_button.draw()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if sound_rect.collidepoint(event.pos):
                    sound_system.toggle_sfx()
                    sound_system.play("click")
                elif music_rect.collidepoint(event.pos):
                    sound_system.toggle_music()
                    sound_system.play("click")
                elif theme_rect.collidepoint(event.pos):
                    # Cycle through themes
                    themes = list(theme_manager.THEMES.keys())
                    current_idx = themes.index(theme_manager.current_theme_name)
                    next_idx = (current_idx + 1) % len(themes)
                    theme_manager.set_theme(themes[next_idx])
                    sound_system.play("click")
                elif resolution_rect.collidepoint(event.pos):
                    sound_system.play("click")
                    display_resolution_settings()
                elif back_rect.collidepoint(event.pos):
                    sound_system.play("click")
                    running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

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

def show_shop_screen(player_id, client, send_request):
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