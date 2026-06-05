#!/usr/bin/env python3
"""
Cross-Platform Game Starter for Tradegame
Works on Windows, macOS (incl. Apple Silicon M1-M4), and Linux.
Handles: Homebrew-managed Python, Python 3.14+ missing pygame wheels,
         missing SDL libs, externally-managed-environment errors.
"""

import subprocess
import sys
import os
import platform
import shutil
import venv


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(SCRIPT_DIR, ".venv")


def run(cmd, **kwargs):
    return subprocess.run(cmd, **kwargs)


def check_call(cmd):
    subprocess.check_call(cmd)


# ── macOS: SDL libs via Homebrew ─────────────────────────────────────────────

def ensure_sdl_macos():
    if platform.system() != "Darwin":
        return
    brew = shutil.which("brew")
    if not brew:
        print("⚠ Homebrew nicht gefunden. Falls pygame-Installation fehlschlägt:")
        print("   Homebrew installieren: https://brew.sh")
        return

    sdl_packages = ["sdl2", "sdl2_image", "sdl2_mixer", "sdl2_ttf", "pkg-config"]
    missing = []
    for pkg in sdl_packages:
        r = run([brew, "list", pkg], capture_output=True)
        if r.returncode != 0:
            missing.append(pkg)

    if missing:
        print(f"→ Installiere SDL-Bibliotheken via Homebrew: {' '.join(missing)}")
        r = run([brew, "install"] + missing)
        if r.returncode != 0:
            print("⚠ Homebrew-Installation teilweise fehlgeschlagen.")
            print(f"   Manuell: brew install {' '.join(missing)}")
        else:
            print("✓ SDL-Bibliotheken installiert.")


# ── Virtuelle Umgebung ────────────────────────────────────────────────────────

def find_best_python():
    """Prefer Python 3.13 (stable pygame wheels), accept 3.8–3.13, warn on 3.14+."""
    candidates = ["python3.13", "python3.12", "python3.11", "python3.10",
                  "python3.9", "python3.8", "python3", "python"]
    for name in candidates:
        path = shutil.which(name)
        if not path:
            continue
        r = run([path, "-c",
                 "import sys; v=sys.version_info; print(v.major,v.minor)"],
                capture_output=True, text=True)
        if r.returncode != 0:
            continue
        major, minor = map(int, r.stdout.strip().split())
        if major == 3 and minor >= 8:
            return path, major, minor
    return None, 0, 0


def ensure_venv():
    venv_python = os.path.join(VENV_DIR, "Scripts" if sys.platform == "win32" else "bin", "python")
    if os.path.isfile(venv_python):
        return venv_python

    python_exe, major, minor = find_best_python()
    if not python_exe:
        print("✗ Python 3.8+ nicht gefunden.")
        print("  Installieren: https://www.python.org/downloads/")
        if platform.system() == "Darwin":
            print("  Oder: brew install python@3.13")
        sys.exit(1)

    if minor >= 14:
        print(f"⚠ Python {major}.{minor} erkannt. pygame hat für 3.14+ evtl. noch keine fertigen Pakete.")
        print("  Empfohlen: brew install python@3.13  (dann neu starten)")
        print("  Wird trotzdem versucht…")

    print(f"→ Erstelle virtuelle Umgebung mit Python {major}.{minor} ...")
    r = run([python_exe, "-m", "venv", VENV_DIR])
    if r.returncode != 0:
        print("✗ Virtuelle Umgebung konnte nicht erstellt werden.")
        sys.exit(1)
    print("✓ Virtuelle Umgebung erstellt.")
    return venv_python


def venv_pip(venv_python):
    return os.path.join(os.path.dirname(venv_python), "pip")


# ── pygame installieren ───────────────────────────────────────────────────────

def install_pygame(venv_python):
    pip = [venv_python, "-m", "pip"]

    # pip aktualisieren
    run(pip + ["install", "--upgrade", "pip", "--quiet"])

    print("→ Installiere pygame ...")
    r = run(pip + ["install", "pygame"])
    if r.returncode == 0:
        print("✓ pygame installiert.")
        return True

    # Fehlgeschlagen → auf macOS SDL-Pfade setzen und nochmal versuchen
    if platform.system() == "Darwin":
        brew = shutil.which("brew")
        if brew:
            prefix = run([brew, "--prefix"], capture_output=True, text=True).stdout.strip()
            env = os.environ.copy()
            env["PKG_CONFIG_PATH"] = f"{prefix}/lib/pkgconfig"
            env["LDFLAGS"] = f"-L{prefix}/lib"
            env["CPPFLAGS"] = f"-I{prefix}/include"
            print("→ Setze SDL-Pfade und versuche erneut ...")
            r2 = run(pip + ["install", "pygame"], env=env)
            if r2.returncode == 0:
                print("✓ pygame installiert.")
                return True

    print("✗ pygame konnte nicht installiert werden.")
    print("  Lösung: brew install python@3.13  und dann neu starten.")
    return False


def install_requirements(venv_python):
    req = os.path.join(SCRIPT_DIR, "requirements.txt")
    if os.path.isfile(req):
        run([venv_python, "-m", "pip", "install", "-r", req, "--quiet"])


# ── pygame im laufenden Interpreter verfügbar machen ─────────────────────────

def activate_venv(venv_python):
    """Add venv site-packages to sys.path so imports work in this process."""
    r = run([venv_python, "-c",
             "import sys; print('\\n'.join(p for p in sys.path if p))"],
            capture_output=True, text=True)
    if r.returncode == 0:
        for p in r.stdout.splitlines():
            if p not in sys.path:
                sys.path.insert(0, p)


# ── Haupt-Einstiegspunkt ──────────────────────────────────────────────────────

def main():
    os.chdir(SCRIPT_DIR)

    print("=" * 50)
    print("  Tradegame - Multiplayer Börsenspiel")
    print("=" * 50)
    print(f"\nSystem:   {platform.system()} {platform.machine()}")
    print(f"Python:   {sys.version.split()[0]}")
    print()

    # 1. SDL-Bibliotheken auf macOS sicherstellen
    ensure_sdl_macos()

    # 2. Virtuelle Umgebung erstellen / finden
    venv_python = ensure_venv()

    # 3. pygame installieren falls nicht vorhanden
    check_r = run([venv_python, "-c", "import pygame"],
                  capture_output=True)
    if check_r.returncode != 0:
        if not install_pygame(venv_python):
            input("\nDrücke Enter zum Beenden...")
            sys.exit(1)

    # 4. Alle weiteren Abhängigkeiten
    install_requirements(venv_python)

    # 5. Wenn wir bereits in der venv laufen → direkt starten
    in_venv = sys.prefix != sys.base_prefix
    if in_venv or os.path.abspath(sys.executable) == os.path.abspath(venv_python):
        print("\n" + "=" * 50)
        print("  Starte Spiel...")
        print("=" * 50 + "\n")
        try:
            import pygame
            from screens import show_main_menu
            pygame.init()
            show_main_menu()
        except Exception as e:
            import traceback
            print(f"\nFehler beim Starten: {e}")
            traceback.print_exc()
            input("\nDrücke Enter zum Beenden...")
            sys.exit(1)
    else:
        # Neustart mit dem venv-Python
        print("\n" + "=" * 50)
        print("  Starte Spiel...")
        print("=" * 50 + "\n")
        result = run([venv_python, os.path.join(SCRIPT_DIR, "main.py")])
        if result.returncode != 0:
            input("\nDas Spiel wurde mit einem Fehler beendet. Drücke Enter...")
            sys.exit(result.returncode)


if __name__ == "__main__":
    main()
