"""
Feature-Integration für Tradegame
Verbindet alle Feature-Module miteinander
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class FeatureEvent:
    """Ein Feature-Event zur Kommunikation zwischen Modulen"""
    event_type: str
    source: str
    data: Dict[str, Any] = field(default_factory=dict)
    player_id: str = ""
    timestamp: float = 0


class EventBus:
    """Zentraler Event-Bus für Feature-Kommunikation"""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_history: List[FeatureEvent] = []
        self._max_history = 1000

    def subscribe(self, event_type: str, callback: Callable):
        """Abonniert einen Event-Typ"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.debug(f"EventBus: Subscriber für '{event_type}' registriert")

    def unsubscribe(self, event_type: str, callback: Callable):
        """Kündigt Abonnement"""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                cb for cb in self._subscribers[event_type] if cb != callback
            ]

    def publish(self, event: FeatureEvent):
        """Veröffentlicht ein Event"""
        import time
        event.timestamp = time.time()

        # In Historie speichern
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

        # An Subscriber senden
        callbacks = self._subscribers.get(event.event_type, [])
        callbacks.extend(self._subscribers.get("*", []))  # Wildcard-Subscriber

        for callback in callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"EventBus: Fehler bei Callback für '{event.event_type}': {e}")

    def emit(self, event_type: str, source: str, player_id: str = "", **data):
        """Shortcut für publish()"""
        event = FeatureEvent(
            event_type=event_type,
            source=source,
            data=data,
            player_id=player_id
        )
        self.publish(event)


# Globale Event-Bus Instanz
event_bus = EventBus()


# ====================================
# Feature-Integration Funktionen
# ====================================

def integrate_achievements():
    """Integriert das Achievement-System mit anderen Features"""
    try:
        from achievements_system import achievement_system

        def on_trade(event: FeatureEvent):
            """Prüft Achievements nach Trade"""
            player_id = event.player_id
            data = event.data

            # Trade-Stats aktualisieren
            stats = {
                "total_trades": achievement_system.get_stat(player_id, "total_trades", 0) + 1,
                "total_profit": achievement_system.get_stat(player_id, "total_profit", 0) + data.get("profit", 0)
            }

            if data.get("profit", 0) > 0:
                stats["winning_trades"] = achievement_system.get_stat(player_id, "winning_trades", 0) + 1

            # Achievements prüfen
            achievement_system.check_achievements(player_id, stats)

        def on_level_up(event: FeatureEvent):
            """Achievement bei Level-Up"""
            player_id = event.player_id
            level = event.data.get("level", 1)
            achievement_system.check_achievements(player_id, {"level": level})

        event_bus.subscribe("trade_completed", on_trade)
        event_bus.subscribe("level_up", on_level_up)
        logger.info("Achievement-System integriert")

    except ImportError:
        logger.warning("Achievement-System nicht verfügbar")


def integrate_progression():
    """Integriert das Progressions-System"""
    try:
        from progression_system import progression_system

        def on_trade(event: FeatureEvent):
            """XP für Trades"""
            player_id = event.player_id
            profit = event.data.get("profit", 0)

            # XP basierend auf Trade-Ergebnis
            if profit > 0:
                xp = min(100, int(profit / 100))  # Max 100 XP pro Trade
            else:
                xp = 5  # Kleine XP auch für Verlust-Trades (Lernerfahrung)

            old_level = progression_system.get_level(player_id)
            progression_system.add_xp(player_id, xp)
            new_level = progression_system.get_level(player_id)

            if new_level > old_level:
                event_bus.emit("level_up", "progression", player_id, level=new_level)

        def on_achievement(event: FeatureEvent):
            """XP für Achievements"""
            player_id = event.player_id
            xp = event.data.get("xp_reward", 0)
            if xp > 0:
                progression_system.add_xp(player_id, xp)

        event_bus.subscribe("trade_completed", on_trade)
        event_bus.subscribe("achievement_unlocked", on_achievement)
        logger.info("Progressions-System integriert")

    except ImportError:
        logger.warning("Progressions-System nicht verfügbar")


def integrate_quests():
    """Integriert das Quest-System"""
    try:
        from quest_system import quest_system

        def on_trade(event: FeatureEvent):
            """Quest-Fortschritt bei Trade"""
            player_id = event.player_id
            stock = event.data.get("stock", "")
            action = event.data.get("action", "")
            quantity = event.data.get("quantity", 0)

            quest_system.update_progress(player_id, "trade", {
                "stock": stock,
                "action": action,
                "quantity": quantity
            })

        def on_login(event: FeatureEvent):
            """Tägliche Quests bei Login"""
            player_id = event.player_id
            quest_system.check_daily_reset(player_id)

        event_bus.subscribe("trade_completed", on_trade)
        event_bus.subscribe("player_login", on_login)
        logger.info("Quest-System integriert")

    except ImportError:
        logger.warning("Quest-System nicht verfügbar")


def integrate_notifications():
    """Integriert das Benachrichtigungs-System"""
    try:
        from notification_system import notification_system

        def on_achievement(event: FeatureEvent):
            """Benachrichtigung bei Achievement"""
            notification_system.achievement(
                event.data.get("name", "Erfolg"),
                event.data.get("description", "")
            )

        def on_trade(event: FeatureEvent):
            """Benachrichtigung bei Trade"""
            profit = event.data.get("profit", 0)
            stock = event.data.get("stock", "")

            if profit > 1000:
                notification_system.success(
                    "Großer Gewinn!",
                    f"+{profit:.0f}€ mit {stock}"
                )
            elif profit < -1000:
                notification_system.warning(
                    "Großer Verlust",
                    f"{profit:.0f}€ mit {stock}"
                )

        def on_news(event: FeatureEvent):
            """Benachrichtigung bei News"""
            notification_system.news(
                event.data.get("headline", "Marktnachricht"),
                event.data.get("summary", "")
            )

        event_bus.subscribe("achievement_unlocked", on_achievement)
        event_bus.subscribe("trade_completed", on_trade)
        event_bus.subscribe("market_news", on_news)
        logger.info("Benachrichtigungs-System integriert")

    except ImportError:
        logger.warning("Benachrichtigungs-System nicht verfügbar")


def integrate_clans():
    """Integriert Clans mit Turnieren"""
    try:
        from clan_system import clan_system
        from tournament_system import tournament_system

        def on_tournament_win(event: FeatureEvent):
            """Clan-XP bei Turniersieg"""
            player_id = event.player_id
            prize = event.data.get("prize", 0)

            clan = clan_system.get_player_clan(player_id)
            if clan:
                # 10% des Preises geht an Clan-Kasse
                clan_contribution = prize * 0.1
                clan_system.contribute_to_treasury(player_id, clan_contribution)

        event_bus.subscribe("tournament_win", on_tournament_win)
        logger.info("Clan-Turnier-Integration aktiviert")

    except ImportError:
        logger.warning("Clan/Turnier-Integration nicht verfügbar")


def integrate_leaderboards():
    """Integriert Bestenlisten-Updates"""
    try:
        from global_leaderboards import leaderboard_system

        def on_game_end(event: FeatureEvent):
            """Leaderboard-Update am Spielende"""
            player_id = event.player_id
            final_wealth = event.data.get("wealth", 0)
            stats = event.data.get("stats", {})

            leaderboard_system.update_player_stats(
                player_id,
                wealth=final_wealth,
                **stats
            )

            # Alle Leaderboards aktualisieren
            if leaderboard_system.needs_update():
                leaderboard_system.update_all_leaderboards()

        event_bus.subscribe("game_ended", on_game_end)
        logger.info("Leaderboard-Integration aktiviert")

    except ImportError:
        logger.warning("Leaderboard-Integration nicht verfügbar")


def integrate_all():
    """Integriert alle verfügbaren Features"""
    logger.info("Starte Feature-Integration...")

    integrate_achievements()
    integrate_progression()
    integrate_quests()
    integrate_notifications()
    integrate_clans()
    integrate_leaderboards()

    logger.info("Feature-Integration abgeschlossen")


# ====================================
# Helper-Funktionen für Game-Events
# ====================================

def emit_trade_event(player_id: str, stock: str, action: str,
                     quantity: int, price: float, profit: float = 0):
    """Emittiert ein Trade-Event"""
    event_bus.emit(
        "trade_completed",
        "game_logic",
        player_id,
        stock=stock,
        action=action,
        quantity=quantity,
        price=price,
        profit=profit
    )


def emit_game_start(player_ids: List[str], game_mode: str):
    """Emittiert Game-Start Event"""
    for player_id in player_ids:
        event_bus.emit(
            "game_started",
            "server",
            player_id,
            game_mode=game_mode,
            players=player_ids
        )


def emit_game_end(player_id: str, wealth: float, stats: Dict):
    """Emittiert Game-End Event"""
    event_bus.emit(
        "game_ended",
        "server",
        player_id,
        wealth=wealth,
        stats=stats
    )


def emit_player_login(player_id: str):
    """Emittiert Login-Event"""
    event_bus.emit("player_login", "auth", player_id)


def emit_achievement(player_id: str, achievement_id: str, name: str,
                     description: str, xp_reward: int):
    """Emittiert Achievement-Event"""
    event_bus.emit(
        "achievement_unlocked",
        "achievements",
        player_id,
        achievement_id=achievement_id,
        name=name,
        description=description,
        xp_reward=xp_reward
    )


def emit_market_news(headline: str, stock: str, effect: float):
    """Emittiert Marktnachrichten-Event"""
    event_bus.emit(
        "market_news",
        "news_system",
        headline=headline,
        stock=stock,
        effect=effect
    )


# Automatische Integration beim Import
# (auskommentiert - sollte explizit aufgerufen werden)
# integrate_all()
