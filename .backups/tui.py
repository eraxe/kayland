#!/usr/bin/env python3
# tui.py - Terminal UI for Kayland using Textual

import sys
import logging
import os
from pathlib import Path
from typing import Optional

# Simple logging setup
LOG_DIR = os.path.expanduser("~/.local/share/kayland/logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "kayland.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("kayland.tui")

# Import our modules - ensure we use the script directory
script_dir = os.path.dirname(os.path.realpath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Check dependencies
try:
    from window_manager import WindowManager
    from app_manager import AppManager
except ImportError as e:
    logger.error(f"Failed to import required modules: {str(e)}")
    print(f"Error: Failed to import required modules: {str(e)}")
    sys.exit(1)

# Check for Textual package
try:
    import textual
    from textual.app import App
except ImportError:
    logger.error("Textual package not found")
    print("Error: The Textual package is required for TUI mode.")
    print("Please install it with: pip install --user textual")
    sys.exit(1)

# Import the TUI app
from tui_app import KaylandTUI
from tui_utils import Settings

def run_tui():
    """Run the Kayland TUI"""
    try:
        # Initialize managers
        window_manager = WindowManager()
        app_manager = AppManager()
        settings = Settings()

        # Create and run the TUI
        app = KaylandTUI(window_manager, app_manager, settings)
        app.run()
        return 0
    except Exception as e:
        logger.error(f"Error running TUI: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        print(f"Error running TUI: {str(e)}")
        return 1

if __name__ == "__main__":
    print("Starting Kayland TUI...")
    sys.exit(run_tui())