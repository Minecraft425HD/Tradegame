"""
Export-System für Tradegame
Exportiert Daten in verschiedene Formate (CSV, JSON, PDF)
"""

import csv
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from config import get_path

logger = logging.getLogger(__name__)


class ExportSystem:
    """Verwaltet Daten-Exporte"""

    def __init__(self):
        self.export_dir = get_path("exports")
        self._ensure_export_dir()

    def _ensure_export_dir(self):
        """Stellt sicher dass Export-Verzeichnis existiert"""
        import os
        os.makedirs(self.export_dir, exist_ok=True)

    def _generate_filename(self, prefix: str, extension: str) -> str:
        """Generiert einen Dateinamen mit Timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{self.export_dir}/{prefix}_{timestamp}.{extension}"

    # === CSV Exporte ===

    def export_trades_csv(self, trades: List[Dict], player_id: str = "player") -> str:
        """Exportiert Trade-Historie als CSV"""
        filename = self._generate_filename(f"trades_{player_id}", "csv")

        headers = [
            "Datum", "Zeit", "Aktie", "Typ", "Anzahl", "Preis",
            "Gesamtwert", "Gewinn/Verlust"
        ]

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(headers)

                for trade in trades:
                    timestamp = trade.get("timestamp", time.time())
                    dt = datetime.fromtimestamp(timestamp)

                    row = [
                        dt.strftime("%d.%m.%Y"),
                        dt.strftime("%H:%M:%S"),
                        trade.get("stock_symbol", ""),
                        trade.get("trade_type", ""),
                        trade.get("shares", 0),
                        f"{trade.get('price', 0):.2f}",
                        f"{trade.get('total_value', 0):.2f}",
                        f"{trade.get('profit_loss', 0):+.2f}"
                    ]
                    writer.writerow(row)

            logger.info(f"Trades exportiert: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Export-Fehler: {e}")
            return ""

    def export_portfolio_csv(self, portfolio: Dict[str, Dict],
                            prices: Dict[str, float],
                            player_id: str = "player") -> str:
        """Exportiert Portfolio als CSV"""
        filename = self._generate_filename(f"portfolio_{player_id}", "csv")

        headers = [
            "Aktie", "Anzahl", "Kaufpreis (Ø)", "Aktueller Preis",
            "Einstand", "Aktueller Wert", "Gewinn/Verlust", "Rendite %"
        ]

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(headers)

                total_cost = 0
                total_value = 0

                for symbol, data in portfolio.items():
                    shares = data.get("shares", 0)
                    avg_price = data.get("avg_buy_price", 0)
                    current_price = prices.get(symbol, avg_price)

                    cost = shares * avg_price
                    value = shares * current_price
                    profit = value - cost
                    returns = (profit / cost * 100) if cost > 0 else 0

                    total_cost += cost
                    total_value += value

                    row = [
                        symbol,
                        shares,
                        f"{avg_price:.2f}",
                        f"{current_price:.2f}",
                        f"{cost:.2f}",
                        f"{value:.2f}",
                        f"{profit:+.2f}",
                        f"{returns:+.2f}%"
                    ]
                    writer.writerow(row)

                # Summenzeile
                total_profit = total_value - total_cost
                total_returns = (total_profit / total_cost * 100) if total_cost > 0 else 0
                writer.writerow([])
                writer.writerow([
                    "GESAMT", "", "", "",
                    f"{total_cost:.2f}",
                    f"{total_value:.2f}",
                    f"{total_profit:+.2f}",
                    f"{total_returns:+.2f}%"
                ])

            logger.info(f"Portfolio exportiert: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Export-Fehler: {e}")
            return ""

    def export_performance_csv(self, performance_data: List[Dict],
                               player_id: str = "player") -> str:
        """Exportiert Performance-Daten als CSV"""
        filename = self._generate_filename(f"performance_{player_id}", "csv")

        headers = ["Datum", "Vermögen", "Tagesänderung", "Änderung %"]

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(headers)

                prev_value = None
                for data in performance_data:
                    timestamp = data.get("timestamp", time.time())
                    dt = datetime.fromtimestamp(timestamp)
                    value = data.get("wealth", 0)

                    if prev_value is not None:
                        change = value - prev_value
                        change_pct = (change / prev_value * 100) if prev_value > 0 else 0
                    else:
                        change = 0
                        change_pct = 0

                    row = [
                        dt.strftime("%d.%m.%Y"),
                        f"{value:.2f}",
                        f"{change:+.2f}",
                        f"{change_pct:+.2f}%"
                    ]
                    writer.writerow(row)
                    prev_value = value

            logger.info(f"Performance exportiert: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Export-Fehler: {e}")
            return ""

    # === JSON Exporte ===

    def export_full_data_json(self, data: Dict, player_id: str = "player") -> str:
        """Exportiert alle Daten als JSON"""
        filename = self._generate_filename(f"data_{player_id}", "json")

        export_data = {
            "export_date": datetime.now().isoformat(),
            "player_id": player_id,
            "data": data
        }

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Daten exportiert: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Export-Fehler: {e}")
            return ""

    # === Berichte ===

    def generate_tax_report(self, trades: List[Dict], year: int,
                            player_id: str = "player") -> str:
        """Generiert einen Steuerbericht"""
        filename = self._generate_filename(f"steuerbericht_{year}_{player_id}", "txt")

        # Trades des Jahres filtern
        year_start = datetime(year, 1, 1).timestamp()
        year_end = datetime(year, 12, 31, 23, 59, 59).timestamp()

        year_trades = [
            t for t in trades
            if year_start <= t.get("timestamp", 0) <= year_end
        ]

        # Statistiken berechnen
        total_profit = sum(t.get("profit_loss", 0) for t in year_trades if t.get("profit_loss", 0) > 0)
        total_loss = sum(t.get("profit_loss", 0) for t in year_trades if t.get("profit_loss", 0) < 0)
        net_profit = total_profit + total_loss

        # Dividenden (falls vorhanden)
        dividends = sum(t.get("dividend", 0) for t in year_trades)

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"{'=' * 60}\n")
                f.write(f"STEUERBERICHT {year}\n")
                f.write(f"{'=' * 60}\n\n")
                f.write(f"Spieler: {player_id}\n")
                f.write(f"Erstellt am: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n")

                f.write(f"{'-' * 40}\n")
                f.write("ZUSAMMENFASSUNG\n")
                f.write(f"{'-' * 40}\n\n")

                f.write(f"Anzahl Trades: {len(year_trades)}\n")
                f.write(f"Gewinne: {total_profit:+,.2f}€\n")
                f.write(f"Verluste: {total_loss:+,.2f}€\n")
                f.write(f"Nettogewinn: {net_profit:+,.2f}€\n")
                if dividends > 0:
                    f.write(f"Dividenden: {dividends:+,.2f}€\n")
                f.write("\n")

                f.write(f"{'-' * 40}\n")
                f.write("STEUERPFLICHTIGE BETRÄGE (HINWEIS)\n")
                f.write(f"{'-' * 40}\n\n")

                # Hinweis: Fiktive Berechnung
                f.write("Kapitalertragssteuer (25%): ")
                if net_profit > 0:
                    tax = net_profit * 0.25
                    soli = tax * 0.055
                    f.write(f"{tax:,.2f}€\n")
                    f.write(f"Solidaritätszuschlag (5.5%): {soli:,.2f}€\n")
                    f.write(f"Gesamt ca.: {tax + soli:,.2f}€\n")
                else:
                    f.write("0,00€ (Verlustvortrag möglich)\n")

                f.write("\n⚠️ Dies ist eine vereinfachte Berechnung.\n")
                f.write("Bitte konsultieren Sie einen Steuerberater.\n")

                f.write(f"\n{'=' * 60}\n")
                f.write("DETAILLIERTE TRADES\n")
                f.write(f"{'=' * 60}\n\n")

                for trade in sorted(year_trades, key=lambda t: t.get("timestamp", 0)):
                    dt = datetime.fromtimestamp(trade.get("timestamp", 0))
                    f.write(f"{dt.strftime('%d.%m.%Y')} | ")
                    f.write(f"{trade.get('trade_type', ''):6s} | ")
                    f.write(f"{trade.get('stock_symbol', ''):8s} | ")
                    f.write(f"{trade.get('shares', 0):5d} x {trade.get('price', 0):8.2f}€ | ")
                    f.write(f"G/V: {trade.get('profit_loss', 0):+10.2f}€\n")

            logger.info(f"Steuerbericht erstellt: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Export-Fehler: {e}")
            return ""

    def generate_summary_report(self, player_data: Dict,
                                 stats: Dict,
                                 player_id: str = "player") -> str:
        """Generiert einen Zusammenfassungs-Bericht"""
        filename = self._generate_filename(f"zusammenfassung_{player_id}", "txt")

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"{'=' * 60}\n")
                f.write(f"SPIELER-ZUSAMMENFASSUNG\n")
                f.write(f"{'=' * 60}\n\n")

                f.write(f"Spieler: {player_id}\n")
                f.write(f"Erstellt: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n")

                f.write(f"{'-' * 40}\n")
                f.write("KONTOSTAND\n")
                f.write(f"{'-' * 40}\n")
                f.write(f"Bargeld: {player_data.get('balance', 0):,.2f}€\n")
                f.write(f"Portfolio-Wert: {player_data.get('portfolio_value', 0):,.2f}€\n")
                f.write(f"Gesamtvermögen: {player_data.get('total_wealth', 0):,.2f}€\n\n")

                f.write(f"{'-' * 40}\n")
                f.write("STATISTIKEN\n")
                f.write(f"{'-' * 40}\n")
                f.write(f"Level: {stats.get('level', 1)}\n")
                f.write(f"Gesamt Trades: {stats.get('total_trades', 0)}\n")
                f.write(f"Gewinnende Trades: {stats.get('winning_trades', 0)}\n")
                f.write(f"Verlierende Trades: {stats.get('losing_trades', 0)}\n")

                win_rate = 0
                if stats.get('total_trades', 0) > 0:
                    win_rate = stats.get('winning_trades', 0) / stats.get('total_trades', 1) * 100
                f.write(f"Gewinnrate: {win_rate:.1f}%\n")

                f.write(f"Gesamtgewinn: {stats.get('total_profit', 0):+,.2f}€\n")
                f.write(f"Bester Trade: {stats.get('best_trade', 0):+,.2f}€\n")
                f.write(f"Schlechtester Trade: {stats.get('worst_trade', 0):+,.2f}€\n")
                f.write(f"Beste Serie: {stats.get('best_streak', 0)} Trades\n")

            logger.info(f"Zusammenfassung erstellt: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Export-Fehler: {e}")
            return ""


# Globale Instanz
export_system = ExportSystem()


def draw_export_menu(screen, font, x: int, y: int, width: int = 300):
    """Zeichnet das Export-Menü"""
    import pygame

    # Header
    header = font.render("📤 Daten exportieren", True, (255, 200, 100))
    screen.blit(header, (x, y))
    y += 35

    export_options = [
        ("trades_csv", "📊 Trade-Historie (CSV)"),
        ("portfolio_csv", "💼 Portfolio (CSV)"),
        ("performance_csv", "📈 Performance (CSV)"),
        ("full_json", "💾 Alle Daten (JSON)"),
        ("tax_report", "🧾 Steuerbericht"),
        ("summary", "📋 Zusammenfassung"),
    ]

    for option_id, option_name in export_options:
        # Button
        pygame.draw.rect(screen, (40, 40, 60), (x, y, width, 30), border_radius=5)

        text = font.render(option_name, True, (200, 200, 200))
        screen.blit(text, (x + 10, y + 5))

        y += 35

    return y
