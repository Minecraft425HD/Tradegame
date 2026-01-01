"""
Rate Limiting System für Tradegame
Schutz vor Spam und DoS-Attacken
"""

import time
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, List
from threading import Lock
from enum import Enum

logger = logging.getLogger(__name__)


class RateLimitAction(Enum):
    """Kategorien von Rate-Limited Aktionen"""
    TRADE = "trade"
    CHAT = "chat"
    DRAW_CARD = "draw_card"
    CONNECTION = "connection"
    LOGIN = "login"
    GENERAL = "general"


@dataclass
class RateLimitConfig:
    """Konfiguration für ein Rate Limit"""
    max_requests: int  # Maximale Anfragen
    window_seconds: float  # Zeitfenster in Sekunden
    block_duration: float = 60.0  # Sperrzeit bei Überschreitung
    burst_allowance: int = 0  # Zusätzliche Burst-Anfragen erlaubt


# Standard-Limits pro Aktion
DEFAULT_LIMITS: Dict[RateLimitAction, RateLimitConfig] = {
    RateLimitAction.TRADE: RateLimitConfig(
        max_requests=10,  # 10 Trades
        window_seconds=60,  # pro Minute
        block_duration=30
    ),
    RateLimitAction.CHAT: RateLimitConfig(
        max_requests=5,  # 5 Nachrichten
        window_seconds=10,  # pro 10 Sekunden
        block_duration=60,
        burst_allowance=3
    ),
    RateLimitAction.DRAW_CARD: RateLimitConfig(
        max_requests=2,  # 2 Karten
        window_seconds=5,  # pro 5 Sekunden
        block_duration=10
    ),
    RateLimitAction.CONNECTION: RateLimitConfig(
        max_requests=5,  # 5 Verbindungen
        window_seconds=60,  # pro Minute
        block_duration=300  # 5 Minuten Sperre
    ),
    RateLimitAction.LOGIN: RateLimitConfig(
        max_requests=5,  # 5 Login-Versuche
        window_seconds=300,  # pro 5 Minuten
        block_duration=900  # 15 Minuten Sperre
    ),
    RateLimitAction.GENERAL: RateLimitConfig(
        max_requests=100,  # 100 Anfragen
        window_seconds=60,  # pro Minute
        block_duration=60
    ),
}


@dataclass
class RateLimitEntry:
    """Ein Eintrag im Rate Limiter"""
    requests: List[float] = field(default_factory=list)
    blocked_until: float = 0
    total_blocked_count: int = 0


class RateLimiter:
    """Token Bucket Rate Limiter mit Sliding Window"""

    def __init__(self, custom_limits: Dict[RateLimitAction, RateLimitConfig] = None):
        self.limits = DEFAULT_LIMITS.copy()
        if custom_limits:
            self.limits.update(custom_limits)

        # Entries pro Client und Aktion
        self._entries: Dict[str, Dict[RateLimitAction, RateLimitEntry]] = defaultdict(
            lambda: defaultdict(RateLimitEntry)
        )
        self._lock = Lock()

        # Statistiken
        self.total_requests = 0
        self.total_blocked = 0
        self.blocked_clients: Dict[str, int] = defaultdict(int)

    def _get_entry(self, client_id: str, action: RateLimitAction) -> RateLimitEntry:
        """Gibt den Entry für einen Client und Aktion zurück"""
        return self._entries[client_id][action]

    def _cleanup_old_requests(self, entry: RateLimitEntry, window: float):
        """Entfernt alte Anfragen außerhalb des Zeitfensters"""
        cutoff = time.time() - window
        entry.requests = [t for t in entry.requests if t > cutoff]

    def check(self, client_id: str, action: RateLimitAction = RateLimitAction.GENERAL) -> Tuple[bool, str]:
        """
        Prüft ob eine Anfrage erlaubt ist
        Returns: (erlaubt, error_message)
        """
        with self._lock:
            self.total_requests += 1

            config = self.limits.get(action, self.limits[RateLimitAction.GENERAL])
            entry = self._get_entry(client_id, action)
            current_time = time.time()

            # Ist Client blockiert?
            if entry.blocked_until > current_time:
                remaining = int(entry.blocked_until - current_time)
                self.total_blocked += 1
                return False, f"Rate limit erreicht. Warte {remaining} Sekunden."

            # Alte Anfragen entfernen
            self._cleanup_old_requests(entry, config.window_seconds)

            # Limit prüfen (mit Burst-Allowance)
            max_allowed = config.max_requests + config.burst_allowance
            if len(entry.requests) >= max_allowed:
                # Blockieren
                entry.blocked_until = current_time + config.block_duration
                entry.total_blocked_count += 1
                self.total_blocked += 1
                self.blocked_clients[client_id] += 1

                logger.warning(
                    f"Rate limit überschritten: {client_id} für {action.value} "
                    f"(Block #{entry.total_blocked_count})"
                )

                return False, f"Zu viele Anfragen. Warte {int(config.block_duration)} Sekunden."

            # Anfrage erlauben und registrieren
            entry.requests.append(current_time)
            return True, ""

    def check_and_consume(self, client_id: str,
                          action: RateLimitAction = RateLimitAction.GENERAL) -> bool:
        """Prüft und konsumiert ein Token (Kurzform)"""
        allowed, _ = self.check(client_id, action)
        return allowed

    def get_remaining(self, client_id: str,
                      action: RateLimitAction = RateLimitAction.GENERAL) -> Tuple[int, float]:
        """
        Gibt verbleibende Anfragen und Zeit bis Reset zurück
        Returns: (remaining_requests, seconds_until_reset)
        """
        with self._lock:
            config = self.limits.get(action, self.limits[RateLimitAction.GENERAL])
            entry = self._get_entry(client_id, action)

            self._cleanup_old_requests(entry, config.window_seconds)

            remaining = max(0, config.max_requests - len(entry.requests))

            if entry.requests:
                oldest = min(entry.requests)
                reset_in = max(0, oldest + config.window_seconds - time.time())
            else:
                reset_in = 0

            return remaining, reset_in

    def is_blocked(self, client_id: str,
                   action: RateLimitAction = RateLimitAction.GENERAL) -> bool:
        """Prüft ob ein Client blockiert ist"""
        entry = self._get_entry(client_id, action)
        return entry.blocked_until > time.time()

    def unblock(self, client_id: str, action: RateLimitAction = None):
        """Hebt eine Blockierung auf"""
        with self._lock:
            if action:
                entry = self._get_entry(client_id, action)
                entry.blocked_until = 0
            else:
                # Alle Aktionen entsperren
                for act in RateLimitAction:
                    entry = self._get_entry(client_id, act)
                    entry.blocked_until = 0

            logger.info(f"Rate limit aufgehoben für {client_id}")

    def reset(self, client_id: str):
        """Setzt alle Limits für einen Client zurück"""
        with self._lock:
            if client_id in self._entries:
                del self._entries[client_id]

    def get_stats(self) -> Dict:
        """Gibt Statistiken zurück"""
        return {
            "total_requests": self.total_requests,
            "total_blocked": self.total_blocked,
            "block_rate": (self.total_blocked / self.total_requests * 100)
                         if self.total_requests > 0 else 0,
            "active_clients": len(self._entries),
            "top_blocked_clients": dict(
                sorted(self.blocked_clients.items(), key=lambda x: x[1], reverse=True)[:10]
            )
        }

    def cleanup(self):
        """Entfernt alte Einträge"""
        with self._lock:
            current_time = time.time()
            cleanup_threshold = 3600  # 1 Stunde

            clients_to_remove = []
            for client_id, actions in self._entries.items():
                all_old = True
                for action, entry in actions.items():
                    config = self.limits.get(action, self.limits[RateLimitAction.GENERAL])
                    self._cleanup_old_requests(entry, config.window_seconds)

                    if entry.requests or entry.blocked_until > current_time:
                        all_old = False
                        break

                if all_old:
                    clients_to_remove.append(client_id)

            for client_id in clients_to_remove:
                del self._entries[client_id]

            if clients_to_remove:
                logger.debug(f"Rate limiter cleanup: {len(clients_to_remove)} Clients entfernt")


class IPRateLimiter:
    """Spezieller Rate Limiter für IP-Adressen"""

    def __init__(self):
        self.limiter = RateLimiter({
            RateLimitAction.CONNECTION: RateLimitConfig(
                max_requests=10,
                window_seconds=60,
                block_duration=600  # 10 Minuten
            )
        })
        self.banned_ips: Dict[str, float] = {}  # IP -> ban_until

    def check_connection(self, ip: str) -> Tuple[bool, str]:
        """Prüft ob eine IP verbinden darf"""
        # Permanent gebannt?
        if ip in self.banned_ips:
            if self.banned_ips[ip] == 0:  # Permanent
                return False, "IP ist permanent gesperrt"
            if self.banned_ips[ip] > time.time():
                remaining = int(self.banned_ips[ip] - time.time())
                return False, f"IP ist gesperrt für {remaining} Sekunden"
            else:
                del self.banned_ips[ip]

        return self.limiter.check(ip, RateLimitAction.CONNECTION)

    def ban_ip(self, ip: str, duration: float = 0):
        """
        Sperrt eine IP
        duration=0 bedeutet permanent
        """
        if duration > 0:
            self.banned_ips[ip] = time.time() + duration
        else:
            self.banned_ips[ip] = 0
        logger.warning(f"IP gebannt: {ip} (duration: {duration}s)")

    def unban_ip(self, ip: str):
        """Entsperrt eine IP"""
        if ip in self.banned_ips:
            del self.banned_ips[ip]
            logger.info(f"IP entsperrt: {ip}")


# Globale Instanzen
rate_limiter = RateLimiter()
ip_rate_limiter = IPRateLimiter()


# Decorator für Rate-Limited Funktionen
def rate_limited(action: RateLimitAction = RateLimitAction.GENERAL):
    """Decorator der Rate Limiting anwendet"""
    def decorator(func):
        def wrapper(client_id: str, *args, **kwargs):
            allowed, error = rate_limiter.check(client_id, action)
            if not allowed:
                raise RateLimitExceeded(error)
            return func(client_id, *args, **kwargs)
        return wrapper
    return decorator


class RateLimitExceeded(Exception):
    """Exception wenn Rate Limit überschritten"""
    pass


def check_rate_limit(client_id: str, action: str = "general") -> Tuple[bool, str]:
    """Kurzform für Rate-Limit-Check"""
    try:
        action_enum = RateLimitAction(action)
    except ValueError:
        action_enum = RateLimitAction.GENERAL

    return rate_limiter.check(client_id, action_enum)
