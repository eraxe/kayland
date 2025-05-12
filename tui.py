#!/usr/bin/env python3
# tui.py - Terminal UI for Kayland using Textual

import sys
import logging
import os
from pathlib import Path
from typing import Optional

# Set up logging
logger = logging.getLogger("kayland.tui")

# Check for Textual package
try:
    import textual
    from textual.app import App

    required_version = "0.30.0"  # Minimum required version
    current_version = getattr(textual, "__version__", "0.0.0")

    from packaging import version

    if version.parse(current_version) < version.parse(required_version):
        logger.error(f"Textual version {current_version} is too old. Please upgrade to {required_version} or newer.")
        print(f"Error: Kayland requires Textual {required_version} or higher.")
        print(f"Please upgrade with: pip install --user textual>={required_version}")
        sys.exit(1)
except ImportError as e:
    logger.error(f"Failed to import Textual: {str(e)}")
    print("Error: The Textual package is required for TUI mode.")
    print("Please install it with: pip install --user textual")
    print("For Arch Linux users: 'sudo pacman -S python-textual' or 'yay -S python-textual'")
    sys.exit(1)

# Import our modules - ensure we use the script directory
script_dir = os.path.dirname(os.path.realpath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Import the modular TUI components
try:
    from tui_app import KaylandTUI
    from tui_utils import Settings
except ImportError:
    # If modular imports fail, create the files in memory
    from tui_generator import generate_tui_modules

    generate_tui_modules()

    # Try again after generation
    try:
        from tui_app import KaylandTUI
        from tui_utils import Settings
    except ImportError as e:
        logger.error(f"Failed to import TUI modules: {str(e)}")
        print(f"Error: Failed to import TUI modules: {str(e)}")
        sys.exit(1)

try:
    from window_manager import WindowManager
    from app_manager import AppManager
except ImportError as e:
    logger.error(f"Failed to import required modules: {str(e)}")
    print(f"Error: Failed to import required modules: {str(e)}")
    sys.exit(1)


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


# Generator for first run
class TUIGenerator:
    """Generates modular TUI files if they don't exist"""

    @staticmethod
    def generate_tui_files():
        from tui_generator import generate_tui_modules
        generate_tui_modules()


if __name__ == "__main__":
    # Check if modules exist and generate if needed
    modules_path = Path(script_dir)
    required_modules = [
        modules_path / "tui_app.py",
        modules_path / "tui_widgets.py",
        modules_path / "tui_screens.py",
        modules_path / "tui_service.py",
        modules_path / "tui_utils.py"
    ]

    if not all(module.exists() for module in required_modules):
        try:
            TUIGenerator.generate_tui_files()
        except Exception as e:
            print(f"Error generating TUI modules: {e}")
            sys.exit(1)

    sys.exit(run_tui())