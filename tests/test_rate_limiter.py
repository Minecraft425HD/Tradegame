"""
Unit Tests für rate_limiter.py
"""

import unittest
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rate_limiter import (
    RateLimiter, RateLimitAction, RateLimitConfig,
    IPRateLimiter, check_rate_limit
)


class TestRateLimiter(unittest.TestCase):
    """Tests für den Rate Limiter"""

    def setUp(self):
        """Test-Setup mit kleinen Limits für schnelle Tests"""
        self.limiter = RateLimiter({
            RateLimitAction.GENERAL: RateLimitConfig(
                max_requests=3,
                window_seconds=1.0,
                block_duration=1.0
            ),
            RateLimitAction.TRADE: RateLimitConfig(
                max_requests=2,
                window_seconds=1.0,
                block_duration=1.0
            )
        })

    def test_allow_within_limit(self):
        """Test Anfragen innerhalb des Limits"""
        for i in range(3):
            allowed, error = self.limiter.check("client_1", RateLimitAction.GENERAL)
            self.assertTrue(allowed, f"Request {i+1} should be allowed")
            self.assertEqual(error, "")

    def test_block_over_limit(self):
        """Test Blockierung bei Überschreitung"""
        # 3 erlaubte Anfragen
        for _ in range(3):
            self.limiter.check("client_1", RateLimitAction.GENERAL)

        # 4. Anfrage sollte blockiert werden
        allowed, error = self.limiter.check("client_1", RateLimitAction.GENERAL)
        self.assertFalse(allowed)
        self.assertIn("Zu viele", error)

    def test_separate_clients(self):
        """Test dass Clients getrennt gezählt werden"""
        # Client 1 ausschöpfen
        for _ in range(3):
            self.limiter.check("client_1", RateLimitAction.GENERAL)

        # Client 2 sollte noch erlaubt sein
        allowed, _ = self.limiter.check("client_2", RateLimitAction.GENERAL)
        self.assertTrue(allowed)

    def test_separate_actions(self):
        """Test dass Aktionen getrennt gezählt werden"""
        # GENERAL ausschöpfen
        for _ in range(3):
            self.limiter.check("client_1", RateLimitAction.GENERAL)

        # TRADE sollte noch erlaubt sein
        allowed, _ = self.limiter.check("client_1", RateLimitAction.TRADE)
        self.assertTrue(allowed)

    def test_window_reset(self):
        """Test dass Fenster nach Zeit zurücksetzt"""
        # Limit erreichen
        for _ in range(3):
            self.limiter.check("client_1", RateLimitAction.GENERAL)

        # Warten bis Fenster zurücksetzt
        time.sleep(1.1)

        # Sollte wieder erlaubt sein
        allowed, _ = self.limiter.check("client_1", RateLimitAction.GENERAL)
        self.assertTrue(allowed)

    def test_get_remaining(self):
        """Test verbleibende Anfragen abfragen"""
        remaining, _ = self.limiter.get_remaining("client_1", RateLimitAction.GENERAL)
        self.assertEqual(remaining, 3)

        self.limiter.check("client_1", RateLimitAction.GENERAL)

        remaining, _ = self.limiter.get_remaining("client_1", RateLimitAction.GENERAL)
        self.assertEqual(remaining, 2)

    def test_is_blocked(self):
        """Test Blockiert-Status abfragen"""
        self.assertFalse(self.limiter.is_blocked("client_1", RateLimitAction.GENERAL))

        # Limit überschreiten
        for _ in range(4):
            self.limiter.check("client_1", RateLimitAction.GENERAL)

        self.assertTrue(self.limiter.is_blocked("client_1", RateLimitAction.GENERAL))

    def test_unblock(self):
        """Test manuelles Entsperren"""
        # Blockieren
        for _ in range(4):
            self.limiter.check("client_1", RateLimitAction.GENERAL)

        self.assertTrue(self.limiter.is_blocked("client_1", RateLimitAction.GENERAL))

        # Entsperren
        self.limiter.unblock("client_1", RateLimitAction.GENERAL)

        self.assertFalse(self.limiter.is_blocked("client_1", RateLimitAction.GENERAL))

    def test_reset_client(self):
        """Test Client komplett zurücksetzen"""
        # Einige Anfragen machen
        for _ in range(2):
            self.limiter.check("client_1", RateLimitAction.GENERAL)

        # Zurücksetzen
        self.limiter.reset("client_1")

        # Sollte wieder voll sein
        remaining, _ = self.limiter.get_remaining("client_1", RateLimitAction.GENERAL)
        self.assertEqual(remaining, 3)

    def test_get_stats(self):
        """Test Statistiken"""
        self.limiter.check("client_1", RateLimitAction.GENERAL)
        self.limiter.check("client_2", RateLimitAction.TRADE)

        stats = self.limiter.get_stats()

        self.assertEqual(stats["total_requests"], 2)
        self.assertEqual(stats["active_clients"], 2)


class TestIPRateLimiter(unittest.TestCase):
    """Tests für IP Rate Limiter"""

    def setUp(self):
        """Test-Setup"""
        self.ip_limiter = IPRateLimiter()
        self.ip_limiter.banned_ips.clear()

    def test_check_connection_allowed(self):
        """Test erlaubte Verbindung"""
        allowed, _ = self.ip_limiter.check_connection("192.168.1.1")
        self.assertTrue(allowed)

    def test_ban_ip(self):
        """Test IP bannen"""
        self.ip_limiter.ban_ip("192.168.1.100", duration=60)

        allowed, error = self.ip_limiter.check_connection("192.168.1.100")
        self.assertFalse(allowed)
        self.assertIn("gesperrt", error)

    def test_ban_ip_permanent(self):
        """Test permanenter IP-Ban"""
        self.ip_limiter.ban_ip("192.168.1.100", duration=0)

        allowed, error = self.ip_limiter.check_connection("192.168.1.100")
        self.assertFalse(allowed)
        self.assertIn("permanent", error)

    def test_unban_ip(self):
        """Test IP entbannen"""
        self.ip_limiter.ban_ip("192.168.1.100")
        self.ip_limiter.unban_ip("192.168.1.100")

        allowed, _ = self.ip_limiter.check_connection("192.168.1.100")
        self.assertTrue(allowed)


class TestCheckRateLimitShortcut(unittest.TestCase):
    """Tests für check_rate_limit Shortcut"""

    def test_check_rate_limit_valid_action(self):
        """Test mit gültiger Aktion"""
        allowed, _ = check_rate_limit("test_client", "trade")
        self.assertTrue(allowed)

    def test_check_rate_limit_invalid_action(self):
        """Test mit ungültiger Aktion (fällt auf GENERAL zurück)"""
        allowed, _ = check_rate_limit("test_client", "invalid_action")
        self.assertTrue(allowed)


if __name__ == '__main__':
    unittest.main()
