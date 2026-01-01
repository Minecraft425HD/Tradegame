"""
Unit Tests für validation.py
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from validation import (
    Validator, GameValidator, ValidationResult,
    sanitize, validate_request
)


class TestValidator(unittest.TestCase):
    """Tests für Basis-Validator"""

    def test_sanitize_string_basic(self):
        """Test Basis-Sanitization"""
        result = Validator.sanitize_string("Hello World")
        self.assertEqual(result, "Hello World")

    def test_sanitize_string_html(self):
        """Test HTML-Escaping"""
        result = Validator.sanitize_string("<script>alert('xss')</script>")
        self.assertNotIn("<script>", result)
        self.assertNotIn("</script>", result)

    def test_sanitize_string_max_length(self):
        """Test Längenbegrenzung"""
        long_string = "a" * 2000
        result = Validator.sanitize_string(long_string, max_length=100)
        self.assertEqual(len(result), 100)

    def test_sanitize_string_whitespace(self):
        """Test Whitespace-Normalisierung"""
        result = Validator.sanitize_string("  Hello    World  ")
        self.assertEqual(result, "Hello World")

    def test_sanitize_string_control_chars(self):
        """Test Steuerzeichen-Entfernung"""
        result = Validator.sanitize_string("Hello\x00World\x1F")
        self.assertNotIn("\x00", result)
        self.assertNotIn("\x1f", result)

    def test_validate_string_min_length(self):
        """Test Mindestlänge"""
        result = Validator.validate_string("ab", min_length=3)
        self.assertFalse(result.is_valid)

        result = Validator.validate_string("abc", min_length=3)
        self.assertTrue(result.is_valid)

    def test_validate_string_max_length(self):
        """Test Maximallänge"""
        result = Validator.validate_string("abcdef", max_length=5)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.value), 5)

    def test_validate_integer_success(self):
        """Test Integer-Validierung erfolgreich"""
        result = Validator.validate_integer(42)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.value, 42)

    def test_validate_integer_string(self):
        """Test Integer aus String"""
        result = Validator.validate_integer("42")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.value, 42)

    def test_validate_integer_invalid(self):
        """Test ungültiger Integer"""
        result = Validator.validate_integer("abc")
        self.assertFalse(result.is_valid)

    def test_validate_integer_bounds(self):
        """Test Integer-Grenzen"""
        result = Validator.validate_integer(5, min_value=10)
        self.assertFalse(result.is_valid)

        result = Validator.validate_integer(15, max_value=10)
        self.assertFalse(result.is_valid)

        result = Validator.validate_integer(10, min_value=5, max_value=15)
        self.assertTrue(result.is_valid)

    def test_validate_float(self):
        """Test Float-Validierung"""
        result = Validator.validate_float(3.14)
        self.assertTrue(result.is_valid)
        self.assertAlmostEqual(result.value, 3.14)

    def test_validate_boolean(self):
        """Test Boolean-Validierung"""
        self.assertTrue(Validator.validate_boolean(True).value)
        self.assertFalse(Validator.validate_boolean(False).value)
        self.assertTrue(Validator.validate_boolean("true").value)
        self.assertFalse(Validator.validate_boolean("false").value)
        self.assertTrue(Validator.validate_boolean(1).value)
        self.assertFalse(Validator.validate_boolean(0).value)

    def test_validate_enum(self):
        """Test Enum-Validierung"""
        allowed = ["buy", "sell", "hold"]

        result = Validator.validate_enum("buy", allowed)
        self.assertTrue(result.is_valid)

        result = Validator.validate_enum("invalid", allowed)
        self.assertFalse(result.is_valid)

    def test_validate_email(self):
        """Test E-Mail-Validierung"""
        result = Validator.validate_email("test@example.com")
        self.assertTrue(result.is_valid)

        result = Validator.validate_email("invalid-email")
        self.assertFalse(result.is_valid)

        result = Validator.validate_email("@missing-local.com")
        self.assertFalse(result.is_valid)


class TestGameValidator(unittest.TestCase):
    """Tests für Spiel-spezifische Validierung"""

    def test_validate_action(self):
        """Test Aktions-Validierung"""
        valid_actions = ["buy", "sell", "draw_card", "chat", "heartbeat"]

        for action in valid_actions:
            result = GameValidator.validate_action(action)
            self.assertTrue(result.is_valid, f"Action {action} should be valid")

        result = GameValidator.validate_action("hack")
        self.assertFalse(result.is_valid)

    def test_validate_stock(self):
        """Test Aktien-Validierung"""
        valid_stocks = ["Beyer", "BMW", "BP", "Commerzbank", "Bitcoin"]

        for stock in valid_stocks:
            result = GameValidator.validate_stock(stock)
            self.assertTrue(result.is_valid, f"Stock {stock} should be valid")

        result = GameValidator.validate_stock("InvalidStock")
        self.assertFalse(result.is_valid)

    def test_validate_quantity(self):
        """Test Mengen-Validierung"""
        result = GameValidator.validate_quantity(10)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.value, 10)

        result = GameValidator.validate_quantity(0)
        self.assertFalse(result.is_valid)

        result = GameValidator.validate_quantity(-5)
        self.assertFalse(result.is_valid)

        result = GameValidator.validate_quantity(10000)
        self.assertFalse(result.is_valid)

    def test_validate_player_name(self):
        """Test Spielername-Validierung"""
        result = GameValidator.validate_player_name("Player1")
        self.assertTrue(result.is_valid)

        result = GameValidator.validate_player_name("Player_123")
        self.assertTrue(result.is_valid)

        result = GameValidator.validate_player_name("A")  # Zu kurz
        self.assertFalse(result.is_valid)

        result = GameValidator.validate_player_name("Player with spaces")
        self.assertFalse(result.is_valid)

    def test_validate_chat_message(self):
        """Test Chat-Nachricht-Validierung"""
        result = GameValidator.validate_chat_message("Hallo Welt!")
        self.assertTrue(result.is_valid)

        result = GameValidator.validate_chat_message("")  # Leer
        self.assertFalse(result.is_valid)

        # Spam-Test
        result = GameValidator.validate_chat_message("aaaaaaaaaaaaaaaa")
        self.assertFalse(result.is_valid)

    def test_validate_game_request_complete(self):
        """Test komplette Request-Validierung"""
        request = {
            "action": "buy",
            "stock": "Beyer",
            "quantity": 10
        }

        is_valid, sanitized, errors = GameValidator.validate_game_request(request)
        self.assertTrue(is_valid)
        self.assertEqual(sanitized["action"], "buy")
        self.assertEqual(sanitized["stock"], "Beyer")
        self.assertEqual(sanitized["quantity"], 10)

    def test_validate_game_request_missing_action(self):
        """Test Request ohne Action"""
        request = {
            "stock": "Beyer",
            "quantity": 10
        }

        is_valid, sanitized, errors = GameValidator.validate_game_request(request)
        self.assertFalse(is_valid)
        self.assertIn("Aktion fehlt", errors)

    def test_validate_game_request_invalid_data(self):
        """Test Request mit ungültigen Daten"""
        request = {
            "action": "invalid_action",
            "stock": "InvalidStock",
            "quantity": -5
        }

        is_valid, sanitized, errors = GameValidator.validate_game_request(request)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_validate_trade_buy_success(self):
        """Test Trade-Validierung: Kauf erfolgreich"""
        player_data = {"konto": 10000, "Abeyer": 0}

        result = GameValidator.validate_trade(
            player_data, "Beyer", 10, "buy", 100.0
        )
        self.assertTrue(result.is_valid)

    def test_validate_trade_buy_insufficient_funds(self):
        """Test Trade-Validierung: Kauf ohne Geld"""
        player_data = {"konto": 500, "Abeyer": 0}

        result = GameValidator.validate_trade(
            player_data, "Beyer", 10, "buy", 100.0
        )
        self.assertFalse(result.is_valid)
        self.assertIn("Geld", result.error)

    def test_validate_trade_sell_success(self):
        """Test Trade-Validierung: Verkauf erfolgreich"""
        player_data = {"konto": 1000, "Abeyer": 20}

        result = GameValidator.validate_trade(
            player_data, "Beyer", 10, "sell", 100.0
        )
        self.assertTrue(result.is_valid)

    def test_validate_trade_sell_insufficient_shares(self):
        """Test Trade-Validierung: Verkauf ohne Aktien"""
        player_data = {"konto": 1000, "Abeyer": 5}

        result = GameValidator.validate_trade(
            player_data, "Beyer", 10, "sell", 100.0
        )
        self.assertFalse(result.is_valid)
        self.assertIn("Aktien", result.error)


class TestShortcuts(unittest.TestCase):
    """Tests für Shortcut-Funktionen"""

    def test_sanitize_shortcut(self):
        """Test sanitize() Funktion"""
        result = sanitize("<script>test</script>")
        self.assertNotIn("<script>", result)

    def test_validate_request_shortcut(self):
        """Test validate_request() Funktion"""
        request = {"action": "buy", "stock": "Beyer", "quantity": 5}
        is_valid, _, _ = validate_request(request)
        self.assertTrue(is_valid)


if __name__ == '__main__':
    unittest.main()
