"""
Logging-Konfiguration für Tradegame
Verbesserte Log-Rotation und strukturiertes Logging
"""

import os
import sys
import logging
import logging.handlers
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any
from config import get_path


# Log-Level Mapping
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}


class JSONFormatter(logging.Formatter):
    """JSON-Formatter für strukturiertes Logging"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Exception-Info hinzufügen wenn vorhanden
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Extra-Felder hinzufügen
        if hasattr(record, 'extra_data'):
            log_data["data"] = record.extra_data

        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """Farbiger Formatter für Terminal-Ausgabe"""

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Grün
        'WARNING': '\033[33m',   # Gelb
        'ERROR': '\033[31m',     # Rot
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


class GameLogFilter(logging.Filter):
    """Filter für spielspezifische Logs"""

    def __init__(self, include_modules: list = None, exclude_modules: list = None):
        super().__init__()
        self.include_modules = include_modules or []
        self.exclude_modules = exclude_modules or []

    def filter(self, record: logging.LogRecord) -> bool:
        if self.include_modules:
            return record.module in self.include_modules

        if self.exclude_modules:
            return record.module not in self.exclude_modules

        return True


def setup_logging(
    log_level: str = "INFO",
    log_file: str = None,
    max_bytes: int = 5 * 1024 * 1024,  # 5 MB
    backup_count: int = 5,
    json_format: bool = False,
    console_output: bool = True
) -> logging.Logger:
    """
    Konfiguriert das Logging-System

    Args:
        log_level: Minimaler Log-Level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Pfad zur Log-Datei (None = Standard)
        max_bytes: Maximale Größe pro Log-Datei
        backup_count: Anzahl der Backup-Dateien
        json_format: JSON-Format für Datei-Logs
        console_output: Ausgabe auf Konsole

    Returns:
        Root-Logger
    """
    # Log-Datei Pfad
    if log_file is None:
        log_file = get_path("game_log.txt")

    # Sicherstellen dass Verzeichnis existiert
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # Root-Logger konfigurieren
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVELS.get(log_level.upper(), logging.INFO))

    # Bestehende Handler entfernen
    root_logger.handlers.clear()

    # Datei-Handler mit Rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)  # Alles in Datei loggen

    if json_format:
        file_handler.setFormatter(JSONFormatter())
    else:
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))

    root_logger.addHandler(file_handler)

    # Konsolen-Handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(LOG_LEVELS.get(log_level.upper(), logging.INFO))

        # Farben nur wenn Terminal unterstützt
        if sys.stdout.isatty():
            console_handler.setFormatter(ColoredFormatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%H:%M:%S'
            ))
        else:
            console_handler.setFormatter(logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(message)s',
                datefmt='%H:%M:%S'
            ))

        root_logger.addHandler(console_handler)

    # Spezielle Logger für externe Bibliotheken dämpfen
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Gibt einen benannten Logger zurück"""
    return logging.getLogger(name)


class LogContext:
    """Kontext-Manager für strukturiertes Logging"""

    def __init__(self, logger: logging.Logger, operation: str, **kwargs):
        self.logger = logger
        self.operation = operation
        self.extra = kwargs
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        self.logger.debug(f"Starte: {self.operation}", extra={"extra_data": self.extra})
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time

        if exc_type:
            self.logger.error(
                f"Fehler bei: {self.operation} nach {duration:.3f}s",
                extra={"extra_data": {**self.extra, "duration": duration}},
                exc_info=True
            )
        else:
            self.logger.debug(
                f"Beendet: {self.operation} in {duration:.3f}s",
                extra={"extra_data": {**self.extra, "duration": duration}}
            )

        return False  # Exception nicht unterdrücken


def log_event(event_type: str, data: Dict[str, Any] = None, level: str = "INFO"):
    """
    Loggt ein strukturiertes Event

    Args:
        event_type: Art des Events (z.B. "trade", "login", "error")
        data: Zusätzliche Daten
        level: Log-Level
    """
    logger = logging.getLogger("events")
    log_func = getattr(logger, level.lower(), logger.info)

    message = f"[{event_type.upper()}]"
    if data:
        message += f" {json.dumps(data, ensure_ascii=False)}"

    log_func(message)


def cleanup_old_logs(log_dir: str = None, max_age_days: int = 30):
    """Entfernt alte Log-Dateien"""
    if log_dir is None:
        log_dir = os.path.dirname(get_path("game_log.txt"))

    if not os.path.exists(log_dir):
        return

    cutoff = time.time() - (max_age_days * 86400)
    removed = 0

    for filename in os.listdir(log_dir):
        if not filename.endswith('.txt') and not filename.endswith('.log'):
            continue

        filepath = os.path.join(log_dir, filename)
        if os.path.getmtime(filepath) < cutoff:
            try:
                os.remove(filepath)
                removed += 1
            except OSError:
                pass

    if removed > 0:
        logging.getLogger(__name__).info(f"Log-Cleanup: {removed} alte Dateien entfernt")


# Initialisierung beim Import
_initialized = False

def init_logging(level: str = "INFO"):
    """Initialisiert das Logging-System (einmalig)"""
    global _initialized
    if not _initialized:
        setup_logging(log_level=level)
        _initialized = True


# Automatische Initialisierung
init_logging()
