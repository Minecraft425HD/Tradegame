#!/bin/bash
# Tradegame Starter for macOS/Linux
# Handles macOS Apple Silicon, Python 3.14+, Homebrew venv restrictions, missing SDL libs

echo "========================================"
echo "  Tradegame - Multiplayer Börsenspiel"
echo "========================================"
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/.venv"

# ── macOS: ensure SDL libs are installed (needed for pygame on Python 3.14) ──
if [[ "$OSTYPE" == "darwin"* ]]; then
    if command -v brew &> /dev/null; then
        SDL_MISSING=false
        for pkg in sdl2 sdl2_image sdl2_mixer sdl2_ttf pkg-config; do
            if ! brew list "$pkg" &> /dev/null; then
                SDL_MISSING=true
                break
            fi
        done
        if [ "$SDL_MISSING" = true ]; then
            echo "→ Installiere fehlende SDL-Bibliotheken via Homebrew..."
            brew install sdl2 sdl2_image sdl2_mixer sdl2_ttf pkg-config
            if [ $? -ne 0 ]; then
                echo "✗ Homebrew-Installation fehlgeschlagen."
                echo "  Bitte manuell ausführen: brew install sdl2 sdl2_image sdl2_mixer sdl2_ttf pkg-config"
                echo ""
            else
                echo "✓ SDL-Bibliotheken installiert."
            fi
        fi
    else
        echo "⚠ Homebrew nicht gefunden. SDL-Bibliotheken werden möglicherweise benötigt."
        echo "  Homebrew installieren: https://brew.sh"
        echo ""
    fi
fi

# ── Wähle Python: bevorzuge 3.13 (stable pygame wheels), fallback auf 3.x ──
PYTHON_CMD=""
for candidate in python3.13 python3.12 python3.11 python3.10 python3.9 python3 python; do
    if command -v "$candidate" &> /dev/null; then
        VER=$("$candidate" -c "import sys; print(sys.version_info[:2])" 2>/dev/null)
        # Akzeptiere 3.8+
        OK=$("$candidate" -c "import sys; print(sys.version_info >= (3,8))" 2>/dev/null)
        if [ "$OK" = "True" ]; then
            PYTHON_CMD="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "✗ Python 3.8 oder höher nicht gefunden!"
    echo "  Bitte installieren: https://www.python.org/downloads/"
    if [[ "$OSTYPE" == "darwin"* ]] && command -v brew &> /dev/null; then
        echo "  Oder: brew install python@3.13"
    fi
    echo ""
    echo "Drücke Enter zum Beenden..."
    read
    exit 1
fi

PYTHON_VER=$("$PYTHON_CMD" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "→ Verwende Python $PYTHON_VER ($PYTHON_CMD)"

# ── Virtuelle Umgebung erstellen falls nicht vorhanden ──
if [ ! -f "$VENV_DIR/bin/python" ]; then
    echo "→ Erstelle virtuelle Umgebung in .venv ..."
    "$PYTHON_CMD" -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "✗ Virtuelle Umgebung konnte nicht erstellt werden."
        echo "  Versuche: $PYTHON_CMD -m venv .venv"
        echo ""
        echo "Drücke Enter zum Beenden..."
        read
        exit 1
    fi
    echo "✓ Virtuelle Umgebung erstellt."
fi

VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

# ── pip aktualisieren ──
"$VENV_PYTHON" -m pip install --upgrade pip --quiet

# ── pygame installieren falls fehlt ──
if ! "$VENV_PYTHON" -c "import pygame" &> /dev/null 2>&1; then
    echo "→ Installiere pygame ..."
    "$VENV_PIP" install pygame
    if [ $? -ne 0 ]; then
        echo ""
        echo "✗ pygame-Installation fehlgeschlagen."
        echo ""
        # Letzter Versuch: SDL-Pfade für Homebrew setzen und nochmal versuchen
        if [[ "$OSTYPE" == "darwin"* ]] && command -v brew &> /dev/null; then
            echo "→ Setze SDL-Pfade und versuche erneut..."
            BREW_PREFIX=$(brew --prefix)
            export PKG_CONFIG_PATH="$BREW_PREFIX/lib/pkgconfig"
            export LDFLAGS="-L$BREW_PREFIX/lib"
            export CPPFLAGS="-I$BREW_PREFIX/include"
            "$VENV_PIP" install pygame
            if [ $? -ne 0 ]; then
                echo "✗ Konnte pygame nicht installieren."
                echo "  Bitte Python 3.13 installieren: brew install python@3.13"
                echo "  Dann diese Datei erneut ausführen."
                echo ""
                echo "Drücke Enter zum Beenden..."
                read
                exit 1
            fi
        else
            echo "  Bitte Python 3.13 installieren: https://www.python.org/downloads/"
            echo ""
            echo "Drücke Enter zum Beenden..."
            read
            exit 1
        fi
    fi
    echo "✓ pygame installiert."
fi

# ── Alle weiteren Requirements installieren ──
if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    "$VENV_PIP" install -r "$SCRIPT_DIR/requirements.txt" --quiet
fi

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
