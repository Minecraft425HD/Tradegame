#!/usr/bin/env python3
"""
Cross-Platform Game Starter for Tradegame
Works on Windows, macOS, and Linux
"""

import subprocess
import sys
import os

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required!")
        print(f"Current version: {sys.version}")
        sys.exit(1)

def check_dependencies():
    """Check if required packages are installed."""
    try:
        import pygame
        print(f"✓ Pygame {pygame.version.ver} found")
        return True
    except ImportError:
        print("✗ Pygame not found")
        return False

def install_dependencies():
    """Install required packages."""
    print("\nInstalling dependencies...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("✓ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install dependencies: {e}")
        return False

def main():
    """Main entry point."""
    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    print("=" * 50)
    print("  Tradegame - Multiplayer Börsenspiel")
    print("=" * 50)
    print(f"\nPlatform: {sys.platform}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Working Directory: {os.getcwd()}")
    print()

    # Check Python version
    check_python_version()

    # Check and install dependencies if needed
    if not check_dependencies():
        print("\nWould you like to install the required dependencies? (y/n)")
        response = input("> ").strip().lower()
        if response in ['y', 'yes', 'ja', 'j']:
            if not install_dependencies():
                print("\nPlease install dependencies manually:")
                print("  pip install -r requirements.txt")
                sys.exit(1)
        else:
            print("\nPlease install dependencies manually:")
            print("  pip install -r requirements.txt")
            sys.exit(1)

    print("\n" + "=" * 50)
    print("  Starting Game...")
    print("=" * 50 + "\n")

    # Import and start the game
    try:
        import pygame
        from screens import show_main_menu

        pygame.init()
        show_main_menu()

    except Exception as e:
        print(f"\nError starting game: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
