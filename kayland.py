#!/usr/bin/env python3
# kayland.py - Main entry point for Kayland

import argparse
import logging
import os
import subprocess
import sys
import re
import socket
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

# Try to import PySide6, needed for GUI
has_pyside6 = True
try:
    import PySide6
except ImportError:
    has_pyside6 = False
    logger.warning("PySide6 package not found. GUI mode will not be available.")


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


def list_shortcuts(app_manager: AppManager, verbose: bool = False) -> None:
    """List all defined shortcuts"""
    shortcuts = app_manager.get_shortcuts()

    if not shortcuts:
        print("No shortcuts defined. Use 'kayland shortcut add' to add a shortcut.")
        return

    # Determine max lengths for formatting
    max_key = max([len(shortcut["key"]) for shortcut in shortcuts], default=4)
    max_desc = max([len(shortcut.get("description", "")) for shortcut in shortcuts], default=11)

    # Print header
    print(f"{'Key':<{max_key + 2}} {'App':<15} {'Description'}")
    print(f"{'-' * max_key} {'-' * 15} {'-' * 11}")

    # Print shortcuts
    for shortcut in shortcuts:
        app_id = shortcut["app_id"]
        app = app_manager.get_app_by_id(app_id)
        app_name = app["name"] if app else "Unknown"
        desc = shortcut.get("description", "")

        print(f"{shortcut['key']:<{max_key + 2}} {app_name:<15} {desc}")

        if verbose:
            print(f"  App ID: {app_id}")
            print(f"  Shortcut ID: {shortcut['id']}")
            print()


def run_service_mode():
    """Run Kayland as a background service that listens for shortcut triggers"""
    logger.info("Starting Kayland service mode")

    # Initialize managers
    app_manager = AppManager()
    window_manager = WindowManager()

    # Create socket for IPC
    socket_path = os.path.expanduser("~/.cache/kayland/kayland.sock")
    os.makedirs(os.path.dirname(socket_path), exist_ok=True)

    if os.path.exists(socket_path):
        os.unlink(socket_path)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(socket_path)
    server.listen(5)

    logger.info(f"Listening on socket: {socket_path}")

    # Register configured shortcuts
    register_shortcuts(app_manager, window_manager)

    # Main service loop
    try:
        while True:
            conn, addr = server.accept()
            data = conn.recv(1024).decode('utf-8')

            if data:
                logger.info(f"Received command: {data}")
                parts = data.strip().split(':', 1)

                if len(parts) == 2:
                    command, arg = parts

                    if command == "launch":
                        app = app_manager.get_app_by_id(arg) or app_manager.get_app_by_alias(arg)

                        if app:
                            result, success = window_manager.toggle_window(
                                app["class_pattern"], app["command"]
                            )
                            logger.info(f"Launch result: {result}")
                            conn.sendall(f"OK: {result}".encode('utf-8'))
                        else:
                            conn.sendall(f"ERROR: App not found: {arg}".encode('utf-8'))

                    elif command == "status":
                        conn.sendall(b"OK: Service is running")

                    elif command == "reload":
                        # Reload app configurations
                        app_manager = AppManager()
                        register_shortcuts(app_manager, window_manager)
                        conn.sendall(b"OK: Configuration reloaded")

                    else:
                        conn.sendall(f"ERROR: Unknown command: {command}".encode('utf-8'))
                else:
                    conn.sendall(b"ERROR: Invalid command format")

            conn.close()

    except KeyboardInterrupt:
        logger.info("Service shutting down")
    finally:
        server.close()
        if os.path.exists(socket_path):
            os.unlink(socket_path)


def register_shortcuts(app_manager, window_manager):
    """Register all shortcuts with kdotool"""
    shortcuts = app_manager.get_shortcuts()
    logger.info(f"Registering {len(shortcuts)} shortcuts")

    for shortcut in shortcuts:
        app_id = shortcut.get("app_id")
        app = app_manager.get_app_by_id(app_id)

        if app:
            try:
                app_manager._register_kdotool_shortcut(shortcut, app)
                logger.info(f"Registered shortcut: {shortcut['key']} -> {app['name']}")
            except Exception as e:
                logger.error(f"Failed to register shortcut {shortcut['key']}: {str(e)}")


def run_gui():
    """Run the Kayland GUI"""
    if not has_pyside6:
        print("Error: The PySide6 package is required for GUI mode.")
        print("Please install it with: pip install --user pyside6")
        print("For Arch Linux users: 'sudo pacman -S python-pyside6' or 'yay -S python-pyside6'")
        sys.exit(1)

    try:
        # Check environment first - this is important
        if not check_environment():
            print("Error: kdotool is required for window management. See log for details.")
            sys.exit(1)

        # Import the GUI module
        from gui import run_gui
        return run_gui()
    except ImportError as e:
        logger.error(f"Failed to import GUI module: {str(e)}")
        print(f"Error: Failed to import GUI module: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error running GUI: {str(e)}")
        print(f"Error running GUI: {str(e)}")
        sys.exit(1)


# Commented out TUI function
"""
def run_tui():
    #Run the Kayland TUI
    if not has_textual:
        print("Error: The Textual package is required for TUI mode.")
        print("Please install it with: pip install --user textual")
        sys.exit(1)

    try:
        # Check environment first - this is important
        if not check_environment():
            print("Error: kdotool is required for window management. See log for details.")
            sys.exit(1)

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
"""


def main():
    """Main entry point for Kayland"""
    parser = argparse.ArgumentParser(description="Kayland - KDE Wayland Window Manager")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # GUI command (default)
    gui_parser = subparsers.add_parser("gui", help="Launch the GUI")

    # TUI command (still available but commented out in implementation)
    tui_parser = subparsers.add_parser("tui", help="Launch the Terminal UI (Deprecated)")

    # Launch command
    launch_parser = subparsers.add_parser("launch", help="Launch or toggle an application")
    launch_parser.add_argument("alias", help="Application alias, name, or ID")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new application")
    add_parser.add_argument("--name", required=True, help="Application name")
    add_parser.add_argument("--alias", dest="aliases", action="append",
                            help="Application alias (can be specified multiple times)")
    add_parser.add_argument("--class", dest="class_pattern", required=True,
                            help="Window class pattern (substring to match)")
    add_parser.add_argument("--command", required=True, help="Launch command")

    # List command
    list_parser = subparsers.add_parser("list", help="List defined applications")
    list_parser.add_argument("--verbose", "-v", action="store_true", help="Show verbose output")

    # Shortcut commands
    shortcut_parser = subparsers.add_parser("shortcut", help="Manage keyboard shortcuts")
    shortcut_subparsers = shortcut_parser.add_subparsers(dest="shortcut_command", help="Shortcut command")

    # Add shortcut
    shortcut_add = shortcut_subparsers.add_parser("add", help="Add a new shortcut")
    shortcut_add.add_argument("--app", required=True, help="Application name, alias, or ID")
    shortcut_add.add_argument("--key", required=True, help="Shortcut key (e.g., 'alt+b')")
    shortcut_add.add_argument("--description", help="Optional description")

    # List shortcuts
    shortcut_list = shortcut_subparsers.add_parser("list", help="List all shortcuts")
    shortcut_list.add_argument("--verbose", "-v", action="store_true", help="Show verbose output")

    # Remove shortcut
    shortcut_remove = shortcut_subparsers.add_parser("remove", help="Remove a shortcut")
    shortcut_remove.add_argument("key", help="Shortcut key to remove")

    # Service commands
    service_parser = subparsers.add_parser("service", help="Manage the Kayland service")
    service_subparsers = service_parser.add_subparsers(dest="service_command", help="Service command")

    # Service install
    service_install = service_subparsers.add_parser("install", help="Install and start the service")

    # Service status
    service_status = service_subparsers.add_parser("status", help="Check service status")

    # Service stop
    service_stop = service_subparsers.add_parser("stop", help="Stop the service")

    # Service uninstall
    service_uninstall = service_subparsers.add_parser("uninstall", help="Uninstall the service")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update Kayland")

    # Uninstall command
    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall Kayland")

    # Debug command
    debug_parser = subparsers.add_parser("debug", help="Debug tools")
    debug_parser.add_argument("--window-info", action="store_true", help="Show information about all windows")
    debug_parser.add_argument("--search", help="Search for windows with a pattern")

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

    # Process service command
    if args.command == "service":
        # Get current directory to run installer script properly
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # Service commands
        if args.service_command == "install":
            # Use install.sh to install the service
            subprocess.run(["bash", "-c",
                            f"cd {current_dir} && ../install.sh --service-only"])
            return 0

        elif args.service_command == "status":
            # Check service status
            result = subprocess.run(["systemctl", "--user", "status", "kayland.service"],
                                    check=False, capture_output=False)
            return result.returncode

        elif args.service_command == "stop":
            # Stop the service
            result = subprocess.run(["systemctl", "--user", "stop", "kayland.service"],
                                    check=False, capture_output=True, text=True)
            if result.returncode == 0:
                print("Kayland service stopped")
            else:
                print(f"Failed to stop service: {result.stderr}")
            return result.returncode

        elif args.service_command == "uninstall":
            # Uninstall service
            subprocess.run(["bash", "-c",
                            f"cd {current_dir} && ../install.sh --service-only --uninstall"])
            return 0

        else:
            # Run in service mode
            logger.info("Starting Kayland in service mode")
            return run_service_mode() or 0

    # Process shortcut commands
    if args.command == "shortcut":
        # Check environment first
        if not check_environment():
            print("Error: kdotool is required for shortcut management")
            return 1

        try:
            app_manager = AppManager()
        except Exception as e:
            logger.error(f"Failed to initialize AppManager: {str(e)}")
            print(f"Error: Failed to initialize AppManager: {str(e)}")
            return 1

        if args.shortcut_command == "list":
            list_shortcuts(app_manager, args.verbose)
            return 0

        elif args.shortcut_command == "add":
            try:
                # Find app by name, alias, or ID
                app = app_manager.get_app_by_name(args.app)
                if not app:
                    app = app_manager.get_app_by_alias(args.app)
                if not app:
                    app = app_manager.get_app_by_id(args.app)

                if not app:
                    print(f"Error: No application found with name, alias, or ID '{args.app}'")
                    return 1

                # Add shortcut
                description = args.description or ""
                shortcut = app_manager.add_shortcut(app["id"], args.key, description)
                print(f"Added shortcut: {args.key} for {app['name']}")
                return 0

            except Exception as e:
                print(f"Error adding shortcut: {str(e)}")
                return 1

        elif args.shortcut_command == "remove":
            try:
                # Find shortcut by key
                shortcuts = app_manager.get_shortcuts()
                for shortcut in shortcuts:
                    if shortcut["key"] == args.key:
                        app_manager.remove_shortcut(shortcut["id"])
                        print(f"Removed shortcut: {args.key}")
                        return 0

                print(f"Error: No shortcut found with key '{args.key}'")
                return 1

            except Exception as e:
                print(f"Error removing shortcut: {str(e)}")
                return 1

        else:
            print("Unknown shortcut command. Use 'kayland shortcut --help' for options.")
            return 1

    # Process debug commands
    if args.command == "debug":
        if args.window_info:
            script_path = os.path.join(script_dir, "window_info.sh")
            if os.path.exists(script_path):
                subprocess.run(["bash", script_path])
            else:
                print(f"Error: Debug script not found at {script_path}")
            return 0
        elif args.search:
            try:
                window_manager = WindowManager()
                found_windows = window_manager._find_matching_windows_direct(args.search)
                print(f"Found {len(found_windows)} windows matching '{args.search}':")
                for i, win in enumerate(found_windows):
                    print(f"\n[{i + 1}] Window ID: {win['id']}")
                    print(f"    Class: {win['class']}")
                    print(f"    Resource Name: {win.get('classname', '')}")
                    print(f"    Title: {win.get('caption', '')}")
                    print(f"    Active: {win.get('is_active', False)}")
                    print(f"    Match Reason: {win.get('match_reason', 'unknown')}")
            except Exception as e:
                print(f"Error searching for windows: {str(e)}")
            return 0

    # If no command is provided or command is 'gui', launch the GUI (now the default)
    if args.command is None or args.command == "gui":
        # Launch GUI
        return run_gui() or 0

    # If command is 'tui', inform user of deprecation
    if args.command == "tui":
        print("Note: The TUI interface is deprecated in favor of the new GUI.")
        print("You can still use it by uncommenting the TUI code in kayland.py")
        print("For now, launching the GUI instead...")
        return run_gui() or 0

    # For other commands that involve window management, check environment
    if not check_environment():
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
    if args.command == "launch":
        # Launch or toggle application
        try:
            window_manager = WindowManager()
        except Exception as e:
            logger.error(f"Failed to initialize WindowManager: {str(e)}")
            print(f"Error: Failed to initialize WindowManager: {str(e)}")
            return 1

        # Try finding the app by alias first
        app = app_manager.get_app_by_alias(args.alias)

        # If not found by alias, try by name
        if not app:
            app = app_manager.get_app_by_name(args.alias)

        # If still not found, try by ID
        if not app:
            app = app_manager.get_app_by_id(args.alias)

        if not app:
            print(f"Error: No application found with alias, name, or ID '{args.alias}'")
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