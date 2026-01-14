"""
Validierungs-System für Tradegame
Zentrale Input-Validierung und Sanitization
"""

import re
import html
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Importiere Konstanten falls verfügbar
try:
    from constants import (
        MIN_STOCK_PRICE, MAX_STOCK_PRICE,
        MAX_SHARES_PER_TRADE, MAX_PLAYERS
    )
except ImportError:
    MIN_STOCK_PRICE = 10
    MAX_STOCK_PRICE = 250
    MAX_SHARES_PER_TRADE = 1000
    MAX_PLAYERS = 4


class ValidationError(Exception):
    """Validierungsfehler mit Details"""
    def __init__(self, message: str, field: str = "", code: str = ""):
        self.message = message
        self.field = field
        self.code = code
        super().__init__(message)


@dataclass
class ValidationResult:
    """Ergebnis einer Validierung"""
    is_valid: bool
    value: Any = None
    error: str = ""
    field: str = ""

    def __bool__(self):
        return self.is_valid


class Validator:
    """Basis-Validator mit wiederverwendbaren Methoden"""

    # Erlaubte Zeichen
    ALLOWED_USERNAME_CHARS = re.compile(r'^[a-zA-Z0-9_-]+$')
    ALLOWED_CHAT_CHARS = re.compile(r'^[\w\s.,!?@#$%&*()[\]{}<>:;\'"+=/-]+$', re.UNICODE)

    # Gefährliche Patterns
    DANGEROUS_PATTERNS = [
        r'<script',
        r'javascript:',
        r'on\w+\s*=',
        r'data:text/html',
        r'vbscript:',
    ]

    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000,
                        allow_html: bool = False) -> str:
        """Bereinigt einen String"""
        if not isinstance(value, str):
            value = str(value)

        # Länge begrenzen
        value = value[:max_length]

        # Whitespace normalisieren
        value = ' '.join(value.split())

        # HTML escapen wenn nicht erlaubt
        if not allow_html:
            value = html.escape(value)

        # Gefährliche Patterns entfernen
        for pattern in Validator.DANGEROUS_PATTERNS:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE)

        # Steuerzeichen entfernen (außer Newline, Tab)
        value = ''.join(char for char in value
                       if char.isprintable() or char in '\n\t')

        return value.strip()

    @staticmethod
    def validate_string(value: Any, min_length: int = 0, max_length: int = 1000,
                        pattern: Optional[re.Pattern] = None,
                        field_name: str = "Feld") -> ValidationResult:
        """Validiert einen String"""
        if value is None:
            return ValidationResult(False, None, f"{field_name} ist erforderlich", field_name)

        if not isinstance(value, str):
            try:
                value = str(value)
            except:
                return ValidationResult(False, None, f"{field_name} muss Text sein", field_name)

        value = Validator.sanitize_string(value, max_length)

        if len(value) < min_length:
            return ValidationResult(
                False, value,
                f"{field_name} muss mindestens {min_length} Zeichen haben",
                field_name
            )

        if len(value) > max_length:
            return ValidationResult(
                False, value,
                f"{field_name} darf maximal {max_length} Zeichen haben",
                field_name
            )

        if pattern and not pattern.match(value):
            return ValidationResult(
                False, value,
                f"{field_name} enthält ungültige Zeichen",
                field_name
            )

        return ValidationResult(True, value)

    @staticmethod
    def validate_integer(value: Any, min_value: int = None, max_value: int = None,
                         field_name: str = "Feld") -> ValidationResult:
        """Validiert eine Ganzzahl"""
        if value is None:
            return ValidationResult(False, None, f"{field_name} ist erforderlich", field_name)

        try:
            int_value = int(value)
        except (ValueError, TypeError):
            return ValidationResult(False, None, f"{field_name} muss eine Zahl sein", field_name)

        if min_value is not None and int_value < min_value:
            return ValidationResult(
                False, int_value,
                f"{field_name} muss mindestens {min_value} sein",
                field_name
            )

        if max_value is not None and int_value > max_value:
            return ValidationResult(
                False, int_value,
                f"{field_name} darf maximal {max_value} sein",
                field_name
            )

        return ValidationResult(True, int_value)

    @staticmethod
    def validate_float(value: Any, min_value: float = None, max_value: float = None,
                       field_name: str = "Feld") -> ValidationResult:
        """Validiert eine Dezimalzahl"""
        if value is None:
            return ValidationResult(False, None, f"{field_name} ist erforderlich", field_name)

        try:
            float_value = float(value)
        except (ValueError, TypeError):
            return ValidationResult(False, None, f"{field_name} muss eine Zahl sein", field_name)

        if min_value is not None and float_value < min_value:
            return ValidationResult(
                False, float_value,
                f"{field_name} muss mindestens {min_value} sein",
                field_name
            )

        if max_value is not None and float_value > max_value:
            return ValidationResult(
                False, float_value,
                f"{field_name} darf maximal {max_value} sein",
                field_name
            )

        return ValidationResult(True, float_value)

    @staticmethod
    def validate_boolean(value: Any, field_name: str = "Feld") -> ValidationResult:
        """Validiert einen Boolean"""
        if value is None:
            return ValidationResult(False, None, f"{field_name} ist erforderlich", field_name)

        if isinstance(value, bool):
            return ValidationResult(True, value)

        if isinstance(value, str):
            if value.lower() in ('true', '1', 'yes', 'ja'):
                return ValidationResult(True, True)
            if value.lower() in ('false', '0', 'no', 'nein'):
                return ValidationResult(True, False)

        if isinstance(value, (int, float)):
            return ValidationResult(True, bool(value))

        return ValidationResult(False, None, f"{field_name} muss ein Boolean sein", field_name)

    @staticmethod
    def validate_enum(value: Any, allowed_values: List[Any],
                      field_name: str = "Feld") -> ValidationResult:
        """Validiert gegen erlaubte Werte"""
        if value is None:
            return ValidationResult(False, None, f"{field_name} ist erforderlich", field_name)

        if value not in allowed_values:
            return ValidationResult(
                False, value,
                f"{field_name} muss einer von {allowed_values} sein",
                field_name
            )

        return ValidationResult(True, value)

    @staticmethod
    def validate_email(value: str, field_name: str = "E-Mail") -> ValidationResult:
        """Validiert eine E-Mail-Adresse"""
        result = Validator.validate_string(value, min_length=5, max_length=254, field_name=field_name)
        if not result:
            return result

        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )

        if not email_pattern.match(result.value):
            return ValidationResult(False, result.value, "Ungültige E-Mail-Adresse", field_name)

        return ValidationResult(True, result.value.lower())


class GameValidator:
    """Spiel-spezifische Validierung"""

    # Gültige Aktionen
    VALID_ACTIONS = ['buy', 'sell', 'draw_card', 'chat', 'set_name', 'heartbeat',
                     'ready', 'start_game', 'leave', 'kick']

    # Gültige Aktien
    VALID_STOCKS = ['Beyer', 'BMW', 'BP', 'Commerzbank',
                    'Bitcoin', 'Ethereum', 'Litecoin', 'Dogecoin']

    @classmethod
    def validate_action(cls, action: str) -> ValidationResult:
        """Validiert eine Spielaktion"""
        result = Validator.validate_string(action, min_length=1, max_length=50, field_name="Aktion")
        if not result:
            return result

        if result.value not in cls.VALID_ACTIONS:
            return ValidationResult(False, result.value, "Ungültige Aktion", "action")

        return result

    @classmethod
    def validate_stock(cls, stock: str) -> ValidationResult:
        """Validiert einen Aktiennamen"""
        result = Validator.validate_string(stock, min_length=1, max_length=50, field_name="Aktie")
        if not result:
            return result

        if result.value not in cls.VALID_STOCKS:
            return ValidationResult(False, result.value, "Unbekannte Aktie", "stock")

        return result

    @classmethod
    def validate_quantity(cls, quantity: Any, max_qty: int = None) -> ValidationResult:
        """Validiert eine Handels-Menge"""
        max_qty = max_qty or MAX_SHARES_PER_TRADE
        return Validator.validate_integer(
            quantity,
            min_value=1,
            max_value=max_qty,
            field_name="Menge"
        )

    @classmethod
    def validate_price(cls, price: Any) -> ValidationResult:
        """Validiert einen Aktienpreis"""
        return Validator.validate_float(
            price,
            min_value=MIN_STOCK_PRICE,
            max_value=MAX_STOCK_PRICE * 10,  # Etwas Spielraum für Crypto
            field_name="Preis"
        )

    @classmethod
    def validate_player_name(cls, name: str) -> ValidationResult:
        """Validiert einen Spielernamen"""
        result = Validator.validate_string(
            name,
            min_length=2,
            max_length=20,
            pattern=Validator.ALLOWED_USERNAME_CHARS,
            field_name="Spielername"
        )
        return result

    @classmethod
    def validate_chat_message(cls, message: str) -> ValidationResult:
        """Validiert eine Chat-Nachricht"""
        result = Validator.validate_string(
            message,
            min_length=1,
            max_length=500,
            field_name="Nachricht"
        )

        if not result:
            return result

        # Zusätzliche Filterung für Chat
        filtered = result.value

        # Spam-Erkennung: Zu viele Wiederholungen
        if re.search(r'(.)\1{10,}', filtered):
            return ValidationResult(False, filtered, "Nachricht enthält Spam", "message")

        return ValidationResult(True, filtered)

    @classmethod
    def validate_game_request(cls, data: Dict) -> Tuple[bool, Dict, List[str]]:
        """
        Validiert eine komplette Spielanfrage
        Returns: (is_valid, sanitized_data, errors)
        """
        errors = []
        sanitized = {}

        # Action (erforderlich)
        if 'action' not in data:
            errors.append("Aktion fehlt")
        else:
            result = cls.validate_action(data['action'])
            if result:
                sanitized['action'] = result.value
            else:
                errors.append(result.error)

        # Stock (optional)
        if 'stock' in data and data['stock']:
            result = cls.validate_stock(data['stock'])
            if result:
                sanitized['stock'] = result.value
            else:
                errors.append(result.error)

        # Quantity (optional)
        if 'quantity' in data and data['quantity'] is not None:
            result = cls.validate_quantity(data['quantity'])
            if result:
                sanitized['quantity'] = result.value
            else:
                errors.append(result.error)

        # Message (optional, für Chat)
        if 'message' in data and data['message']:
            result = cls.validate_chat_message(data['message'])
            if result:
                sanitized['message'] = result.value
            else:
                errors.append(result.error)

        # Name (optional)
        if 'name' in data and data['name']:
            result = cls.validate_player_name(data['name'])
            if result:
                sanitized['name'] = result.value
            else:
                errors.append(result.error)

        return len(errors) == 0, sanitized, errors

    @classmethod
    def validate_trade(cls, player_data: Dict, stock: str, quantity: int,
                       action: str, stock_price: float) -> ValidationResult:
        """
        Validiert einen kompletten Trade
        Prüft ob Spieler genug Geld/Aktien hat
        """
        if action == 'buy':
            total_cost = quantity * stock_price
            balance = player_data.get('konto', 0)

            if total_cost > balance:
                return ValidationResult(
                    False, None,
                    f"Nicht genug Geld. Kosten: {total_cost:.2f}€, Verfügbar: {balance:.2f}€",
                    "balance"
                )

        elif action == 'sell':
            # Stock-Key im Portfolio
            stock_key = f"A{stock.lower()}"
            owned = player_data.get(stock_key, 0)

            if quantity > owned:
                return ValidationResult(
                    False, None,
                    f"Nicht genug Aktien. Besitz: {owned}, Verkauf: {quantity}",
                    "shares"
                )

        return ValidationResult(True, {"stock": stock, "quantity": quantity, "action": action})


def validate_json_message(data: Any, max_size: int = 10000) -> Tuple[bool, Dict, str]:
    """
    Validiert eine eingehende JSON-Nachricht
    Returns: (is_valid, data, error_message)
    """
    if data is None:
        return False, {}, "Keine Daten empfangen"

    if not isinstance(data, dict):
        return False, {}, "Daten müssen ein Objekt sein"

    # Größe prüfen (serialisiert)
    try:
        import json
        serialized = json.dumps(data)
        if len(serialized) > max_size:
            return False, {}, f"Nachricht zu groß (max {max_size} Bytes)"
    except:
        return False, {}, "Ungültiges JSON-Format"

    return True, data, ""


# Shortcut-Funktionen
def sanitize(value: str, max_length: int = 1000) -> str:
    """Kurzform für String-Sanitization"""
    return Validator.sanitize_string(value, max_length)


def validate_request(data: Dict) -> Tuple[bool, Dict, List[str]]:
    """Kurzform für Request-Validierung"""
    return GameValidator.validate_game_request(data)
