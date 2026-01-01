# Tradegame - Multiplayer Börsenspiel

Ein rundenbasiertes Multiplayer-Börsenspiel für 2 Spieler, entwickelt mit Python und Pygame.

## Features

- **Multiplayer**: Host/Join über lokales Netzwerk oder Internet
- **4 Aktien**: Beyer, BMW, BP, Commerzbank
- **4 Kryptowährungen**: Bitcoin, Ethereum, Litecoin, Dogecoin (freischaltbar)
- **Ereigniskarten**: 10 verschiedene Marktereignisse
- **Chat-System**: Kommunikation während des Spiels
- **Speichern/Laden**: Automatisches Speichern des Spielstands

---

## Installation

### Voraussetzungen

- **Python 3.8** oder höher
- **pip** (Python Package Manager)

### Windows

1. **Python installieren**
   - Download von [python.org](https://www.python.org/downloads/)
   - Bei der Installation "Add Python to PATH" aktivieren!

2. **Spiel herunterladen**
   ```cmd
   git clone https://github.com/Minecraft425HD/Tradegame.git
   cd Tradegame
   ```

3. **Abhängigkeiten installieren**
   ```cmd
   pip install -r requirements.txt
   ```

4. **Spiel starten**
   ```cmd
   python start_game.py
   ```

   Oder Doppelklick auf `Start.bat`

### macOS

1. **Python installieren** (falls nicht vorhanden)
   ```bash
   # Mit Homebrew
   brew install python3

   # Oder Download von python.org
   ```

2. **Spiel herunterladen**
   ```bash
   git clone https://github.com/Minecraft425HD/Tradegame.git
   cd Tradegame
   ```

3. **Abhängigkeiten installieren**
   ```bash
   pip3 install -r requirements.txt
   ```

4. **Spiel starten**
   ```bash
   python3 start_game.py
   ```

   Oder:
   ```bash
   chmod +x start_game.sh
   ./start_game.sh
   ```

---

## Spiel starten

### Als Host (Server)

1. Starte das Spiel
2. Klicke auf "Multiplayer"
3. Gib deinen Spielernamen ein
4. Klicke auf "Host Game"
5. Teile deine IP-Adresse mit dem anderen Spieler

### Als Client (Beitreten)

1. Starte das Spiel
2. Klicke auf "Multiplayer"
3. Gib die IP-Adresse des Hosts ein
4. Gib deinen Spielernamen ein
5. Klicke auf "Join Game"

### IP-Adresse finden

**Windows:**
```cmd
ipconfig
```
Suche nach "IPv4-Adresse"

**macOS:**
```bash
ifconfig | grep "inet "
```
Oder: Systemeinstellungen → Netzwerk

---

## Spielsteuerung

| Taste | Aktion |
|-------|--------|
| **T** | Chat öffnen |
| **Enter** | Nachricht senden / Aktien kaufen/verkaufen |
| **ESC** | Einstellungen / Chat schließen |
| **Maus** | Buttons klicken, Aktien auswählen |

---

## Netzwerk-Konfiguration

Das Spiel verwendet **Port 5556** (TCP).

### Firewall-Einstellungen

**Windows:**
```cmd
netsh advfirewall firewall add rule name="Tradegame" dir=in action=allow protocol=TCP localport=5556
```

**macOS:**
- Systemeinstellungen → Sicherheit → Firewall → Firewall-Optionen
- Eingehende Verbindungen für Python erlauben

### Über Internet spielen

Für Spiele über das Internet:
1. Port 5556 im Router weiterleiten (Port Forwarding)
2. Öffentliche IP-Adresse an den anderen Spieler geben
   - Finde sie auf [whatismyip.com](https://whatismyip.com)

---

## Projektstruktur

```
Tradegame/
├── start_game.py      # Cross-Platform Starter (empfohlen)
├── start_game.sh      # macOS/Linux Shell-Skript
├── Start.bat          # Windows Batch-Datei
├── main.py            # Einstiegspunkt
├── config.py          # Konfiguration
├── constants.py       # Konstanten
├── client.py          # Client-Logik
├── server.py          # Server-Logik
├── screens.py         # UI-Screens
├── game_logic.py      # Spiellogik
├── ui.py              # UI-Komponenten
├── network.py         # Netzwerk-Protokoll
├── Colors/            # Farbkonfiguration
├── Variables/         # Spielvariablen
├── background.jpg     # Hintergrundbild
└── requirements.txt   # Python-Abhängigkeiten
```

---

## Fehlerbehebung

### "Pygame not found"
```bash
pip install pygame
```

### Verbindung fehlgeschlagen
- Prüfe ob die IP-Adresse korrekt ist
- Prüfe ob Port 5556 in der Firewall freigegeben ist
- Prüfe ob beide im selben Netzwerk sind

### Spiel startet nicht
- Prüfe Python-Version: `python --version` (min. 3.8)
- Installiere Abhängigkeiten neu: `pip install -r requirements.txt`

---

## Lizenz

GNU General Public License v3.0

---

## Autor

Minecraft425HD
