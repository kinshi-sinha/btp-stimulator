#!/bin/bash
# IIoT Traffic Simulator - macOS launcher
# Double-click this file to start the simulator GUI.

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
    echo ""
    echo "  ERROR: Python 3 is not installed."
    echo ""
    echo "  Please install Python 3.10 or newer from:"
    echo "    https://www.python.org/downloads/"
    echo ""
    echo "  IMPORTANT: install from python.org (NOT Homebrew),"
    echo "  because the python.org installer includes tkinter,"
    echo "  which this app needs."
    echo ""
    read -n 1 -s -r -p "Press any key to close..."
    exit 1
fi

if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    echo ""
    echo "  ERROR: tkinter is not available in your Python install."
    echo ""
    echo "  Easiest fix: install Python from https://www.python.org/downloads/"
    echo "  (the python.org installer bundles tkinter)."
    echo ""
    echo "  Or, if using Homebrew Python:"
    echo "    brew install python-tk@3.12"
    echo ""
    read -n 1 -s -r -p "Press any key to close..."
    exit 1
fi

python3 main.py
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "  The simulator exited with an error. See messages above."
    read -n 1 -s -r -p "Press any key to close..."
fi
