#!/bin/bash
# Tradegame Linux Launcher
# Unterstützt: Ubuntu/Debian, Fedora/RHEL, Arch Linux, openSUSE
# Installiert automatisch: Python 3, SDL-Libs, pygame, Firewall-Freigabe (ufw/firewalld)

cd "$(dirname "$0")"
SCRIPT_DIR="$(pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "========================================"
echo "  Tradegame - Multiplayer Börsenspiel"
echo "  Linux Starter"
echo "========================================"
echo ""

# ── Paketmanager erkennen ─────────────────────────────────────────────────────
detect_pkg_manager() {
    if command -v apt-get &> /dev/null; then echo "apt"
    elif command -v dnf &> /dev/null; then echo "dnf"
    elif command -v pacman &> /dev/null; then echo "pacman"
    elif command -v zypper &> /dev/null; then echo "zypper"
    else echo "unknown"
    fi
}
PKG_MGR=$(detect_pkg_manager)
echo "→ Erkannter Paketmanager: $PKG_MGR"

install_pkg() {
    case "$PKG_MGR" in
        apt)    sudo apt-get install -y "$@" ;;
        dnf)    sudo dnf install -y "$@" ;;
        pacman) sudo pacman -S --noconfirm "$@" ;;
        zypper) sudo zypper install -y "$@" ;;
        *)      echo "✗ Unbekannter Paketmanager. Bitte manuell installieren: $*"; return 1 ;;
    esac
}

# ── Python 3 installieren falls nicht vorhanden ───────────────────────────────
PYTHON_CMD=""
for candidate in python3.13 python3.12 python3.11 python3.10 python3 python; do
    if command -v "$candidate" &> /dev/null; then
        OK=$("$candidate" -c "import sys; print(sys.version_info >= (3,8))" 2>/dev/null)
        if [ "$OK" = "True" ]; then
            PYTHON_CMD="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "→ Python 3 nicht gefunden. Installiere..."
    case "$PKG_MGR" in
        apt)    sudo apt-get update -qq && install_pkg python3 python3-venv python3-pip ;;
        dnf)    install_pkg python3 python3-pip ;;
        pacman) install_pkg python python-pip ;;
        zypper) install_pkg python3 python3-pip ;;
    esac
    PYTHON_CMD="python3"
fi

echo "→ Verwende Python: $($PYTHON_CMD --version)"

# ── python3-venv sicherstellen ────────────────────────────────────────────────
if ! "$PYTHON_CMD" -m venv --help &> /dev/null; then
    echo "→ Installiere python3-venv..."
    case "$PKG_MGR" in
        apt)    install_pkg python3-venv ;;
        dnf)    install_pkg python3-venv ;;
        pacman) : ;;  # in python enthalten
        zypper) install_pkg python3-venv ;;
    esac
fi

# ── SDL-Bibliotheken installieren ─────────────────────────────────────────────
SDL_CHECK=$(python3 -c "import ctypes; ctypes.CDLL('libSDL2-2.0.so.0')" 2>&1)
if [[ $SDL_CHECK == *"Error"* ]] || [[ $SDL_CHECK == *"No such"* ]]; then
    echo "→ Installiere SDL-Bibliotheken..."
    case "$PKG_MGR" in
        apt)    install_pkg libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev ;;
        dnf)    install_pkg SDL2-devel SDL2_image-devel SDL2_mixer-devel SDL2_ttf-devel ;;
        pacman) install_pkg sdl2 sdl2_image sdl2_mixer sdl2_ttf ;;
        zypper) install_pkg libSDL2-devel libSDL2_image-devel libSDL2_mixer-devel libSDL2_ttf-devel ;;
    esac
    echo "✓ SDL-Bibliotheken installiert."
fi

# ── Virtuelle Umgebung ────────────────────────────────────────────────────────
if [ ! -f "$VENV_DIR/bin/python" ]; then
    echo "→ Erstelle virtuelle Umgebung..."
    "$PYTHON_CMD" -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "✗ Virtuelle Umgebung konnte nicht erstellt werden."
        read -p "Drücke Enter zum Beenden..."; exit 1
    fi
    echo "✓ Virtuelle Umgebung erstellt."
fi

VENV_PYTHON="$VENV_DIR/bin/python"

# ── pip aktualisieren ─────────────────────────────────────────────────────────
"$VENV_PYTHON" -m pip install --upgrade pip --quiet

# ── pygame und Abhängigkeiten installieren ────────────────────────────────────
if ! "$VENV_PYTHON" -c "import pygame" &> /dev/null; then
    echo "→ Installiere pygame..."
    "$VENV_PYTHON" -m pip install pygame
    if [ $? -ne 0 ]; then
        echo "✗ pygame-Installation fehlgeschlagen."
        read -p "Drücke Enter zum Beenden..."; exit 1
    fi
    echo "✓ pygame installiert."
fi

if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    "$VENV_PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt" --quiet
fi

# ── Firewall freigeben (Port 5556) ────────────────────────────────────────────
echo "→ Richte Firewall ein (Port 5556)..."
FIREWALL_DONE=false

if command -v ufw &> /dev/null; then
    UFW_STATUS=$(sudo ufw status 2>/dev/null | head -1)
    if echo "$UFW_STATUS" | grep -qi "active"; then
        sudo ufw allow 5556/tcp comment "Tradegame" 2>/dev/null
        sudo ufw allow 5556/udp comment "Tradegame" 2>/dev/null
        echo "✓ ufw: Port 5556 freigegeben."
        FIREWALL_DONE=true
    fi
fi

if [ "$FIREWALL_DONE" = false ] && command -v firewall-cmd &> /dev/null; then
    if systemctl is-active --quiet firewalld 2>/dev/null; then
        sudo firewall-cmd --permanent --add-port=5556/tcp 2>/dev/null
        sudo firewall-cmd --permanent --add-port=5556/udp 2>/dev/null
        sudo firewall-cmd --reload 2>/dev/null
        echo "✓ firewalld: Port 5556 freigegeben."
        FIREWALL_DONE=true
    fi
fi

if [ "$FIREWALL_DONE" = false ] && command -v iptables &> /dev/null; then
    sudo iptables -C INPUT -p tcp --dport 5556 -j ACCEPT 2>/dev/null || \
        sudo iptables -A INPUT -p tcp --dport 5556 -j ACCEPT 2>/dev/null
    sudo iptables -C INPUT -p udp --dport 5556 -j ACCEPT 2>/dev/null || \
        sudo iptables -A INPUT -p udp --dport 5556 -j ACCEPT 2>/dev/null
    echo "✓ iptables: Port 5556 freigegeben."
    FIREWALL_DONE=true
fi

[ "$FIREWALL_DONE" = false ] && echo "  Keine aktive Firewall gefunden, keine Aktion nötig."

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
    read -p "Drücke Enter zum Beenden..."
fi
