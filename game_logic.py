import random
from config import game_state, logging, ereigniskarten, news_data
from constants import (
    NORMAL_STOCKS, CRYPTO_STOCKS, MAX_STOCK_PRICE, MIN_STOCK_PRICE,
    STOCK_RESET_PRICE, STOCK_PENALTY_PER_SHARE, STOCK_MULTIPLIER_ON_OVERFLOW,
    EVENT_CARD_PROBABILITY, EVENT_CARD_RESET_COUNT, MIN_CARD_VALUE, MAX_CARD_VALUE,
    MULTIPLY_DIVIDE_VALUE, OPERATOR_ADD_COUNT, OPERATOR_SUB_COUNT,
    OPERATOR_MUL_COUNT, OPERATOR_DIV_COUNT, CRYPTO_UNLOCK_COST,
    ROUNDS_PER_PURCHASE, ROUND_PRICE_MULTIPLIER, MAX_GLOBAL_ROUNDS,
    BITCOIN_MIN_PRICE, BITCOIN_MAX_PRICE, ETHEREUM_MIN_PRICE, ETHEREUM_MAX_PRICE,
    LITECOIN_MIN_PRICE, LITECOIN_MAX_PRICE, DOGECOIN_MIN_PRICE, DOGECOIN_MAX_PRICE
)

def runde_auf_zehner(num):
    """Rounds a number to the nearest 10."""
    if num is None or not isinstance(num, (int, float)):
        return 0
    remainder = num % 10
    if remainder < 5:
        return int(num - remainder)
    else:
        return int(num + (10 - remainder))

def get_news_text(stock, change):
    """Gets a random news headline for a stock change."""
    if not news_data or stock not in news_data:
        if change > 0:
            return f"{stock} Aktie steigt um {change} Punkte!"
        else:
            return f"{stock} Aktie fällt um {abs(change)} Punkte!"

    try:
        key = "positive" if change > 0 else "negative"
        template = news_data[stock][key]
        if isinstance(template, list):
            template = random.choice(template)
        return template.format(change=abs(change))
    except (KeyError, ValueError) as e:
        logging.error(f"Fehler beim Generieren von News-Text: {e}")
        return f"{stock}: {'+' if change > 0 else ''}{change}"

def handle_negative_balance(player_id):
    """Handles players with negative balance - forces stock sale or marks as lost."""
    if player_id not in game_state.get("players", {}):
        logging.warning(f"handle_negative_balance: Spieler {player_id} nicht gefunden")
        return

    player = game_state["players"][player_id]

    if player.get("konto", 0) >= 0:
        return  # No negative balance, nothing to do

    # Calculate total stock value
    total_value = 0
    crypto_stocks = list(CRYPTO_STOCKS) if player.get("krypto", False) else []
    all_stocks = list(NORMAL_STOCKS) + crypto_stocks

    for stock in all_stocks:
        stock_key = f"A{stock.lower()}"
        qty = player.get(stock_key, 0)
        if qty > 0:
            value = qty * game_state["stocks"].get(stock, 0)
            total_value += value

    # Check if player is bankrupt
    if total_value + player["konto"] < 0:
        logging.info(f"Spieler {player_id} hat verloren: Kontostand {player['konto']}$ + Gesamtwert {total_value}$ < 0")
        print(f"Spieler {player_id} hat verloren: Kontostand {player['konto']}$ + Gesamtwert {total_value}$ < 0")
        player["lost"] = True

        # Mark game as over for 2-player games
        if len(game_state["players"]) == 2:
            for pid, p in game_state["players"].items():
                p["game_over"] = True
    else:
        # Force sell all stocks to cover negative balance
        for stock in all_stocks:
            stock_key = f"A{stock.lower()}"
            qty = player.get(stock_key, 0)
            if qty > 0:
                sale_value = qty * game_state["stocks"].get(stock, 0)
                player["konto"] = player.get("konto", 0) + sale_value
                player[stock_key] = 0
                player["sold_money"] = player.get("sold_money", 0) + sale_value

        logging.info(f"Spieler {player_id}: Alle Aktien verkauft, Neuer Kontostand: {player['konto']}$")
        print(f"Spieler {player_id}: Alle Aktien verkauft, Neuer Kontostand: {player['konto']}$")

def draw_card_multiplayer(player_id):
    """Draws a card for the player, applying stock changes."""
    if player_id not in game_state.get("players", {}):
        logging.error(f"draw_card_multiplayer: Spieler {player_id} nicht gefunden")
        return

    player = game_state["players"][player_id]

    # Check if player has rounds left
    current_round = player.get("game_round", 0)
    max_rounds = player.get("max_rounds", MAX_GLOBAL_ROUNDS)

    if current_round >= max_rounds:
        logging.info(f"Spieler {player_id} hat keine Runden mehr übrig")
        return

    # Increment round
    player["game_round"] = current_round + 1

    # Reset event card flag after cooldown
    if player.get("ereigniskarten_counter", 0) >= EVENT_CARD_RESET_COUNT:
        player["ereigniskarte_gezogen"] = False
        player["ereigniskarten_counter"] = 0

    player["ereigniskarten_counter"] = player.get("ereigniskarten_counter", 0) + 1

    # Setup operator probabilities
    operator_probabilities = (
        ["+"] * OPERATOR_ADD_COUNT +
        ["-"] * OPERATOR_SUB_COUNT +
        ["*"] * OPERATOR_MUL_COUNT +
        ["/"] * OPERATOR_DIV_COUNT
    )
    operator_limits = {"+": 2, "-": 2, "*": 1, "/": 1}

    # Initialize drawn values
    drawn_values = {stock: 0 for stock in NORMAL_STOCKS}
    game_state["drawn_values"] = drawn_values

    # Determine card type
    event_probability = player.get("event_card_probability", EVENT_CARD_PROBABILITY)
    if not player.get("ereigniskarte_gezogen", False) and random.random() < event_probability:
        card_type = 5  # Event card
        player["ereigniskarte_gezogen"] = True
    else:
        card_type = random.randint(1, 4)

    stocks = list(NORMAL_STOCKS)
    used_operators = {"+": 0, "-": 0, "*": 0, "/": 0}

    if card_type == 5:
        # Event card
        if ereigniskarten:
            ereigniskarte = random.choice(ereigniskarten)
            for stock in stocks:
                value = ereigniskarte.get(stock, 0)
                if value != 0:
                    operator = "+" if value > 0 else "-"
                    drawn_values[stock] = f"{operator} {abs(value)}"
            game_state["last_event_text"] = ereigniskarte.get("text", "Marktereignis!")
        else:
            game_state["last_event_text"] = "Keine Ereigniskarten verfügbar."
    else:
        # Regular card - affects 1-4 stocks
        num_stocks = card_type
        selected_stocks = random.sample(stocks, min(num_stocks, len(stocks)))

        for stock in selected_stocks:
            value = runde_auf_zehner(random.randint(MIN_CARD_VALUE, MAX_CARD_VALUE))
            while value == 0:
                value = runde_auf_zehner(random.randint(MIN_CARD_VALUE, MAX_CARD_VALUE))

            # Select operator respecting limits
            available_operators = [op for op in operator_probabilities if used_operators[op] < operator_limits[op]]
            if not available_operators:
                available_operators = ["+", "-"]

            operator = random.choice(available_operators)

            # Multiply/divide always uses fixed value
            if operator in ["*", "/"]:
                value = MULTIPLY_DIVIDE_VALUE

            drawn_values[stock] = f"{operator} {value}"
            used_operators[operator] += 1

        game_state["last_event_text"] = "Ein zufälliges Marktereignis beeinflusst die Kurse."

    # Apply stock changes
    for stock, operation in drawn_values.items():
        if isinstance(operation, str) and operation:
            try:
                parts = operation.split()
                if len(parts) != 2:
                    continue

                operator, value = parts
                value = int(value)
                old_value = game_state["stocks"].get(stock, 0)
                new_value = old_value

                if operator == "+":
                    new_value = old_value + value
                elif operator == "-":
                    new_value = old_value - value
                elif operator == "*":
                    new_value = runde_auf_zehner(old_value * value)
                elif operator == "/":
                    if value != 0:
                        new_value = runde_auf_zehner(old_value // value)

                # Handle overflow (stock price too high)
                if new_value > MAX_STOCK_PRICE:
                    excess = new_value - MAX_STOCK_PRICE
                    game_state["stocks"][stock] = STOCK_RESET_PRICE

                    # Bonus for shareholders
                    for pid, p in game_state["players"].items():
                        stock_key = f"A{stock.lower()}"
                        owned_shares = p.get(stock_key, 0)
                        if owned_shares > 0:
                            bonus = excess * owned_shares
                            p["konto"] = p.get("konto", 0) + bonus
                            p[stock_key] = owned_shares * STOCK_MULTIPLIER_ON_OVERFLOW
                            logging.info(f"Spieler {pid}: Bonus {bonus}$ für {stock}, Aktien verdoppelt")

                # Handle underflow (stock price too low)
                elif new_value < MIN_STOCK_PRICE:
                    game_state["stocks"][stock] = MIN_STOCK_PRICE

                    # Penalty for shareholders
                    for pid, p in game_state["players"].items():
                        stock_key = f"A{stock.lower()}"
                        owned_shares = p.get(stock_key, 0)
                        if owned_shares > 0:
                            penalty = owned_shares * STOCK_PENALTY_PER_SHARE
                            p["konto"] = p.get("konto", 0) - penalty
                            p["lost_money"] = p.get("lost_money", 0) + penalty
                            logging.info(f"Spieler {pid}: Penalty {penalty}$ für {stock}")

                else:
                    game_state["stocks"][stock] = new_value

            except (ValueError, IndexError) as e:
                logging.error(f"Fehler beim Verarbeiten der Operation {operation}: {e}")
                continue

    # Update crypto prices if player has crypto unlocked
    if player.get("krypto", False):
        krypto_ziehen_multiplayer()

    # Check all players for negative balance
    for pid in list(game_state["players"].keys()):
        handle_negative_balance(pid)

def krypto_ziehen_multiplayer():
    """Updates cryptocurrency prices with weighted random values."""
    # Bitcoin uses tiered random selection
    stufen = [
        (BITCOIN_MIN_PRICE, 10000),
        (10000, 20000),
        (20000, 30000),
        (30000, 40000),
        (40000, 50000),
        (50000, 60000),
        (60000, 70000),
        (70000, 80000),
        (80000, 90000),
        (90000, BITCOIN_MAX_PRICE)
    ]
    stufen_gewichte = [5] * 10

    # Select tier and randomize Bitcoin price
    for _ in range(3):  # Multiple selections for more variance
        stufe = random.choices(stufen, weights=stufen_gewichte, k=1)[0]
        game_state["stocks"]["Bitcoin"] = runde_auf_zehner(random.randint(stufe[0], stufe[1]))

    # Other crypto prices
    game_state["stocks"]["Ethereum"] = runde_auf_zehner(
        random.randint(ETHEREUM_MIN_PRICE, ETHEREUM_MAX_PRICE)
    )
    game_state["stocks"]["Litecoin"] = runde_auf_zehner(
        random.randint(LITECOIN_MIN_PRICE, LITECOIN_MAX_PRICE)
    )
    game_state["stocks"]["Dogecoin"] = runde_auf_zehner(
        random.randint(DOGECOIN_MIN_PRICE, DOGECOIN_MAX_PRICE)
    )

def buy_stock_multiplayer(player_id, stock, quantity):
    """Buys stocks for a player."""
    if player_id not in game_state.get("players", {}):
        logging.error(f"buy_stock_multiplayer: Spieler {player_id} nicht gefunden")
        return False

    if quantity <= 0:
        logging.warning(f"Ungültige Kaufmenge: {quantity}")
        return False

    if stock not in game_state.get("stocks", {}):
        logging.warning(f"Ungültige Aktie: {stock}")
        return False

    player = game_state["players"][player_id]
    stock_price = game_state["stocks"].get(stock, 0)
    cost = quantity * stock_price

    if player.get("konto", 0) >= cost:
        player["konto"] = player.get("konto", 0) - cost
        stock_key = f"A{stock.lower()}"
        player[stock_key] = player.get(stock_key, 0) + quantity
        player["bought_stocks"] = player.get("bought_stocks", 0) + quantity
        logging.info(f"Spieler {player_id} kauft {quantity}x {stock} für {cost}$")
        handle_negative_balance(player_id)
        return True
    else:
        logging.info(f"Spieler {player_id} hat nicht genug Geld für {quantity}x {stock}")
        return False

def sell_stock_multiplayer(player_id, stock, quantity):
    """Sells stocks for a player."""
    if player_id not in game_state.get("players", {}):
        logging.error(f"sell_stock_multiplayer: Spieler {player_id} nicht gefunden")
        return False

    if quantity <= 0:
        logging.warning(f"Ungültige Verkaufsmenge: {quantity}")
        return False

    if stock not in game_state.get("stocks", {}):
        logging.warning(f"Ungültige Aktie: {stock}")
        return False

    player = game_state["players"][player_id]
    stock_key = f"A{stock.lower()}"
    owned = player.get(stock_key, 0)

    if owned >= quantity:
        player[stock_key] = owned - quantity
        earnings = quantity * game_state["stocks"].get(stock, 0)
        player["konto"] = player.get("konto", 0) + earnings
        player["sold_money"] = player.get("sold_money", 0) + earnings
        logging.info(f"Spieler {player_id} verkauft {quantity}x {stock} für {earnings}$")
        handle_negative_balance(player_id)
        return True
    else:
        logging.info(f"Spieler {player_id} hat nicht genug {stock} Aktien ({owned} < {quantity})")
        return False

def buy_rounds_multiplayer(player_id):
    """Buys additional rounds for a player."""
    if player_id not in game_state.get("players", {}):
        logging.error(f"buy_rounds_multiplayer: Spieler {player_id} nicht gefunden")
        return False

    player = game_state["players"][player_id]
    cost = player.get("buy_rounds", 1000)

    if player.get("konto", 0) >= cost:
        player["konto"] = player.get("konto", 0) - cost
        player["lost_money"] = player.get("lost_money", 0) + cost
        player["buy_rounds"] = cost * ROUND_PRICE_MULTIPLIER
        player["max_rounds"] = player.get("max_rounds", MAX_GLOBAL_ROUNDS) + ROUNDS_PER_PURCHASE
        logging.info(f"Spieler {player_id} kauft {ROUNDS_PER_PURCHASE} Runden für {cost}$")
        handle_negative_balance(player_id)
        return True
    else:
        logging.info(f"Spieler {player_id} hat nicht genug Geld für Runden ({player.get('konto', 0)} < {cost})")
        return False

def unlock_crypto_multiplayer(player_id):
    """Unlocks cryptocurrency trading for a player."""
    if player_id not in game_state.get("players", {}):
        logging.error(f"unlock_crypto_multiplayer: Spieler {player_id} nicht gefunden")
        return False

    player = game_state["players"][player_id]

    if player.get("krypto", False):
        logging.info(f"Spieler {player_id} hat Krypto bereits freigeschaltet")
        return False

    if player.get("konto", 0) >= CRYPTO_UNLOCK_COST:
        player["konto"] = player.get("konto", 0) - CRYPTO_UNLOCK_COST
        player["lost_money"] = player.get("lost_money", 0) + CRYPTO_UNLOCK_COST
        player["krypto"] = True
        logging.info(f"Spieler {player_id} schaltet Krypto-Markt frei für {CRYPTO_UNLOCK_COST}$")
        handle_negative_balance(player_id)
        return True
    else:
        logging.info(f"Spieler {player_id} hat nicht genug Geld für Krypto ({player.get('konto', 0)} < {CRYPTO_UNLOCK_COST})")
        return False
