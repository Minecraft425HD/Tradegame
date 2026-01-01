"""
Unit Tests für auth_system.py
"""

import unittest
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth_system import (
    AuthSystem, User, Session,
    InvalidCredentialsError, UserExistsError, ValidationError, UserBannedError
)


class TestAuthSystem(unittest.TestCase):
    """Tests für das Authentifizierungs-System"""

    def setUp(self):
        """Test-Setup mit frischem AuthSystem"""
        self.auth = AuthSystem()
        # Daten nicht aus Datei laden
        self.auth.users.clear()
        self.auth.usernames.clear()
        self.auth.sessions.clear()
        self.auth.user_sessions.clear()

    def test_register_success(self):
        """Test erfolgreiche Registrierung"""
        user, token = self.auth.register("testuser", "password123")

        self.assertIsNotNone(user)
        self.assertIsNotNone(token)
        self.assertEqual(user.username, "testuser")
        self.assertIn(user.user_id, self.auth.users)

    def test_register_duplicate_username(self):
        """Test Registrierung mit existierendem Username"""
        self.auth.register("testuser", "password123")

        with self.assertRaises(UserExistsError):
            self.auth.register("testuser", "otherpassword")

    def test_register_case_insensitive(self):
        """Test Case-Insensitive Usernamen"""
        self.auth.register("TestUser", "password123")

        with self.assertRaises(UserExistsError):
            self.auth.register("testuser", "password123")

    def test_register_invalid_username_short(self):
        """Test zu kurzer Username"""
        with self.assertRaises(ValidationError):
            self.auth.register("ab", "password123")

    def test_register_invalid_username_chars(self):
        """Test ungültige Zeichen im Username"""
        with self.assertRaises(ValidationError):
            self.auth.register("user@name", "password123")

    def test_register_invalid_password_short(self):
        """Test zu kurzes Passwort"""
        with self.assertRaises(ValidationError):
            self.auth.register("testuser", "123")

    def test_login_success(self):
        """Test erfolgreicher Login"""
        self.auth.register("testuser", "password123")
        user, token = self.auth.login("testuser", "password123")

        self.assertIsNotNone(user)
        self.assertIsNotNone(token)
        self.assertEqual(user.username, "testuser")

    def test_login_wrong_password(self):
        """Test Login mit falschem Passwort"""
        self.auth.register("testuser", "password123")

        with self.assertRaises(InvalidCredentialsError):
            self.auth.login("testuser", "wrongpassword")

    def test_login_unknown_user(self):
        """Test Login mit unbekanntem User"""
        with self.assertRaises(InvalidCredentialsError):
            self.auth.login("unknownuser", "password123")

    def test_login_case_insensitive(self):
        """Test Case-Insensitive Login"""
        self.auth.register("TestUser", "password123")
        user, token = self.auth.login("testuser", "password123")

        self.assertEqual(user.username, "TestUser")

    def test_validate_token_success(self):
        """Test Token-Validierung erfolgreich"""
        user, token = self.auth.register("testuser", "password123")
        validated_user = self.auth.validate_token(token)

        self.assertIsNotNone(validated_user)
        self.assertEqual(validated_user.user_id, user.user_id)

    def test_validate_token_invalid(self):
        """Test ungültiger Token"""
        result = self.auth.validate_token("invalid_token_12345")
        self.assertIsNone(result)

    def test_logout(self):
        """Test Logout"""
        user, token = self.auth.register("testuser", "password123")

        result = self.auth.logout(token)
        self.assertTrue(result)

        # Token sollte jetzt ungültig sein
        self.assertIsNone(self.auth.validate_token(token))

    def test_change_password(self):
        """Test Passwort ändern"""
        user, token = self.auth.register("testuser", "oldpassword")

        result = self.auth.change_password(user.user_id, "oldpassword", "newpassword")
        self.assertTrue(result)

        # Mit neuem Passwort einloggen
        user, token = self.auth.login("testuser", "newpassword")
        self.assertIsNotNone(token)

        # Altes Passwort sollte nicht mehr funktionieren
        with self.assertRaises(InvalidCredentialsError):
            self.auth.login("testuser", "oldpassword")

    def test_ban_user(self):
        """Test User bannen"""
        user, token = self.auth.register("testuser", "password123")

        result = self.auth.ban_user(user.user_id, "Cheating", duration_hours=1)
        self.assertTrue(result)

        # User sollte nicht mehr einloggen können
        with self.assertRaises(UserBannedError):
            self.auth.login("testuser", "password123")

    def test_unban_user(self):
        """Test User entbannen"""
        user, token = self.auth.register("testuser", "password123")
        self.auth.ban_user(user.user_id, "Test")

        result = self.auth.unban_user(user.user_id)
        self.assertTrue(result)

        # User sollte wieder einloggen können
        user, token = self.auth.login("testuser", "password123")
        self.assertIsNotNone(token)

    def test_failed_login_attempts_lockout(self):
        """Test Lockout nach zu vielen Fehlversuchen"""
        self.auth.register("testuser", "password123")

        # Mehrere fehlgeschlagene Logins
        for _ in range(5):
            try:
                self.auth.login("testuser", "wrongpassword")
            except InvalidCredentialsError:
                pass

        # Nächster Versuch sollte wegen Lockout fehlschlagen
        with self.assertRaises(InvalidCredentialsError) as context:
            self.auth.login("testuser", "password123")  # Richtiges Passwort!

        self.assertIn("Warte", str(context.exception))


class TestUser(unittest.TestCase):
    """Tests für User-Klasse"""

    def test_user_to_dict(self):
        """Test User-Serialisierung"""
        user = User(
            user_id="user_1",
            username="testuser",
            password_hash="hash",
            salt="salt",
            created_at=time.time()
        )

        data = user.to_dict()
        self.assertEqual(data["user_id"], "user_1")
        self.assertEqual(data["username"], "testuser")

    def test_user_from_dict(self):
        """Test User-Deserialisierung"""
        data = {
            "user_id": "user_1",
            "username": "testuser",
            "password_hash": "hash",
            "salt": "salt",
            "created_at": time.time(),
            "last_login": 0,
            "is_banned": False,
            "ban_reason": "",
            "ban_until": 0,
            "failed_login_attempts": 0,
            "last_failed_login": 0,
            "email": "",
            "is_verified": False
        }

        user = User.from_dict(data)
        self.assertEqual(user.user_id, "user_1")
        self.assertEqual(user.username, "testuser")

    def test_is_currently_banned(self):
        """Test Ban-Status-Prüfung"""
        user = User(
            user_id="user_1",
            username="testuser",
            password_hash="hash",
            salt="salt",
            created_at=time.time()
        )

        # Nicht gebannt
        self.assertFalse(user.is_currently_banned())

        # Permanent gebannt
        user.is_banned = True
        user.ban_until = 0
        self.assertTrue(user.is_currently_banned())

        # Temporär gebannt (noch aktiv)
        user.ban_until = time.time() + 3600
        self.assertTrue(user.is_currently_banned())

        # Temporär gebannt (abgelaufen)
        user.ban_until = time.time() - 1
        self.assertFalse(user.is_currently_banned())


class TestSession(unittest.TestCase):
    """Tests für Session-Klasse"""

    def test_session_expired(self):
        """Test Session-Ablauf"""
        # Abgelaufene Session
        session = Session(
            token="token",
            user_id="user_1",
            created_at=time.time() - 3600,
            expires_at=time.time() - 60
        )
        self.assertTrue(session.is_expired())

        # Gültige Session
        session = Session(
            token="token",
            user_id="user_1",
            created_at=time.time(),
            expires_at=time.time() + 3600
        )
        self.assertFalse(session.is_expired())


if __name__ == '__main__':
    unittest.main()
