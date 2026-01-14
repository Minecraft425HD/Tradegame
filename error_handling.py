"""
Error Handling System für Tradegame
Zentrale Fehlerbehandlung und Logging
"""

import sys
import time
import traceback
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, List
from functools import wraps

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Schweregrad eines Fehlers"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Kategorie eines Fehlers"""
    NETWORK = "network"
    DATABASE = "database"
    GAME_LOGIC = "game_logic"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    FILE_IO = "file_io"
    UNKNOWN = "unknown"


@dataclass
class GameError(Exception):
    """Basis-Exception für alle Spielfehler"""
    message: str
    code: str = "UNKNOWN_ERROR"
    severity: ErrorSeverity = ErrorSeverity.ERROR
    category: ErrorCategory = ErrorCategory.UNKNOWN
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    recoverable: bool = True

    def __str__(self):
        return f"[{self.code}] {self.message}"

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "category": self.category.value,
            "details": self.details,
            "timestamp": self.timestamp,
            "recoverable": self.recoverable
        }


# Spezifische Fehler-Klassen
class NetworkError(GameError):
    """Netzwerkfehler"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            code="NETWORK_ERROR",
            category=ErrorCategory.NETWORK,
            **kwargs
        )


class ConnectionLostError(NetworkError):
    """Verbindung verloren"""
    def __init__(self, message: str = "Verbindung zum Server verloren", **kwargs):
        super().__init__(message, **kwargs)
        self.code = "CONNECTION_LOST"


class TimeoutError(NetworkError):
    """Zeitüberschreitung"""
    def __init__(self, message: str = "Zeitüberschreitung", **kwargs):
        super().__init__(message, **kwargs)
        self.code = "TIMEOUT"


class DatabaseError(GameError):
    """Datenbankfehler"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            category=ErrorCategory.DATABASE,
            **kwargs
        )


class ValidationError(GameError):
    """Validierungsfehler"""
    def __init__(self, message: str, field: str = "", **kwargs):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.WARNING,
            details={"field": field, **kwargs.get("details", {})},
            **{k: v for k, v in kwargs.items() if k != "details"}
        )


class AuthenticationError(GameError):
    """Authentifizierungsfehler"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            code="AUTH_ERROR",
            category=ErrorCategory.AUTHENTICATION,
            **kwargs
        )


class RateLimitError(GameError):
    """Rate Limit überschritten"""
    def __init__(self, message: str = "Zu viele Anfragen", retry_after: float = 60, **kwargs):
        super().__init__(
            message=message,
            code="RATE_LIMIT",
            category=ErrorCategory.RATE_LIMIT,
            severity=ErrorSeverity.WARNING,
            details={"retry_after": retry_after, **kwargs.get("details", {})},
            **{k: v for k, v in kwargs.items() if k != "details"}
        )


class InsufficientFundsError(GameError):
    """Nicht genug Geld"""
    def __init__(self, required: float, available: float, **kwargs):
        super().__init__(
            message=f"Nicht genug Geld. Benötigt: {required:.2f}€, Verfügbar: {available:.2f}€",
            code="INSUFFICIENT_FUNDS",
            category=ErrorCategory.GAME_LOGIC,
            severity=ErrorSeverity.WARNING,
            details={"required": required, "available": available},
            **kwargs
        )


class InsufficientSharesError(GameError):
    """Nicht genug Aktien"""
    def __init__(self, stock: str, required: int, available: int, **kwargs):
        super().__init__(
            message=f"Nicht genug {stock}-Aktien. Benötigt: {required}, Verfügbar: {available}",
            code="INSUFFICIENT_SHARES",
            category=ErrorCategory.GAME_LOGIC,
            severity=ErrorSeverity.WARNING,
            details={"stock": stock, "required": required, "available": available},
            **kwargs
        )


class GameStateError(GameError):
    """Ungültiger Spielzustand"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            code="GAME_STATE_ERROR",
            category=ErrorCategory.GAME_LOGIC,
            **kwargs
        )


class ErrorCollector:
    """Sammelt und verwaltet Fehler"""

    def __init__(self, max_errors: int = 1000):
        self.errors: List[GameError] = []
        self.max_errors = max_errors
        self.error_counts: Dict[str, int] = {}
        self.callbacks: List[Callable[[GameError], None]] = []

    def add(self, error: GameError):
        """Fügt einen Fehler hinzu"""
        self.errors.append(error)

        # Zähler aktualisieren
        self.error_counts[error.code] = self.error_counts.get(error.code, 0) + 1

        # Callbacks ausführen
        for callback in self.callbacks:
            try:
                callback(error)
            except Exception as e:
                logger.error(f"Error callback failed: {e}")

        # Log
        log_level = {
            ErrorSeverity.DEBUG: logging.DEBUG,
            ErrorSeverity.INFO: logging.INFO,
            ErrorSeverity.WARNING: logging.WARNING,
            ErrorSeverity.ERROR: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL,
        }.get(error.severity, logging.ERROR)

        logger.log(log_level, f"{error.code}: {error.message}")

        # Limit einhalten
        if len(self.errors) > self.max_errors:
            self.errors = self.errors[-self.max_errors:]

    def get_recent(self, count: int = 10) -> List[GameError]:
        """Gibt die letzten Fehler zurück"""
        return self.errors[-count:]

    def get_by_category(self, category: ErrorCategory) -> List[GameError]:
        """Gibt Fehler einer Kategorie zurück"""
        return [e for e in self.errors if e.category == category]

    def get_stats(self) -> Dict:
        """Gibt Fehlerstatistiken zurück"""
        return {
            "total": len(self.errors),
            "by_code": self.error_counts.copy(),
            "by_severity": {
                sev.value: len([e for e in self.errors if e.severity == sev])
                for sev in ErrorSeverity
            },
            "by_category": {
                cat.value: len([e for e in self.errors if e.category == cat])
                for cat in ErrorCategory
            }
        }

    def clear(self):
        """Löscht alle Fehler"""
        self.errors.clear()
        self.error_counts.clear()

    def register_callback(self, callback: Callable[[GameError], None]):
        """Registriert einen Callback für neue Fehler"""
        self.callbacks.append(callback)


# Globale Instanz
error_collector = ErrorCollector()


def handle_exception(error: Exception, context: str = "") -> GameError:
    """Konvertiert eine Exception zu einem GameError"""
    if isinstance(error, GameError):
        error_collector.add(error)
        return error

    # Traceback erfassen
    tb = traceback.format_exc()

    game_error = GameError(
        message=str(error),
        code="UNHANDLED_EXCEPTION",
        severity=ErrorSeverity.ERROR,
        category=ErrorCategory.UNKNOWN,
        details={
            "exception_type": type(error).__name__,
            "traceback": tb,
            "context": context
        },
        recoverable=False
    )

    error_collector.add(game_error)
    return game_error


def safe_execute(func: Callable, *args, default=None, context: str = "", **kwargs):
    """Führt eine Funktion sicher aus und fängt Fehler ab"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        handle_exception(e, context or func.__name__)
        return default


def error_handler(context: str = "", reraise: bool = False, default=None):
    """Decorator für Fehlerbehandlung"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except GameError as e:
                error_collector.add(e)
                if reraise:
                    raise
                return default
            except Exception as e:
                handle_exception(e, context or func.__name__)
                if reraise:
                    raise
                return default
        return wrapper
    return decorator


def create_error_response(error: GameError) -> Dict:
    """Erstellt eine Fehlerantwort für Clients"""
    return {
        "success": False,
        "error": {
            "code": error.code,
            "message": error.message,
            "recoverable": error.recoverable
        }
    }


def setup_global_exception_handler():
    """Richtet globalen Exception Handler ein"""
    def handler(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        error = GameError(
            message=str(exc_value),
            code="UNHANDLED_EXCEPTION",
            severity=ErrorSeverity.CRITICAL,
            details={
                "exception_type": exc_type.__name__,
                "traceback": ''.join(traceback.format_tb(exc_traceback))
            },
            recoverable=False
        )
        error_collector.add(error)
        logger.critical(f"Unhandled exception: {error}")

    sys.excepthook = handler


# Initialisierung
setup_global_exception_handler()
