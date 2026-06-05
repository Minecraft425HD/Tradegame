#!/bin/bash
# Tradegame macOS Launcher
# Doppelklick im Finder startet dieses Skript.
# Installiert automatisch: Homebrew, Python 3.13, SDL-Libs, pygame, Firewall-Freigabe.

cd "$(dirname "$0")"
SCRIPT_DIR="$(pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "========================================"
echo "  Tradegame - Multiplayer Börsenspiel"
echo "  macOS Starter"
echo "========================================"
echo ""

# ── Homebrew installieren falls nicht vorhanden ───────────────────────────────
if ! command -v brew &> /dev/null; then
    echo "→ Homebrew nicht gefunden. Installiere Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # PATH für Apple Silicon
    if [ -f "/opt/homebrew/bin/brew" ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -f "/usr/local/bin/brew" ]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    if ! command -v brew &> /dev/null; then
        echo "✗ Homebrew-Installation fehlgeschlagen."
        echo "  Bitte manuell installieren: https://brew.sh"
        echo ""; echo "Drücke Enter zum Beenden..."; read; exit 1
    fi
    echo "✓ Homebrew installiert."
else
    # Sicherstellen dass brew im PATH ist (Apple Silicon)
    if [ -f "/opt/homebrew/bin/brew" ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
fi

# ── Python 3.13 installieren falls nicht vorhanden ───────────────────────────
if ! command -v python3.13 &> /dev/null; then
    echo "→ Python 3.13 nicht gefunden. Installiere via Homebrew..."
    brew install python@3.13
    if [ $? -ne 0 ]; then
        echo "✗ Python 3.13 Installation fehlgeschlagen."
        echo ""; echo "Drücke Enter zum Beenden..."; read; exit 1
    fi
    echo "✓ Python 3.13 installiert."
fi

PYTHON_CMD="$(brew --prefix python@3.13)/bin/python3.13"
if [ ! -f "$PYTHON_CMD" ]; then
    PYTHON_CMD="python3.13"
fi
echo "→ Verwende Python: $($PYTHON_CMD --version)"

# ── SDL-Bibliotheken installieren ─────────────────────────────────────────────
SDL_MISSING=false
for pkg in sdl2 sdl2_image sdl2_mixer sdl2_ttf pkg-config; do
    if ! brew list "$pkg" &> /dev/null; then
        SDL_MISSING=true
        break
    fi
done
if [ "$SDL_MISSING" = true ]; then
    echo "→ Installiere SDL-Bibliotheken..."
    brew install sdl2 sdl2_image sdl2_mixer sdl2_ttf pkg-config
    echo "✓ SDL-Bibliotheken installiert."
else
    echo "✓ SDL-Bibliotheken vorhanden."
fi

# ── Virtuelle Umgebung ────────────────────────────────────────────────────────
if [ ! -f "$VENV_DIR/bin/python" ]; then
    echo "→ Erstelle virtuelle Umgebung..."
    "$PYTHON_CMD" -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "✗ Virtuelle Umgebung konnte nicht erstellt werden."
        echo ""; echo "Drücke Enter zum Beenden..."; read; exit 1
    fi
    echo "✓ Virtuelle Umgebung erstellt."
fi

VENV_PYTHON="$VENV_DIR/bin/python"

# ── pip aktualisieren ─────────────────────────────────────────────────────────
"$VENV_PYTHON" -m pip install --upgrade pip --quiet

# ── pygame installieren ───────────────────────────────────────────────────────
if ! "$VENV_PYTHON" -c "import pygame" &> /dev/null; then
    echo "→ Installiere pygame..."
    BREW_PREFIX=$(brew --prefix)
    export PKG_CONFIG_PATH="$BREW_PREFIX/lib/pkgconfig"
    export LDFLAGS="-L$BREW_PREFIX/lib"
    export CPPFLAGS="-I$BREW_PREFIX/include"
    "$VENV_PYTHON" -m pip install pygame
    if [ $? -ne 0 ]; then
        echo "✗ pygame-Installation fehlgeschlagen."
        echo ""; echo "Drücke Enter zum Beenden..."; read; exit 1
    fi
    echo "✓ pygame installiert."
fi

# ── Weitere Abhängigkeiten ────────────────────────────────────────────────────
if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    "$VENV_PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt" --quiet
fi

# ── Firewall freigeben (Port 5556) ────────────────────────────────────────────
echo "→ Prüfe Firewall..."
GAME_PYTHON="$VENV_PYTHON"

# macOS Application Firewall: Python-Binary freigeben
if /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate | grep -q "enabled"; then
    /usr/libexec/ApplicationFirewall/socketfilterfw --add "$GAME_PYTHON" 2>/dev/null
    /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp "$GAME_PYTHON" 2>/dev/null
    echo "✓ Firewall: Python freigegeben."
else
    echo "✓ Firewall ist deaktiviert, keine Aktion nötig."
fi

# pf firewall (nur falls aktiv und Port noch nicht freigegeben)
if sudo pfctl -s rules 2>/dev/null | grep -q "5556"; then
    echo "✓ Port 5556 bereits freigegeben."
else
    # Nicht-invasiv: Nur Hinweis, kein sudo-Zwang
    echo "  Port 5556 wird vom Spiel verwendet (lokales Netzwerk)."
    echo "  macOS fragt beim ersten Start automatisch nach Erlaubnis."
fi

# ── Spiel starten ─────────────────────────────────────────────────────────────
echo ""
echo "========================================"
echo "  Starte Spiel..."
echo "========================================"
echo ""

"$VENV_PYTHON" "$SCRIPT_DIR/main.py"

if [ $? -ne 0 ]; then
    echo ""
    echo "Das Spiel wurde mit einem Fehler beendet."
    echo "Drücke Enter zum Beenden..."
    read
fi
