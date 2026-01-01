"""
Unit Tests für game_logic.py
"""

import unittest
import sys
import os

# Pfad zum Hauptverzeichnis hinzufügen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_logic import (
    buy_stock_multiplayer,
    sell_stock_multiplayer,
    apply_stock_changes,
    get_stock_key
)
from constants import MIN_STOCK_PRICE, MAX_STOCK_PRICE, STARTING_BALANCE


class TestStockKey(unittest.TestCase):
    """Tests für get_stock_key Funktion"""

    def test_stock_key_normal(self):
        """Test normale Aktien"""
        self.assertEqual(get_stock_key("Beyer"), "Abeyer")
        self.assertEqual(get_stock_key("BMW"), "Abmw")
        self.assertEqual(get_stock_key("BP"), "Abp")

    def test_stock_key_crypto(self):
        """Test Kryptowährungen"""
        self.assertEqual(get_stock_key("Bitcoin"), "Abitcoin")
        self.assertEqual(get_stock_key("Ethereum"), "Aethereum")

    def test_stock_key_case_insensitive(self):
        """Test Case-Insensitivität"""
        self.assertEqual(get_stock_key("BEYER"), "Abeyer")
        self.assertEqual(get_stock_key("beyer"), "Abeyer")


class TestBuyStock(unittest.TestCase):
    """Tests für buy_stock_multiplayer Funktion"""

    def setUp(self):
        """Test-Setup"""
        self.game_state = {
            "players": {
                "player_1": {
                    "konto": 100000,
                    "Abeyer": 0,
                    "Abmw": 10
                }
            },
            "stocks": {
                "Beyer": 100,
                "BMW": 150
            }
        }

    def test_buy_success(self):
        """Test erfolgreicher Kauf"""
        result = buy_stock_multiplayer(
            self.game_state, "player_1", "Beyer", 10
        )
        self.assertTrue(result)
        self.assertEqual(self.game_state["players"]["player_1"]["Abeyer"], 10)
        self.assertEqual(self.game_state["players"]["player_1"]["konto"], 99000)

    def test_buy_insufficient_funds(self):
        """Test Kauf ohne genug Geld"""
        self.game_state["players"]["player_1"]["konto"] = 500
        result = buy_stock_multiplayer(
            self.game_state, "player_1", "Beyer", 10
        )
        self.assertFalse(result)
        self.assertEqual(self.game_state["players"]["player_1"]["Abeyer"], 0)
        self.assertEqual(self.game_state["players"]["player_1"]["konto"], 500)

    def test_buy_invalid_quantity(self):
        """Test mit ungültiger Menge"""
        result = buy_stock_multiplayer(
            self.game_state, "player_1", "Beyer", 0
        )
        self.assertFalse(result)

        result = buy_stock_multiplayer(
            self.game_state, "player_1", "Beyer", -5
        )
        self.assertFalse(result)

    def test_buy_adds_to_existing(self):
        """Test Kauf addiert zu existierenden Aktien"""
        result = buy_stock_multiplayer(
            self.game_state, "player_1", "BMW", 5
        )
        self.assertTrue(result)
        self.assertEqual(self.game_state["players"]["player_1"]["Abmw"], 15)


class TestSellStock(unittest.TestCase):
    """Tests für sell_stock_multiplayer Funktion"""

    def setUp(self):
        """Test-Setup"""
        self.game_state = {
            "players": {
                "player_1": {
                    "konto": 50000,
                    "Abeyer": 20,
                    "Abmw": 0
                }
            },
            "stocks": {
                "Beyer": 100,
                "BMW": 150
            }
        }

    def test_sell_success(self):
        """Test erfolgreicher Verkauf"""
        result = sell_stock_multiplayer(
            self.game_state, "player_1", "Beyer", 10
        )
        self.assertTrue(result)
        self.assertEqual(self.game_state["players"]["player_1"]["Abeyer"], 10)
        self.assertEqual(self.game_state["players"]["player_1"]["konto"], 51000)

    def test_sell_all(self):
        """Test Verkauf aller Aktien"""
        result = sell_stock_multiplayer(
            self.game_state, "player_1", "Beyer", 20
        )
        self.assertTrue(result)
        self.assertEqual(self.game_state["players"]["player_1"]["Abeyer"], 0)
        self.assertEqual(self.game_state["players"]["player_1"]["konto"], 52000)

    def test_sell_insufficient_shares(self):
        """Test Verkauf ohne genug Aktien"""
        result = sell_stock_multiplayer(
            self.game_state, "player_1", "Beyer", 30
        )
        self.assertFalse(result)
        self.assertEqual(self.game_state["players"]["player_1"]["Abeyer"], 20)

    def test_sell_zero_shares(self):
        """Test Verkauf von Aktien die man nicht hat"""
        result = sell_stock_multiplayer(
            self.game_state, "player_1", "BMW", 5
        )
        self.assertFalse(result)


class TestApplyStockChanges(unittest.TestCase):
    """Tests für apply_stock_changes Funktion"""

    def setUp(self):
        """Test-Setup"""
        self.game_state = {
            "stocks": {
                "Beyer": 100,
                "BMW": 150,
                "BP": 50
            }
        }

    def test_apply_addition(self):
        """Test Addition"""
        changes = {"Beyer": "+ 20"}
        apply_stock_changes(self.game_state, changes)
        self.assertEqual(self.game_state["stocks"]["Beyer"], 120)

    def test_apply_subtraction(self):
        """Test Subtraktion"""
        changes = {"BMW": "- 30"}
        apply_stock_changes(self.game_state, changes)
        self.assertEqual(self.game_state["stocks"]["BMW"], 120)

    def test_apply_multiplication(self):
        """Test Multiplikation"""
        changes = {"BP": "* 2"}
        apply_stock_changes(self.game_state, changes)
        self.assertEqual(self.game_state["stocks"]["BP"], 100)

    def test_apply_division(self):
        """Test Division"""
        changes = {"Beyer": "/ 2"}
        apply_stock_changes(self.game_state, changes)
        self.assertEqual(self.game_state["stocks"]["Beyer"], 50)

    def test_price_bounds_max(self):
        """Test obere Preisgrenze"""
        self.game_state["stocks"]["Beyer"] = 200
        changes = {"Beyer": "+ 100"}
        apply_stock_changes(self.game_state, changes)
        self.assertLessEqual(self.game_state["stocks"]["Beyer"], MAX_STOCK_PRICE)

    def test_price_bounds_min(self):
        """Test untere Preisgrenze"""
        self.game_state["stocks"]["BP"] = 20
        changes = {"BP": "- 50"}
        apply_stock_changes(self.game_state, changes)
        self.assertGreaterEqual(self.game_state["stocks"]["BP"], MIN_STOCK_PRICE)


class TestPlayerValidation(unittest.TestCase):
    """Tests für Spieler-Validierung"""

    def test_invalid_player_id(self):
        """Test mit ungültiger Spieler-ID"""
        game_state = {
            "players": {"player_1": {"konto": 100000, "Abeyer": 0}},
            "stocks": {"Beyer": 100}
        }

        result = buy_stock_multiplayer(game_state, "invalid_player", "Beyer", 10)
        self.assertFalse(result)

    def test_invalid_stock_name(self):
        """Test mit ungültigem Aktiennamen"""
        game_state = {
            "players": {"player_1": {"konto": 100000}},
            "stocks": {"Beyer": 100}
        }

        result = buy_stock_multiplayer(game_state, "player_1", "InvalidStock", 10)
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
