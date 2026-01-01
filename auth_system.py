"""
Authentifizierungs-System für Tradegame
Token-basierte Authentifizierung mit Passwort-Hashing
"""

import hashlib
import secrets
import time
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from config import get_path

logger = logging.getLogger(__name__)


# Konstanten
TOKEN_EXPIRY_HOURS = 24
MIN_PASSWORD_LENGTH = 6
MAX_PASSWORD_LENGTH = 128
MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 20
SALT_LENGTH = 32
TOKEN_LENGTH = 64


@dataclass
class User:
    """Ein registrierter Benutzer"""
    user_id: str
    username: str
    password_hash: str
    salt: str
    created_at: float
    last_login: float = 0
    is_banned: bool = False
    ban_reason: str = ""
    ban_until: float = 0
    failed_login_attempts: int = 0
    last_failed_login: float = 0
    email: str = ""
    is_verified: bool = False

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "password_hash": self.password_hash,
            "salt": self.salt,
            "created_at": self.created_at,
            "last_login": self.last_login,
            "is_banned": self.is_banned,
            "ban_reason": self.ban_reason,
            "ban_until": self.ban_until,
            "failed_login_attempts": self.failed_login_attempts,
            "last_failed_login": self.last_failed_login,
            "email": self.email,
            "is_verified": self.is_verified
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        return cls(**data)

    def is_currently_banned(self) -> bool:
        """Prüft ob User aktuell gebannt ist"""
        if not self.is_banned:
            return False
        if self.ban_until == 0:  # Permanenter Ban
            return True
        return time.time() < self.ban_until


@dataclass
class Session:
    """Eine aktive Session"""
    token: str
    user_id: str
    created_at: float
    expires_at: float
    ip_address: str = ""
    user_agent: str = ""

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_dict(self) -> dict:
        return {
            "token": self.token,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Session':
        return cls(**data)


class AuthenticationError(Exception):
    """Basis-Exception für Auth-Fehler"""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Ungültige Anmeldedaten"""
    pass


class UserBannedError(AuthenticationError):
    """Benutzer ist gebannt"""
    pass


class UserExistsError(AuthenticationError):
    """Benutzername existiert bereits"""
    pass


class ValidationError(AuthenticationError):
    """Validierungsfehler"""
    pass


class AuthSystem:
    """Authentifizierungs-Manager"""

    # Lockout nach zu vielen Fehlversuchen
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION = 300  # 5 Minuten

    def __init__(self):
        self.users: Dict[str, User] = {}  # user_id -> User
        self.usernames: Dict[str, str] = {}  # username.lower() -> user_id
        self.sessions: Dict[str, Session] = {}  # token -> Session
        self.user_sessions: Dict[str, str] = {}  # user_id -> token
        self.data_file = get_path("data/users.json")
        self.user_counter = 0
        self.load_data()

    def load_data(self):
        """Lädt Benutzerdaten"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                self.user_counter = data.get("counter", 0)

                for user_data in data.get("users", []):
                    user = User.from_dict(user_data)
                    self.users[user.user_id] = user
                    self.usernames[user.username.lower()] = user.user_id

                for session_data in data.get("sessions", []):
                    session = Session.from_dict(session_data)
                    if not session.is_expired():
                        self.sessions[session.token] = session
                        self.user_sessions[session.user_id] = session.token

            logger.info(f"Auth: {len(self.users)} Benutzer geladen")
        except (FileNotFoundError, json.JSONDecodeError):
            logger.info("Auth: Keine Benutzerdaten gefunden, starte neu")

    def save_data(self):
        """Speichert Benutzerdaten"""
        try:
            data = {
                "counter": self.user_counter,
                "users": [u.to_dict() for u in self.users.values()],
                "sessions": [s.to_dict() for s in self.sessions.values() if not s.is_expired()]
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Auth: Fehler beim Speichern: {e}")

    def _hash_password(self, password: str, salt: str) -> str:
        """Hasht ein Passwort mit Salt (PBKDF2)"""
        return hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # Iterationen
        ).hex()

    def _generate_salt(self) -> str:
        """Generiert einen zufälligen Salt"""
        return secrets.token_hex(SALT_LENGTH)

    def _generate_token(self) -> str:
        """Generiert einen Session-Token"""
        return secrets.token_hex(TOKEN_LENGTH)

    def _validate_username(self, username: str) -> Tuple[bool, str]:
        """Validiert einen Benutzernamen"""
        if len(username) < MIN_USERNAME_LENGTH:
            return False, f"Benutzername muss mindestens {MIN_USERNAME_LENGTH} Zeichen haben"
        if len(username) > MAX_USERNAME_LENGTH:
            return False, f"Benutzername darf maximal {MAX_USERNAME_LENGTH} Zeichen haben"
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            return False, "Benutzername darf nur Buchstaben, Zahlen, _ und - enthalten"
        if username.lower() in ['admin', 'system', 'server', 'moderator', 'mod']:
            return False, "Dieser Benutzername ist reserviert"
        return True, ""

    def _validate_password(self, password: str) -> Tuple[bool, str]:
        """Validiert ein Passwort"""
        if len(password) < MIN_PASSWORD_LENGTH:
            return False, f"Passwort muss mindestens {MIN_PASSWORD_LENGTH} Zeichen haben"
        if len(password) > MAX_PASSWORD_LENGTH:
            return False, f"Passwort darf maximal {MAX_PASSWORD_LENGTH} Zeichen haben"
        # Optional: Komplexitätsanforderungen
        # if not re.search(r'[A-Z]', password):
        #     return False, "Passwort muss mindestens einen Großbuchstaben enthalten"
        # if not re.search(r'[0-9]', password):
        #     return False, "Passwort muss mindestens eine Zahl enthalten"
        return True, ""

    def register(self, username: str, password: str, email: str = "") -> Tuple[User, str]:
        """
        Registriert einen neuen Benutzer
        Returns: (User, token)
        Raises: UserExistsError, ValidationError
        """
        # Validierung
        valid, msg = self._validate_username(username)
        if not valid:
            raise ValidationError(msg)

        valid, msg = self._validate_password(password)
        if not valid:
            raise ValidationError(msg)

        # Existiert bereits?
        if username.lower() in self.usernames:
            raise UserExistsError("Benutzername bereits vergeben")

        # Benutzer erstellen
        self.user_counter += 1
        user_id = f"user_{self.user_counter}"
        salt = self._generate_salt()
        password_hash = self._hash_password(password, salt)

        user = User(
            user_id=user_id,
            username=username,
            password_hash=password_hash,
            salt=salt,
            created_at=time.time(),
            email=email
        )

        self.users[user_id] = user
        self.usernames[username.lower()] = user_id

        # Automatisch einloggen
        token = self._create_session(user_id)

        self.save_data()
        logger.info(f"Auth: Benutzer registriert: {username}")

        return user, token

    def login(self, username: str, password: str,
              ip_address: str = "", user_agent: str = "") -> Tuple[User, str]:
        """
        Meldet einen Benutzer an
        Returns: (User, token)
        Raises: InvalidCredentialsError, UserBannedError
        """
        # Benutzer finden
        user_id = self.usernames.get(username.lower())
        if not user_id:
            raise InvalidCredentialsError("Ungültiger Benutzername oder Passwort")

        user = self.users[user_id]

        # Gesperrt wegen zu vieler Fehlversuche?
        if user.failed_login_attempts >= self.MAX_FAILED_ATTEMPTS:
            lockout_remaining = (user.last_failed_login + self.LOCKOUT_DURATION) - time.time()
            if lockout_remaining > 0:
                raise InvalidCredentialsError(
                    f"Zu viele Fehlversuche. Warte {int(lockout_remaining)} Sekunden."
                )
            else:
                # Lockout abgelaufen, Reset
                user.failed_login_attempts = 0

        # Gebannt?
        if user.is_currently_banned():
            raise UserBannedError(f"Benutzer ist gesperrt: {user.ban_reason}")

        # Passwort prüfen
        password_hash = self._hash_password(password, user.salt)
        if password_hash != user.password_hash:
            user.failed_login_attempts += 1
            user.last_failed_login = time.time()
            self.save_data()
            raise InvalidCredentialsError("Ungültiger Benutzername oder Passwort")

        # Erfolgreicher Login
        user.failed_login_attempts = 0
        user.last_login = time.time()

        # Alte Session invalidieren
        if user_id in self.user_sessions:
            old_token = self.user_sessions[user_id]
            if old_token in self.sessions:
                del self.sessions[old_token]

        # Neue Session erstellen
        token = self._create_session(user_id, ip_address, user_agent)

        self.save_data()
        logger.info(f"Auth: Login erfolgreich: {username}")

        return user, token

    def _create_session(self, user_id: str, ip_address: str = "",
                        user_agent: str = "") -> str:
        """Erstellt eine neue Session"""
        token = self._generate_token()
        expires_at = time.time() + (TOKEN_EXPIRY_HOURS * 3600)

        session = Session(
            token=token,
            user_id=user_id,
            created_at=time.time(),
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )

        self.sessions[token] = session
        self.user_sessions[user_id] = token

        return token

    def validate_token(self, token: str) -> Optional[User]:
        """
        Validiert einen Token und gibt den Benutzer zurück
        Returns: User oder None wenn ungültig
        """
        session = self.sessions.get(token)
        if not session:
            return None

        if session.is_expired():
            del self.sessions[token]
            if self.user_sessions.get(session.user_id) == token:
                del self.user_sessions[session.user_id]
            return None

        user = self.users.get(session.user_id)
        if not user or user.is_currently_banned():
            return None

        return user

    def logout(self, token: str) -> bool:
        """Meldet einen Benutzer ab"""
        session = self.sessions.get(token)
        if not session:
            return False

        del self.sessions[token]
        if self.user_sessions.get(session.user_id) == token:
            del self.user_sessions[session.user_id]

        self.save_data()
        return True

    def change_password(self, user_id: str, old_password: str,
                        new_password: str) -> bool:
        """Ändert das Passwort eines Benutzers"""
        user = self.users.get(user_id)
        if not user:
            return False

        # Altes Passwort prüfen
        old_hash = self._hash_password(old_password, user.salt)
        if old_hash != user.password_hash:
            return False

        # Neues Passwort validieren
        valid, msg = self._validate_password(new_password)
        if not valid:
            raise ValidationError(msg)

        # Neues Passwort setzen
        new_salt = self._generate_salt()
        new_hash = self._hash_password(new_password, new_salt)
        user.salt = new_salt
        user.password_hash = new_hash

        # Alle Sessions invalidieren
        if user_id in self.user_sessions:
            token = self.user_sessions[user_id]
            if token in self.sessions:
                del self.sessions[token]
            del self.user_sessions[user_id]

        self.save_data()
        logger.info(f"Auth: Passwort geändert für {user.username}")
        return True

    def ban_user(self, user_id: str, reason: str, duration_hours: float = 0) -> bool:
        """
        Sperrt einen Benutzer
        duration_hours=0 bedeutet permanenter Ban
        """
        user = self.users.get(user_id)
        if not user:
            return False

        user.is_banned = True
        user.ban_reason = reason
        user.ban_until = time.time() + (duration_hours * 3600) if duration_hours > 0 else 0

        # Session beenden
        if user_id in self.user_sessions:
            token = self.user_sessions[user_id]
            if token in self.sessions:
                del self.sessions[token]
            del self.user_sessions[user_id]

        self.save_data()
        logger.warning(f"Auth: Benutzer gebannt: {user.username} - {reason}")
        return True

    def unban_user(self, user_id: str) -> bool:
        """Entsperrt einen Benutzer"""
        user = self.users.get(user_id)
        if not user:
            return False

        user.is_banned = False
        user.ban_reason = ""
        user.ban_until = 0

        self.save_data()
        logger.info(f"Auth: Benutzer entsperrt: {user.username}")
        return True

    def get_user(self, user_id: str) -> Optional[User]:
        """Gibt einen Benutzer zurück"""
        return self.users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Findet Benutzer nach Username"""
        user_id = self.usernames.get(username.lower())
        return self.users.get(user_id) if user_id else None

    def cleanup_expired_sessions(self):
        """Entfernt abgelaufene Sessions"""
        expired = [token for token, session in self.sessions.items()
                   if session.is_expired()]

        for token in expired:
            session = self.sessions.pop(token)
            if self.user_sessions.get(session.user_id) == token:
                del self.user_sessions[session.user_id]

        if expired:
            self.save_data()
            logger.debug(f"Auth: {len(expired)} abgelaufene Sessions entfernt")

    def is_authenticated(self, token: str) -> bool:
        """Prüft ob ein Token gültig ist"""
        return self.validate_token(token) is not None


# Globale Instanz
auth_system = AuthSystem()


# Decorator für authentifizierte Funktionen
def require_auth(func):
    """Decorator der Authentifizierung erfordert"""
    def wrapper(token: str, *args, **kwargs):
        user = auth_system.validate_token(token)
        if not user:
            raise AuthenticationError("Nicht authentifiziert")
        return func(user, *args, **kwargs)
    return wrapper
