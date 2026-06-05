@echo off
chcp 65001 >nul
title Tradegame - Starter

echo ========================================
echo   Tradegame - Multiplayer Börsenspiel
echo   Windows Starter
echo ========================================
echo.

:: Als Administrator neu starten falls nötig (für Firewall)
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Starte als Administrator für Firewall-Einrichtung...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

:: ── Python installieren falls nicht vorhanden ──────────────────────────────
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python nicht gefunden. Installiere Python 3.13...
    echo.

    :: Versuche winget
    winget --version >nul 2>&1
    if %errorlevel% == 0 (
        echo Installiere via winget...
        winget install --id Python.Python.3.13 -e --silent --accept-source-agreements --accept-package-agreements
        goto :check_python_again
    )

    :: Fallback: Python-Installer herunterladen
    echo Lade Python 3.13 Installer herunter...
    powershell -Command "& {Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.13.0/python-3.13.0-amd64.exe' -OutFile '%TEMP%\python_installer.exe'}"
    if %errorlevel% neq 0 (
        echo ✗ Download fehlgeschlagen.
        echo   Bitte Python manuell installieren: https://www.python.org/downloads/
        pause
        exit /b 1
    )
    echo Starte Python-Installation (bitte dem Installer folgen)...
    echo WICHTIG: "Add Python to PATH" aktivieren!
    "%TEMP%\python_installer.exe" /passive InstallAllUsers=1 PrependPath=1 Include_test=0
    del "%TEMP%\python_installer.exe"

    :: PATH aktualisieren
    call refreshenv >nul 2>&1
    set "PATH=%PATH%;%LocalAppData%\Programs\Python\Python313;%LocalAppData%\Programs\Python\Python313\Scripts"
    set "PATH=%PATH%;C:\Python313;C:\Python313\Scripts"
    set "PATH=%PATH%;C:\Program Files\Python313;C:\Program Files\Python313\Scripts"
)

:check_python_again
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ Python konnte nicht gefunden werden nach Installation.
    echo   Bitte Terminal neu starten oder Python manuell installieren.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo → Verwende %%v

:: ── Virtuelle Umgebung ─────────────────────────────────────────────────────
if not exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    echo → Erstelle virtuelle Umgebung...
    python -m venv "%SCRIPT_DIR%.venv"
    if %errorlevel% neq 0 (
        echo ✗ Virtuelle Umgebung konnte nicht erstellt werden.
        pause
        exit /b 1
    )
    echo ✓ Virtuelle Umgebung erstellt.
)

set VENV_PYTHON="%SCRIPT_DIR%.venv\Scripts\python.exe"
set VENV_PIP="%SCRIPT_DIR%.venv\Scripts\pip.exe"

:: ── pip aktualisieren ──────────────────────────────────────────────────────
%VENV_PYTHON% -m pip install --upgrade pip --quiet

:: ── pygame und Abhängigkeiten installieren ─────────────────────────────────
%VENV_PYTHON% -c "import pygame" >nul 2>&1
if %errorlevel% neq 0 (
    echo → Installiere pygame...
    %VENV_PIP% install pygame
    if %errorlevel% neq 0 (
        echo ✗ pygame-Installation fehlgeschlagen.
        pause
        exit /b 1
    )
    echo ✓ pygame installiert.
)

if exist "%SCRIPT_DIR%requirements.txt" (
    %VENV_PIP% install -r "%SCRIPT_DIR%requirements.txt" --quiet
)

:: ── Firewall-Regeln einrichten ─────────────────────────────────────────────
echo → Richte Firewall ein (Port 5556)...

netsh advfirewall firewall show rule name="Tradegame" >nul 2>&1
if %errorlevel% neq 0 (
    netsh advfirewall firewall add rule name="Tradegame" dir=in action=allow protocol=TCP localport=5556 >nul
    netsh advfirewall firewall add rule name="Tradegame" dir=out action=allow protocol=TCP localport=5556 >nul
    netsh advfirewall firewall add rule name="Tradegame UDP" dir=in action=allow protocol=UDP localport=5556 >nul
    netsh advfirewall firewall add rule name="Tradegame UDP" dir=out action=allow protocol=UDP localport=5556 >nul
    echo ✓ Firewall-Regeln erstellt.
) else (
    echo ✓ Firewall bereits eingerichtet.
)

:: ── Spiel starten ──────────────────────────────────────────────────────────
echo.
echo ========================================
echo   Starte Spiel...
echo ========================================
echo.

%VENV_PYTHON% "%SCRIPT_DIR%main.py"

if %errorlevel% neq 0 (
    echo.
    echo Das Spiel wurde mit einem Fehler beendet.
    pause
)
