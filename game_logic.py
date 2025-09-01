import random
from config import game_state, logging, ereigniskarten, news_data

def runde_auf_zehner(num):
    remainder = num % 10
    if remainder < 5:
        return num - remainder
    else:
        return num + (10 - remainder)

def get_news_text(stock, change):
    if change > 0:
        return news_data[stock]["positive"].format(change=change)
    else:
        return news_data[stock]["negative"].format(change=abs(change))

def handle_negative_balance(player_id):
    player = game_state["players"].get(player_id, {})
    if player.get("konto", 0) < 0:
        total_value = 0
        normal_stocks = ["Beyer", "BMW", "BP", "Commerzbank"]
        crypto_stocks = ["Bitcoin", "Ethereum", "Litecoin", "Dogecoin"] if player.get("krypto", False) else []
        all_stocks = normal_stocks + crypto_stocks
        for stock in all_stocks:
            qty = player.get(f"A{stock.lower()}", 0)
            value = qty * game_state["stocks"].get(stock, 0)
            total_value += value
        if total_value + player["konto"] < 0:
            logging.info(f"Spieler {player_id} hat verloren: Kontostand {player['konto']}$ + Gesamtwert {total_value}$ < 0")
            print(f"Spieler {player_id} hat verloren: Kontostand {player['konto']}$ + Gesamtwert {total_value}$ < 0")
            player["lost"] = True
            if len(game_state["players"]) == 2:
                for pid, p in game_state["players"].items():
                    p["game_over"] = True
        else:
            for stock in all_stocks:
                qty = player.get(f"A{stock.lower()}", 0)
                if qty > 0:
                    player["konto"] += qty * game_state["stocks"].get(stock, 0)
                    player[f"A{stock.lower()}"] = 0
            logging.info(f"Spieler {player_id}: Alle Aktien verkauft, Neuer Kontostand: {player['konto']}$")
            print(f"Spieler {player_id}: Alle Aktien verkauft, Neuer Kontostand: {player['konto']}$")

def draw_card_multiplayer(player_id):
    player = game_state["players"].get(player_id, {})
    if player.get("game_round", 0) >= player.get("max_rounds", 50):
        return
    player["game_round"] = player.get("game_round", 0) + 1
    if player.get("ereigniskarten_counter", 0) >= 10:
        player["ereigniskarte_gezogen"] = False
        player["ereigniskarten_counter"] = 0
    player["ereigniskarten_counter"] = player.get("ereigniskarten_counter", 0) + 1
    operator_probabilities = ["+"] * 5 + ["-"] * 5 + ["*"] * 1 + ["/"] * 2
    operator_limits = {"+": 2, "-": 2, "*": 1, "/": 1}
    drawn_values = {"Beyer": 0, "BMW": 0, "BP": 0, "Commerzbank": 0}
    game_state["drawn_values"] = drawn_values
    if not player.get("ereigniskarte_gezogen", False) and random.random() < player.get("event_card_probability", 0.5):
        card_type = 5
        player["ereigniskarte_gezogen"] = True
    else:
        card_type = random.randint(1, 4)
    stocks = ["Beyer", "BMW", "BP", "Commerzbank"]
    used_operators = {"+": 0, "-": 0, "*": 0, "/": 0}
    if card_type == 5:
        ereigniskarte = random.choice(ereigniskarten)
        for stock in stocks:
            value = ereigniskarte.get(stock, 0)
            if value != 0:
                operator = "+" if value > 0 else "-"
                drawn_values[stock] = f"{operator} {abs(value)}"
        game_state["last_event_text"] = ereigniskarte["text"]
    else:
        num_stocks = card_type
        for stock in random.sample(stocks, num_stocks):
            value = runde_auf_zehner(random.randint(1, 50))
            while value == 0:
                value = runde_auf_zehner(random.randint(1, 50))
            operator = random.choice([op for op in operator_probabilities if used_operators[op] < operator_limits[op]])
            if operator in ["*", "/"]:
                value = 2
            drawn_values[stock] = f"{operator} {value}"
            used_operators[operator] += 1
        game_state["last_event_text"] = "Ein zufälliges Marktereignis beeinflusst die Kurse."
    for stock, operation in drawn_values.items():
        if isinstance(operation, str):
            operator, value = operation.split()
            value = int(value)
            old_value = game_state["stocks"].get(stock, 0)
            new_value = old_value
            if operator == "+":
                new_value += value
            elif operator == "-":
                new_value -= value
            elif operator == "*":
                new_value = runde_auf_zehner(old_value * value)
            elif operator == "/":
                new_value = runde_auf_zehner(old_value // value)
            if new_value > 250:
                excess = new_value - 250
                game_state["stocks"][stock] = 80
                for pid, p in game_state["players"].items():
                    owned_shares = p.get(f"A{stock.lower()}", 0)
                    if owned_shares > 0:
                        bonus = excess * owned_shares
                        p["konto"] = p.get("konto", 0) + bonus
                        p[f"A{stock.lower()}"] *= 2
            elif new_value < 10:
                game_state["stocks"][stock] = 10
                for pid, p in game_state["players"].items():
                    owned_shares = p.get(f"A{stock.lower()}", 0)
                    if owned_shares > 0:
                        penalty = owned_shares * -20
                        p["konto"] = p.get("konto", 0) + penalty
                        p["lost_money"] = p.get("lost_money", 0) + abs(penalty)
            else:
                game_state["stocks"][stock] = new_value
    if player.get("krypto", False):
        krypto_ziehen_multiplayer()
    for pid in list(game_state["players"].keys()):
        handle_negative_balance(pid)

def krypto_ziehen_multiplayer():
    stufen = [(1000, 10000), (10000, 20000), (20000, 30000), (30000, 40000), (40000, 50000),
              (50000, 60000), (60000, 70000), (70000, 80000), (80000, 90000), (90000, 100000)]
    stufen_gewichte = [5] * 10
    for _ in range(3):
        stufe = random.choices(stufen, weights=stufen_gewichte, k=1)[0]
        game_state["stocks"]["Bitcoin"] = runde_auf_zehner(random.randint(stufe[0], stufe[1]))
    game_state["stocks"]["Ethereum"] = runde_auf_zehner(random.randint(1000, 3000))
    game_state["stocks"]["Litecoin"] = runde_auf_zehner(random.randint(50, 100))
    game_state["stocks"]["Dogecoin"] = runde_auf_zehner(random.randint(10, 50))

def buy_stock_multiplayer(player_id, stock, quantity):
    player = game_state["players"].get(player_id, {})
    cost = quantity * game_state["stocks"].get(stock, 0)
    if player.get("konto", 0) >= cost:
        player["konto"] = player.get("konto", 0) - cost
        player[f"A{stock.lower()}"] = player.get(f"A{stock.lower()}", 0) + quantity
        player["bought_stocks"] = player.get("bought_stocks", 0) + quantity
    handle_negative_balance(player_id)

def sell_stock_multiplayer(player_id, stock, quantity):
    player = game_state["players"].get(player_id, {})
    if player.get(f"A{stock.lower()}", 0) >= quantity:
        player[f"A{stock.lower()}"] = player.get(f"A{stock.lower()}", 0) - quantity
        earnings = quantity * game_state["stocks"].get(stock, 0)
        player["konto"] = player.get("konto", 0) + earnings
        player["sold_money"] = player.get("sold_money", 0) + earnings
    handle_negative_balance(player_id)

def buy_rounds_multiplayer(player_id):
    player = game_state["players"].get(player_id, {})
    if player.get("konto", 0) >= player.get("buy_rounds", 0):
        player["konto"] = player.get("konto", 0) - player.get("buy_rounds", 0)
        player["lost_money"] = player.get("lost_money", 0) + player.get("buy_rounds", 0)
        player["buy_rounds"] = player.get("buy_rounds", 0) * 2
        player["max_rounds"] = player.get("max_rounds", 50) + 10
    handle_negative_balance(player_id)

def unlock_crypto_multiplayer(player_id):
    player = game_state["players"].get(player_id, {})
    if player.get("konto", 0) >= 10000 and not player.get("krypto", False):
        player["konto"] = player.get("konto", 0) - 10000
        player["lost_money"] = player.get("lost_money", 0) + 10000
        player["krypto"] = True
    handle_negative_balance(player_id)