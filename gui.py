#!/usr/bin/env python3
# gui.py - GUI Entry Point for Kayland using PySide6

import sys
import logging
import os
from pathlib import Path

# Set up logging
LOG_DIR = os.path.expanduser("~/.local/share/kayland/logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "kayland_gui.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("kayland.gui")

# Import our modules - ensure we use the script directory
script_dir = os.path.dirname(os.path.realpath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Check for PySide6 package
try:
    # Import core PySide6 modules, including QAction from the right place
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QCoreApplication, Qt
    from PySide6.QtGui import QAction, QIcon  # QAction is in QtGui, not QtWidgets
except ImportError as e:
    logger.error(f"Failed to import PySide6: {str(e)}")
    print("Error: The PySide6 package is required for GUI mode.")
    print("Please install it with: sudo pacman -S python-pyside6")
    sys.exit(1)

# Import the required modules with better error handling
try:
    # Try importing each module separately to isolate which one fails
    try:
        from window_manager import WindowManager
    except ImportError as e:
        logger.error(f"Failed to import WindowManager: {str(e)}")
        raise

    try:
        from app_manager import AppManager
    except ImportError as e:
        logger.error(f"Failed to import AppManager: {str(e)}")
        raise

    try:
        from gui_utils import Settings
    except ImportError as e:
        logger.error(f"Failed to import Settings: {str(e)}")
        raise

    try:
        from gui_app import KaylandGUI
    except ImportError as e:
        # This is likely the problematic import
        logger.error(f"Failed to import KaylandGUI: {str(e)}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

except ImportError as e:
    logger.error(f"Failed to import required modules: {str(e)}")
    print(f"Error: Failed to import required modules: {str(e)}")
    sys.exit(1)


def get_asset_path(file_name):
    """Get the correct path to an asset file considering various installation scenarios"""
    # Try multiple possible locations
    potential_paths = [
        # Check for assets in the same directory as the script
        os.path.join(os.path.dirname(__file__), file_name),
        # Check for assets in the parent directory
        os.path.join(os.path.dirname(os.path.dirname(__file__)), file_name),
        # Check for assets in a dedicated assets directory
        os.path.join(os.path.dirname(__file__), "assets", file_name),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", file_name),
        # Check for system-wide installation
        os.path.expanduser(f"~/.local/share/kayland/assets/{file_name}"),
        # More general install locations
        f"/usr/share/kayland/assets/{file_name}",
        f"/usr/local/share/kayland/assets/{file_name}"
    ]

    for path in potential_paths:
        if os.path.exists(path):
            return path

    # If no file is found, log a warning but return the first path anyway
    logger.warning(f"Asset file not found: {file_name}")
    return potential_paths[0]


def check_environment():
    """Check if running on KDE Wayland with kdotool available"""
    # Check for Wayland
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if "wayland" not in session_type:
        logger.warning(f"Kayland is designed for Wayland. Current session: {session_type}")
        print(f"Warning: Kayland is designed for Wayland. Current session: {session_type}")

    # Check for KDE
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    if "kde" not in desktop:
        logger.warning(f"Kayland is designed for KDE. Current desktop: {desktop}")
        print(f"Warning: Kayland is designed for KDE. Current desktop: {desktop}")

    # Check for kdotool - this is a hard requirement for window management
    try:
        import subprocess
        subprocess.run(["which", "kdotool"], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        logger.error("kdotool is required but not found.")
        print("Error: kdotool is required but not found.")
        print("Please install kdotool first: https://github.com/jinliu/kdotool")
        return False

# Create scripts directory if it doesn't exist
def setup_scripts_dir():
    """Setup scripts directory in config folder"""
    scripts_dir = os.path.expanduser("~/.config/kayland/scripts")
    os.makedirs(scripts_dir, exist_ok=True)
    return scripts_dir

def run_gui():
    """Run the Kayland GUI"""
    try:
        # Check environment first
        if not check_environment():
            print("Error: kdotool is required for window management. See log for details.")
            return 1

        # Setup scripts directory
        setup_scripts_dir()

        # Initialize managers
        window_manager = WindowManager()
        app_manager = AppManager()
        settings = Settings()

        # Initialize QApplication
        QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
        app = QApplication(sys.argv)

        # Set app icon
        icon_path = get_asset_path("kayland.png")
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))

        # Create and show the GUI
        main_window = KaylandGUI(window_manager, app_manager, settings)
        main_window.show()

        return app.exec()
    except Exception as e:
        logger.error(f"Error running GUI: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        print(f"Error running GUI: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(run_gui())