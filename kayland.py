#!/usr/bin/env python3
# kayland.py - Main entry point for Kayland

import argparse
import logging
import os
import subprocess
import sys
import re
from typing import List, Dict, Optional, Any

# Set up logging
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

logger = logging.getLogger("kayland")

# Import our modules - ensure we use the script directory
script_dir = os.path.dirname(os.path.realpath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Check for required dependencies before continuing
try:
    from window_manager import WindowManager
    from app_manager import AppManager
except ImportError as e:
    logger.error(f"Failed to import required modules: {str(e)}")
    print(f"Error: Failed to import required modules: {str(e)}")
    print("Please make sure all Kayland files are in the correct location.")
    sys.exit(1)

# Try to import textual, needed for TUI
has_textual = True
try:
    import textual
except ImportError:
    has_textual = False
    logger.warning("Textual package not found. TUI mode will not be available.")


def check_environment() -> bool:
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
        subprocess.run(["which", "kdotool"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        logger.error("kdotool is required but not found.")
        print("Error: kdotool is required but not found.")
        print("Please install kdotool first: https://github.com/jinliu/kdotool")
        return False

    return True


def update_kayland() -> bool:
    """Update Kayland from the GitHub repository"""
    try:
        # Run the installer script with the --update flag
        update_script = """
        curl -sSL https://raw.githubusercontent.com/eraxe/kayland/main/install.sh | bash -s -- --update
        """
        result = subprocess.run(["bash", "-c", update_script], capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"Update failed: {result.stderr}")
            print(f"Update failed: {result.stderr}")
            return False

        logger.info("Kayland updated successfully")
        print("Kayland updated successfully")
        return True
    except Exception as e:
        logger.error(f"Update failed: {str(e)}")
        print(f"Update failed: {str(e)}")
        return False


def list_apps(app_manager: AppManager, verbose: bool = False) -> None:
    """List all defined applications"""
    apps = app_manager.get_all_apps()

    if not apps:
        print("No applications defined. Use 'kayland add' to add an application.")
        return

    # Determine max lengths for formatting
    max_name = max([len(app["name"]) for app in apps], default=4)
    max_aliases = max([len(",".join(app.get("aliases", []))) for app in apps], default=7)

    # Print header
    print(f"{'Name':<{max_name + 2}} {'Aliases':<{max_aliases + 2}} {'Class Pattern'}")
    print(f"{'-' * max_name} {'-' * max_aliases} {'-' * 12}")

    # Print apps
    for app in apps:
        aliases = ",".join(app.get("aliases", []))
        print(f"{app['name']:<{max_name + 2}} {aliases:<{max_aliases + 2}} {app['class_pattern']}")

        if verbose:
            print(f"  Command: {app['command']}")
            print(f"  ID: {app['id']}")
            print()


def run_tui():
    """Run the Kayland TUI"""
    if not has_textual:
        print("Error: The Textual package is required for TUI mode.")
        print("Please install it with: pip install --user textual")
        sys.exit(1)

    try:
        # Import the TUI module
        from tui import run_tui
        run_tui()
    except ImportError as e:
        logger.error(f"Failed to import TUI module: {str(e)}")
        print(f"Error: Failed to import TUI module: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error running TUI: {str(e)}")
        print(f"Error running TUI: {str(e)}")
        sys.exit(1)


def main():
    """Main entry point for Kayland"""
    parser = argparse.ArgumentParser(description="Kayland - KDE Wayland Window Manager")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # TUI command (default)
    tui_parser = subparsers.add_parser("tui", help="Launch the Terminal UI")

    # Launch command
    launch_parser = subparsers.add_parser("launch", help="Launch or toggle an application")
    launch_parser.add_argument("alias", help="Application alias or ID")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new application")
    add_parser.add_argument("--name", required=True, help="Application name")
    add_parser.add_argument("--alias", dest="aliases", action="append",
                            help="Application alias (can be specified multiple times)")
    add_parser.add_argument("--class", dest="class_pattern", required=True,
                            help="Window class pattern (regular expression)")
    add_parser.add_argument("--command", required=True, help="Launch command")

    # List command
    list_parser = subparsers.add_parser("list", help="List defined applications")
    list_parser.add_argument("--verbose", "-v", action="store_true", help="Show verbose output")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update Kayland")

    # Uninstall command
    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall Kayland")

    # Parse arguments
    args = parser.parse_args()

    # Process uninstall command
    if args.command == "uninstall":
        print("Uninstalling Kayland...")
        subprocess.run(["bash", "-c",
                        "curl -sSL https://raw.githubusercontent.com/eraxe/kayland/main/install.sh | bash -s -- --uninstall"])
        return 0

    # Process update command
    if args.command == "update":
        return 0 if update_kayland() else 1

    # Check environment for all other commands that involve window management
    if args.command == "launch" and not check_environment():
        print("Error: kdotool is required for window management. See log for details.")
        return 1

    # Initialize app manager for all commands
    try:
        app_manager = AppManager()
    except Exception as e:
        logger.error(f"Failed to initialize AppManager: {str(e)}")
        print(f"Error: Failed to initialize AppManager: {str(e)}")
        return 1

    # Process commands
    if args.command == "tui" or args.command is None:
        # Launch TUI
        run_tui()
    elif args.command == "launch":
        # Launch or toggle application
        try:
            window_manager = WindowManager()
        except Exception as e:
            logger.error(f"Failed to initialize WindowManager: {str(e)}")
            print(f"Error: Failed to initialize WindowManager: {str(e)}")
            return 1

        app = app_manager.get_app_by_alias(args.alias)
        if not app:
            app = app_manager.get_app_by_id(args.alias)

        if not app:
            print(f"Error: No application found with alias or ID '{args.alias}'")
            return 1

        result, success = window_manager.toggle_window(app["class_pattern"], app["command"])
        print(result)
        return 0 if success else 1
    elif args.command == "add":
        # Add a new application
        aliases = args.aliases if args.aliases else []
        app = app_manager.add_app(args.name, args.class_pattern, args.command, aliases)
        print(f"Added application: {app['name']}")
    elif args.command == "list":
        # List applications
        list_apps(app_manager, args.verbose)
    else:
        parser.print_help()

    return 0


if __name__ == "__main__":
    sys.exit(main())