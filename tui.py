#!/usr/bin/env python3
# tui.py - Terminal UI for Kayland using Textual

import sys
import logging
import os
from typing import Dict, Any, Optional

# Set up logging
logger = logging.getLogger("kayland.tui")

# Check for Textual package
try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, Vertical
    from textual.widgets import Header, Footer, Button, Static, Input, ListView, ListItem
    from textual.screen import Screen
    from textual import events
except ImportError as e:
    logger.error(f"Failed to import Textual: {str(e)}")
    print("Error: The Textual package is required for TUI mode.")
    print("Please install it with: pip install --user textual")
    sys.exit(1)

# Import our modules - ensure we use the script directory
script_dir = os.path.dirname(os.path.realpath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

try:
    from window_manager import WindowManager
    from app_manager import AppManager
except ImportError as e:
    logger.error(f"Failed to import required modules: {str(e)}")
    print(f"Error: Failed to import required modules: {str(e)}")
    sys.exit(1)


class AppListItem(ListItem):
    """A list item representing an application"""

    def __init__(self, app: Dict[str, Any]):
        super().__init__()
        self.app = app

    def compose(self) -> ComposeResult:
        yield Static(f"{self.app['name']} ({', '.join(self.app.get('aliases', []))})")

    def on_click(self) -> None:
        self.app_selected(self.app["id"])

    def app_selected(self, app_id: str) -> None:
        """Called when an app is selected"""
        self.post_message(AppSelectedMessage(app_id))


class AppSelectedMessage(events.Message):
    """Message sent when an app is selected"""

    def __init__(self, app_id: str):
        super().__init__()
        self.app_id = app_id


class AppFormScreen(Screen):
    """Screen for adding or editing an app"""

    def __init__(self, app_manager: AppManager, app_id: str = None):
        super().__init__()
        self.app_manager = app_manager
        self.app_id = app_id
        self.app = None

        if app_id:
            self.app = app_manager.get_app_by_id(app_id)

    def compose(self) -> ComposeResult:
        is_edit = self.app is not None

        with Container():
            yield Header(f"{'Edit' if is_edit else 'Add'} Application")

            with Vertical():
                yield Static("Name:")
                yield Input(
                    id="name",
                    value=self.app["name"] if is_edit else "",
                    placeholder="Application name"
                )

                yield Static("Class Pattern:")
                yield Input(
                    id="class_pattern",
                    value=self.app["class_pattern"] if is_edit else "",
                    placeholder="Window class pattern (regular expression)"
                )

                yield Static("Command:")
                yield Input(
                    id="command",
                    value=self.app["command"] if is_edit else "",
                    placeholder="Launch command"
                )

                yield Static("Aliases (comma-separated):")
                yield Input(
                    id="aliases",
                    value=",".join(self.app.get("aliases", [])) if is_edit else "",
                    placeholder="app,app-alias,etc"
                )

                with Horizontal():
                    yield Button("Cancel", id="cancel")
                    yield Button("Save", id="save")
                    if is_edit:
                        yield Button("Delete", id="delete", variant="error")

            yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "cancel":
            self.app.pop_screen()
        elif event.button.id == "save":
            self._save_app()
        elif event.button.id == "delete":
            self._delete_app()

    def _save_app(self) -> None:
        """Save the app definition"""
        name = self.query_one("#name").value
        class_pattern = self.query_one("#class_pattern").value
        command = self.query_one("#command").value
        aliases_text = self.query_one("#aliases").value

        # Basic validation
        if not name or not class_pattern or not command:
            self.notify("All fields except aliases are required", severity="error")
            return

        # Process aliases, removing empty entries
        aliases = [a.strip() for a in aliases_text.split(",") if a.strip()]

        # Update or create app
        if self.app_id:
            self.app_manager.update_app(
                self.app_id, name, class_pattern, command, aliases
            )
            self.notify(f"Updated app: {name}")
        else:
            app = self.app_manager.add_app(name, class_pattern, command, aliases)
            self.notify(f"Added app: {name}")

        self.app.pop_screen()

    def _delete_app(self) -> None:
        """Delete the app definition"""
        if not self.app_id:
            return

        name = self.app["name"]
        self.app_manager.delete_app(self.app_id)
        self.notify(f"Deleted app: {name}")
        self.app.pop_screen()


class KaylandTUI(App):
    """Kayland Terminal User Interface"""

    TITLE = "Kayland - KDE Wayland Window Manager"
    CSS_PATH = None  # We're not using custom CSS for simplicity

    def __init__(self):
        super().__init__()

        try:
            self.window_manager = WindowManager()
            self.app_manager = AppManager()
        except Exception as e:
            logger.error(f"Failed to initialize managers: {str(e)}")
            print(f"Error: Failed to initialize: {str(e)}")
            sys.exit(1)

    def compose(self) -> ComposeResult:
        yield Header()

        with Container():
            with Horizontal():
                with Vertical(id="app-list-container"):
                    yield Static("Applications", classes="heading")
                    self.app_list = ListView(id="app-list")
                    yield self.app_list

                    with Horizontal():
                        yield Button("Add", id="add-app")
                        yield Button("Edit", id="edit-app")
                        yield Button("Copy", id="copy-app")
                        yield Button("Launch", id="launch-app")

                with Vertical(id="app-details"):
                    yield Static("Application Details", classes="heading")
                    yield Static(id="app-detail-content")

        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted"""
        self._refresh_app_list()

    def _refresh_app_list(self) -> None:
        """Refresh the application list"""
        try:
            apps = self.app_manager.get_all_apps()

            # Clear the list
            self.app_list.clear()

            # Add apps to the list
            for app in apps:
                self.app_list.append(AppListItem(app))
        except Exception as e:
            logger.error(f"Failed to refresh app list: {str(e)}")
            self.notify(f"Failed to refresh app list: {str(e)}", severity="error")

    def on_app_selected_message(self, message: AppSelectedMessage) -> None:
        """Handle app selection"""
        try:
            app = self.app_manager.get_app_by_id(message.app_id)
            if app:
                # Update app details
                detail_content = self.query_one("#app-detail-content")
                detail_content.update(
                    f"Name: {app['name']}\n"
                    f"Class Pattern: {app['class_pattern']}\n"
                    f"Command: {app['command']}\n"
                    f"Aliases: {', '.join(app.get('aliases', []))}\n"
                    f"ID: {app['id']}"
                )
        except Exception as e:
            logger.error(f"Failed to display app details: {str(e)}")
            self.notify(f"Failed to display app details: {str(e)}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        try:
            if event.button.id == "add-app":
                self.push_screen(AppFormScreen(self.app_manager))
            elif event.button.id == "edit-app":
                self._edit_selected_app()
            elif event.button.id == "copy-app":
                self._copy_selected_app()
            elif event.button.id == "launch-app":
                self._launch_selected_app()
        except Exception as e:
            logger.error(f"Error handling button press: {str(e)}")
            self.notify(f"Error: {str(e)}", severity="error")

    def _get_selected_app_id(self) -> Optional[str]:
        """Get the ID of the selected app"""
        if not self.app_list.index:
            self.notify("No application selected", severity="warning")
            return None

        try:
            selected_item = self.app_list.children[self.app_list.index]
            if isinstance(selected_item, AppListItem):
                return selected_item.app["id"]
        except IndexError:
            pass

        return None

    def _edit_selected_app(self) -> None:
        """Edit the selected app"""
        app_id = self._get_selected_app_id()
        if app_id:
            self.push_screen(AppFormScreen(self.app_manager, app_id))

    def _copy_selected_app(self) -> None:
        """Copy the selected app"""
        app_id = self._get_selected_app_id()
        if app_id:
            new_app = self.app_manager.copy_app(app_id)
            if new_app:
                self.notify(f"Copied app: {new_app['name']}")
                self._refresh_app_list()

    def _launch_selected_app(self) -> None:
        """Launch the selected app"""
        app_id = self._get_selected_app_id()
        if app_id:
            app = self.app_manager.get_app_by_id(app_id)
            if app:
                try:
                    result, success = self.window_manager.toggle_window(
                        app["class_pattern"], app["command"]
                    )
                    self.notify(result, severity="error" if not success else "information")
                except Exception as e:
                    logger.error(f"Failed to launch application: {str(e)}")
                    self.notify(f"Failed to launch application: {str(e)}", severity="error")

    def on_screen_resume(self) -> None:
        """Called when returning to the main screen"""
        self._refresh_app_list()


def run_tui():
    """Run the Kayland TUI"""
    try:
        app = KaylandTUI()
        app.run()
    except Exception as e:
        logger.error(f"Error running TUI: {str(e)}")
        print(f"Error running TUI: {str(e)}")
        sys.exit(1)