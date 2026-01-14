#!/bin/bash
# Tradegame Starter for macOS/Linux

echo "========================================"
echo "  Tradegame - Multiplayer Börsenspiel"
echo "========================================"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check for Python 3
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python not found!"
    echo "Please install Python 3.8 or higher."
    exit 1
fi

echo "Using: $PYTHON_CMD"
echo ""

# Run the game
$PYTHON_CMD start_game.py

# Keep terminal open on error
if [ $? -ne 0 ]; then
    echo ""
    echo "Press Enter to close..."
    read
fi
