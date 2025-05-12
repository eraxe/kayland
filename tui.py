#!/usr/bin/env python3
# tui.py - Terminal UI for Kayland using Textual

import sys
import logging
import os
import time
import subprocess
import re
from typing import Dict, Any, Optional, List

# Set up logging
logger = logging.getLogger("kayland.tui")

# Check for Textual package
try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, Vertical, Grid, VerticalScroll
    from textual.widgets import Header, Footer, Button, Static, Input, ListView, ListItem, Label, Log
    from textual.widgets import Switch, DataTable, Select, TextArea
    from textual.screen import Screen, ModalScreen
    from textual.containers import TabPane, TabbedContent
    from textual.widgets.tab_list import Tab
    from textual import events
    from textual.binding import Binding
    from rich.text import Text
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

# Synthwave theme CSS
SYNTHWAVE_CSS = """
Screen {
    background: #2b213a;
}

.heading {
    background: #f615f6;
    color: #ffffff;
    text-align: center;
    text-style: bold;
    margin-bottom: 1;
    border: solid #ff00ff;
    height: 1;
}

.subheading {
    background: #3b1f5f;
    color: #00fff5;
    text-align: center;
    margin-bottom: 1;
    border: solid #00ccff;
    height: 1;
}

#app-list-container {
    width: 40%;
    height: 100%;
    border: hkey #ff00a0;
    background: #2b213a;
}

#app-details-container {
    width: 60%;
    height: 100%;
    border: hkey #00ccff;
    background: #2b213a;
}

#app-details {
    height: 50%;
    border-bottom: solid #00ccff;
}

#log-container {
    height: 50%;
}

Button {
    background: #00fff5;
    color: #3b1f5f;
    text-style: bold;
    min-width: 8;
    margin: 0 1;  /* Add horizontal margin between buttons */
}

Button:hover {
    background: #f615f6;
    color: #ffffff;
}

Input {
    background: #150a2d;
    color: #ffffff;
    border: solid #00ccff;
    margin-bottom: 1;
}

Input:focus {
    border: double #f615f6;
}

ListItem {
    background: #150a2d;
    color: #ffffff;
    padding: 1;
}

ListItem:hover {
    background: #3b1f5f;
    border: solid #f615f6;
}

ListView {
    border: solid #00ccff;
    background: #150a2d;
    height: 100%;
    margin-bottom: 1;
}

Label {
    color: #00fff5;
    margin-bottom: 0;
    width: 100%;
}

.action-buttons {
    margin-top: 1;
    height: auto;
    align: center middle;
}

.selected {
    background: #3b1f5f;
    border: solid #f615f6;
}

#app-detail-content {
    background: #150a2d;
    border: solid #00ccff;
    padding: 1;
    height: 100%;
    color: #ffffff;
}

#log-content {
    background: #150a2d;
    border: solid #00ccff;
    padding: 1;
    color: #ffffff;
    height: 100%;
    overflow: auto;
}

.form-container {
    background: #2b213a;
    border: wide #ff00ff;
    padding: 2;
    margin: 2 4;
    height: auto;
}

.form-grid {
    grid-size: 2;
    grid-columns: 1fr 3fr;
    padding: 0;
    margin-bottom: 1;
}

.button-container {
    height: auto;
    align: center middle;
    margin-top: 1;
}

Header {
    background: #3b1f5f;
    color: #ff00a0;
}

Footer {
    background: #150a2d;
    color: #00fff5;
}

/* Styles for service status and shortcuts */
TabbedContent {
    height: 100%;
}

.status-container {
    height: auto;
    padding: 1;
    margin: 1;
    border: solid #00ccff;
}

.status-text {
    margin: 1;
    padding: 1;
    text-align: center;
}

.service-controls {
    margin-top: 1;
    height: auto;
    align: center middle;
}

.shortcut-table {
    height: 100%;
    overflow: auto;
}

Select {
    background: #150a2d;
    color: #ffffff;
    border: solid #00ccff;
    margin-bottom: 1;
}

Select:focus {
    border: double #f615f6;
}

DataTable {
    background: #150a2d;
    color: #ffffff;
    border: solid #00ccff;
    height: 90%;
}

TextArea {
    background: #150a2d;
    color: #00fff5;
    border: solid #00ccff;
}
"""


class AppListItemData(ListItem):
    """A list item representing an application"""

    def __init__(self, app_data: Dict[str, Any]):
        super().__init__()
        self._app_data = app_data

    @property
    def app_data(self) -> Dict[str, Any]:
        return self._app_data

    def compose(self) -> ComposeResult:
        aliases = self._app_data.get('aliases', [])
        alias_text = f" ({', '.join(aliases)})" if aliases else ""
        yield Static(Text(f"{self._app_data['name']}", style="#00fff5") +
                     Text(alias_text, style="#ff00a0"))

    def on_click(self) -> None:
        # Add selected style
        for item in self.parent.children:
            if isinstance(item, AppListItemData):
                item.remove_class("selected")
        self.add_class("selected")

        # Signal app selection
        self.post_message(AppSelectedMessage(self._app_data["id"]))


class AppSelectedMessage(events.Message):
    """Message sent when an app is selected"""

    def __init__(self, app_id: str):
        super().__init__()
        self.app_id = app_id


class AppFormScreen(ModalScreen):
    """Screen for adding or editing an app"""
    BINDINGS = [("escape", "close_screen", "Close")]

    def __init__(self, parent_app: App, app_manager: AppManager, app_id: str = None):
        super().__init__()
        self.parent_app = parent_app
        self.app_manager = app_manager
        self.app_id = app_id
        self.app_data = None

        if app_id:
            self.app_data = app_manager.get_app_by_id(app_id)

    def compose(self) -> ComposeResult:
        is_edit = self.app_data is not None
        title = "Edit Application" if is_edit else "Add Application"

        with Container(classes="form-container"):
            yield Static(title, classes="heading")

            with Grid(classes="form-grid"):
                yield Label("Name:")
                yield Input(
                    id="name",
                    value=self.app_data["name"] if is_edit else "",
                    placeholder="Application name"
                )

                yield Label("Class Pattern:")
                yield Input(
                    id="class_pattern",
                    value=self.app_data["class_pattern"] if is_edit else "",
                    placeholder="Window class pattern (substring to match)"
                )

                yield Label("Command:")
                yield Input(
                    id="command",
                    value=self.app_data["command"] if is_edit else "",
                    placeholder="Launch command"
                )

                yield Label("Aliases:")
                yield Input(
                    id="aliases",
                    value=",".join(self.app_data.get("aliases", [])) if is_edit else "",
                    placeholder="app,app-alias,etc (comma-separated)"
                )

            with Horizontal(classes="button-container"):
                yield Button("Cancel", id="cancel", variant="primary")
                yield Button("Save", id="save", variant="success")
                if is_edit:
                    yield Button("Delete", id="delete", variant="error")

    def action_close_screen(self) -> None:
        """Close the screen"""
        self.dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "cancel":
            self.dismiss()
        elif event.button.id == "save":
            self._save_app()
        elif event.button.id == "delete":
            self._delete_app()

    def _save_app(self) -> None:
        """Save the app definition"""
        try:
            name = self.query_one("#name").value
            class_pattern = self.query_one("#class_pattern").value
            command = self.query_one("#command").value
            aliases_text = self.query_one("#aliases").value

            # Basic validation
            if not name or not class_pattern or not command:
                self.parent_app.notify("All fields except aliases are required", severity="error")
                return

            # Process aliases, removing empty entries
            aliases = [a.strip() for a in aliases_text.split(",") if a.strip()]

            # Update or create app
            try:
                if self.app_id:
                    self.app_manager.update_app(
                        self.app_id, name, class_pattern, command, aliases
                    )
                    message = f"Updated app: {name}"
                    self.parent_app.add_log_entry(message, "success")
                    self.parent_app.notify(message, timeout=3)
                else:
                    app = self.app_manager.add_app(name, class_pattern, command, aliases)
                    message = f"Added app: {name} with ID: {app['id']}"
                    self.parent_app.add_log_entry(message, "success")
                    self.parent_app.notify(message, timeout=3)

                # Explicitly signal changes were made
                self.dismiss({"changes_made": True})
            except ValueError as e:
                error_msg = f"Error: {str(e)}"
                self.parent_app.add_log_entry(error_msg, "error")
                self.parent_app.notify(error_msg, severity="error")

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.parent_app.add_log_entry(error_msg, "error")
            self.parent_app.notify(error_msg, severity="error")
            logger.error(f"Error saving app: {str(e)}")

    def _delete_app(self) -> None:
        """Delete the app definition"""
        if not self.app_id:
            return

        try:
            name = self.app_data["name"]
            self.app_manager.delete_app(self.app_id)
            message = f"Deleted app: {name}"
            self.parent_app.add_log_entry(message, "success")
            self.parent_app.notify(message, timeout=3)
            self.dismiss({"changes_made": True})
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.parent_app.add_log_entry(error_msg, "error")
            self.parent_app.notify(error_msg, severity="error")
            logger.error(f"Error deleting app: {str(e)}")


class ShortcutScreen(ModalScreen):
    """Screen for adding or editing a shortcut"""
    BINDINGS = [("escape", "close_screen", "Close")]

    def __init__(self, parent_app: App, app_manager: AppManager, shortcut_id: str = None):
        super().__init__()
        self.parent_app = parent_app
        self.app_manager = app_manager
        self.shortcut_id = shortcut_id
        self.shortcut_data = None

        if shortcut_id:
            self.shortcut_data = app_manager.get_shortcut_by_id(shortcut_id)

    def compose(self) -> ComposeResult:
        is_edit = self.shortcut_data is not None
        title = "Edit Shortcut" if is_edit else "Add Shortcut"

        with Container(classes="form-container"):
            yield Static(title, classes="heading")

            with Grid(classes="form-grid"):
                yield Label("Application:")
                app_input = Select(id="app_id")
                for app in self.app_manager.get_all_apps():
                    app_input.add_option(app["id"], app["name"])
                if is_edit and self.shortcut_data:
                    app_input.value = self.shortcut_data["app_id"]
                yield app_input

                yield Label("Shortcut Key:")
                yield Input(
                    id="key",
                    value=self.shortcut_data["key"] if is_edit else "",
                    placeholder="e.g. alt+b, ctrl+shift+g"
                )

                yield Label("Description:")
                yield Input(
                    id="description",
                    value=self.shortcut_data.get("description", "") if is_edit else "",
                    placeholder="Optional description"
                )

            with Horizontal(classes="button-container"):
                yield Button("Cancel", id="cancel", variant="primary")
                yield Button("Save", id="save", variant="success")
                if is_edit:
                    yield Button("Delete", id="delete", variant="error")

    def action_close_screen(self) -> None:
        """Close the screen"""
        self.dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "cancel":
            self.dismiss()
        elif event.button.id == "save":
            self._save_shortcut()
        elif event.button.id == "delete":
            self._delete_shortcut()

    def _save_shortcut(self) -> None:
        """Save the shortcut"""
        try:
            app_id = self.query_one("#app_id", Select).value
            key = self.query_one("#key").value
            description = self.query_one("#description").value

            # Basic validation
            if not app_id or not key:
                self.parent_app.notify("Application and shortcut key are required", severity="error")
                return

            # Validate shortcut format
            if not re.match(r'^[a-z0-9+]+$', key.lower()):
                self.parent_app.notify("Invalid shortcut format. Use format like 'alt+b'", severity="error")
                return

            # Update or create shortcut
            try:
                if self.shortcut_id:
                    self.app_manager.update_shortcut(
                        self.shortcut_id, app_id, key, description
                    )
                    message = f"Updated shortcut: {key}"
                    self.parent_app.add_log_entry(message, "success")
                    self.parent_app.notify(message, timeout=3)
                else:
                    shortcut = self.app_manager.add_shortcut(app_id, key, description)
                    message = f"Added shortcut: {key}"
                    self.parent_app.add_log_entry(message, "success")
                    self.parent_app.notify(message, timeout=3)

                # Explicitly signal changes were made
                self.dismiss({"changes_made": True})
            except ValueError as e:
                error_msg = f"Error: {str(e)}"
                self.parent_app.add_log_entry(error_msg, "error")
                self.parent_app.notify(error_msg, severity="error")

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.parent_app.add_log_entry(error_msg, "error")
            self.parent_app.notify(error_msg, severity="error")
            logger.error(f"Error saving shortcut: {str(e)}")

    def _delete_shortcut(self) -> None:
        """Delete the shortcut"""
        if not self.shortcut_id:
            return

        try:
            key = self.shortcut_data["key"]
            self.app_manager.remove_shortcut(self.shortcut_id)
            message = f"Deleted shortcut: {key}"
            self.parent_app.add_log_entry(message, "success")
            self.parent_app.notify(message, timeout=3)
            self.dismiss({"changes_made": True})
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.parent_app.add_log_entry(error_msg, "error")
            self.parent_app.notify(error_msg, severity="error")
            logger.error(f"Error deleting shortcut: {str(e)}")


class ServiceStatusWidget(Container):
    """Widget showing systemd service status and controls"""

    def __init__(self, parent_app):
        super().__init__(id="service-status-widget")
        self.parent_app = parent_app
        self.status_timer = 0
        self.service_running = False

    def compose(self) -> ComposeResult:
        with Container(classes="status-container"):
            yield Static("Kayland Service", classes="subheading")
            yield Static(id="service-status", classes="status-text")

            with Horizontal(classes="service-controls"):
                yield Button("Check Status", id="check-status", variant="primary")
                yield Button("Start Service", id="start-service", variant="success")
                yield Button("Stop Service", id="stop-service", variant="warning")
                yield Button("Restart Service", id="restart-service", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        button_id = event.button.id

        if button_id == "check-status":
            self.check_service_status()
        elif button_id == "start-service":
            self.manage_service("start")
        elif button_id == "stop-service":
            self.manage_service("stop")
        elif button_id == "restart-service":
            self.manage_service("restart")

    def check_service_status(self) -> None:
        """Check the status of the Kayland service"""
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", "kayland.service"],
                capture_output=True,
                text=True
            )

            status_text = self.query_one("#service-status", Static)

            if result.stdout.strip() == "active":
                self.service_running = True
                status_text.update(Text("● SERVICE RUNNING", style="bold green"))
                self.parent_app.add_log_entry("Kayland service is running", "success")
            else:
                self.service_running = False
                status_text.update(Text("● SERVICE STOPPED", style="bold red"))
                self.parent_app.add_log_entry("Kayland service is not running", "warning")

            # Also get the full status for the log
            full_status = subprocess.run(
                ["systemctl", "--user", "status", "kayland.service"],
                capture_output=True,
                text=True
            )

            self.parent_app.add_log_entry(full_status.stdout, "info")
        except Exception as e:
            self.service_running = False
            self.parent_app.add_log_entry(f"Error checking service status: {str(e)}", "error")

    def manage_service(self, action: str) -> None:
        """Start, stop or restart the service"""
        try:
            command = ["systemctl", "--user", action, "kayland.service"]
            result = subprocess.run(command, capture_output=True, text=True)

            if result.returncode == 0:
                message = f"Service {action} successful"
                self.parent_app.add_log_entry(message, "success")
                self.parent_app.notify(message, timeout=3)

                # Wait a moment for the service to change state
                self.parent_app.set_timer(1, self.check_service_status)
            else:
                error = result.stderr or f"Unknown error during service {action}"
                self.parent_app.add_log_entry(error, "error")
                self.parent_app.notify(f"Service {action} failed", severity="error", timeout=3)

        except Exception as e:
            self.parent_app.add_log_entry(f"Error during service {action}: {str(e)}", "error")

    def on_mount(self) -> None:
        """Check status when mounted"""
        self.check_service_status()


# KaylandTUI class (updated with shortcut and service management tabs)
class KaylandTUI(App):
    """Kayland Terminal User Interface"""

    TITLE = "Kayland - KDE Wayland Window Manager"
    CSS = SYNTHWAVE_CSS
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("a", "add_app", "Add App", show=True),
        Binding("e", "edit_app", "Edit App", show=True),
        Binding("c", "copy_app", "Copy App", show=True),
        Binding("l", "launch_app", "Launch App", show=True),
        Binding("s", "add_shortcut", "Add Shortcut", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("p", "toggle_palette", "Palette", show=True),
    ]

    def __init__(self):
        super().__init__()

        try:
            self.window_manager = WindowManager()
            self.app_manager = AppManager()
            self.selected_app_id = None
            self.selected_shortcut_id = None
            self.log_entries = []
        except Exception as e:
            logger.error(f"Failed to initialize managers: {str(e)}")
            print(f"Error: Failed to initialize: {str(e)}")
            sys.exit(1)

    def compose(self) -> ComposeResult:
        yield Header()

        with TabbedContent(id="main-tabs"):
            with TabPane("Applications", id="apps-tab"):
                with Container():
                    with Horizontal():
                        # Left panel: App list and buttons
                        with Vertical(id="app-list-container"):
                            yield Static("Applications", classes="heading")
                            with VerticalScroll():
                                self.app_list = ListView(id="app-list")
                                yield self.app_list

                            # Changed from Grid to Horizontal for buttons
                            with Horizontal(classes="action-buttons"):
                                yield Button("Add", id="add-app", variant="primary")
                                yield Button("Edit", id="edit-app", variant="primary")
                                yield Button("Copy", id="copy-app", variant="primary")
                                yield Button("Launch", id="launch-app", variant="success")

                        # Right panel: App details and logs
                        with Vertical(id="app-details-container"):
                            # App details section
                            with Vertical(id="app-details"):
                                yield Static("Application Details", classes="heading")
                                with VerticalScroll():
                                    yield Static(id="app-detail-content")

                            # Log section
                            with Vertical(id="log-container"):
                                yield Static("System Logs", classes="subheading")
                                with VerticalScroll():
                                    yield Static(id="log-content")

            with TabPane("Shortcuts", id="shortcuts-tab"):
                with Container():
                    yield Static("Keyboard Shortcuts", classes="heading")

                    with Vertical():
                        # Shortcut table
                        self.shortcut_table = DataTable(id="shortcut-table", classes="shortcut-table")
                        self.shortcut_table.add_columns("App", "Key", "Description")
                        yield self.shortcut_table

                        with Horizontal(classes="action-buttons"):
                            yield Button("Add Shortcut", id="add-shortcut", variant="primary")
                            yield Button("Edit Shortcut", id="edit-shortcut", variant="primary")
                            yield Button("Remove Shortcut", id="remove-shortcut", variant="error")

            with TabPane("Service", id="service-tab"):
                with Container():
                    yield Static("Kayland Service Management", classes="heading")

                    yield ServiceStatusWidget(self)

                    with Vertical():
                        yield Static("Service Information", classes="subheading")
                        with VerticalScroll():
                            yield TextArea(
                                id="service-info",
                                language="bash",
                                read_only=True,
                                text=(
                                    "The Kayland service allows shortcuts to work in the background.\n\n"
                                    "When running, you can use your configured shortcuts from anywhere\n"
                                    "without having to manually launch the app.\n\n"
                                    "Service logs can be viewed with:\n"
                                    "journalctl --user -u kayland.service -f"
                                )
                            )

        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted"""
        self._refresh_app_list()
        self._refresh_shortcut_list()
        self.add_log_entry("Kayland started successfully", "info")

    def add_log_entry(self, message: str, level: str = "info") -> None:
        """Add a log entry to the log panel"""
        try:
            timestamp = time.strftime("%H:%M:%S")
            style = {
                "info": "#00fff5",
                "error": "#ff0000",
                "warning": "#ffff00",
                "success": "#00ff00"
            }.get(level, "#ffffff")

            # For multi-line messages, split and format each line
            if "\n" in message:
                lines = message.split("\n")
                entry = Text(f"[{timestamp}] ", style="#aaaaaa")
                entry.append(Text(lines[0], style=style))

                # Format the remaining lines with indentation
                for line in lines[1:]:
                    self.log_entries.insert(0, Text("    " + line, style=style))

                self.log_entries.insert(0, entry)
            else:
                entry = Text(f"[{timestamp}] ", style="#aaaaaa")
                entry.append(Text(message, style=style))
                self.log_entries.insert(0, entry)  # Insert at top for newest first

            # Always log to console for debugging
            print(f"[{level.upper()}] {message}")

            # Update the log content - make sure this is always called
            log_content = self.query_one("#log-content", Static)
            if log_content:
                log_text = Text("\n").join(self.log_entries[:100])  # Limit to last 100 entries
                log_content.update(log_text)

                # Force a refresh of the log container
                log_container = self.query_one("#log-container", Vertical)
                if log_container:
                    log_container.refresh()

        except Exception as e:
            # If we can't update the log UI, log to system logger
            logger.error(f"Failed to update log UI: {str(e)}")
            # And print to console as a fallback
            print(f"LOG ERROR: {str(e)}")
            print(f"[{level.upper()}] {message}")

    def _refresh_app_list(self) -> None:
        """Refresh the application list"""
        try:
            # Get apps directly from app_manager
            apps = self.app_manager.get_all_apps()

            # Debug info
            self.add_log_entry(f"Refreshing app list, found {len(apps)} apps", "info")

            # Completely rebuild the list from scratch
            self.app_list.clear()

            # Add apps to the list
            for app in apps:
                # Create a new app list item - this avoids the setter issue
                list_item = AppListItemData(app)
                self.app_list.append(list_item)

                # If this is the selected app, mark it as selected
                if self.selected_app_id and app.get("id") == self.selected_app_id:
                    list_item.add_class("selected")

            # Update app details if we had a selection
            if self.selected_app_id:
                app = self.app_manager.get_app_by_id(self.selected_app_id)
                if app:
                    self._update_app_details(app)
                else:
                    self.selected_app_id = None
                    self._update_app_details(None)
            else:
                self._update_app_details(None)

        except Exception as e:
            error_msg = f"Failed to refresh app list: {str(e)}"
            logger.error(error_msg)
            self.add_log_entry(error_msg, "error")
            self.notify(error_msg, severity="error")

    def _refresh_shortcut_list(self) -> None:
        """Refresh the shortcut list table"""
        try:
            # Clear existing rows
            self.shortcut_table.clear()

            # Get shortcuts from app manager
            shortcuts = self.app_manager.get_shortcuts()

            for shortcut in shortcuts:
                app_id = shortcut.get("app_id", "")
                app_name = "Unknown"

                # Get app name if available
                app = self.app_manager.get_app_by_id(app_id)
                if app:
                    app_name = app["name"]

                # Add to table
                self.shortcut_table.add_row(
                    app_name,
                    shortcut.get("key", ""),
                    shortcut.get("description", "")
                )

            if not shortcuts:
                self.add_log_entry("No shortcuts found", "info")

        except Exception as e:
            error_msg = f"Failed to refresh shortcut list: {str(e)}"
            logger.error(error_msg)
            self.add_log_entry(error_msg, "error")
            self.notify(error_msg, severity="error")

    def _update_app_details(self, app: Optional[Dict[str, Any]]) -> None:
        """Update the app details panel"""
        detail_content = self.query_one("#app-detail-content")

        if app:
            content = Text("\n")
            content.append(Text("Name: ", style="#ff00a0"))
            content.append(Text(f"{app['name']}\n\n", style="#ffffff"))

            content.append(Text("Class Pattern: ", style="#ff00a0"))
            content.append(Text(f"{app['class_pattern']}\n\n", style="#ffffff"))

            content.append(Text("Command: ", style="#ff00a0"))
            content.append(Text(f"{app['command']}\n\n", style="#ffffff"))

            content.append(Text("Aliases: ", style="#ff00a0"))
            content.append(Text(f"{', '.join(app.get('aliases', []))}\n\n", style="#ffffff"))

            content.append(Text("ID: ", style="#ff00a0"))
            content.append(Text(f"{app['id']}", style="#ffffff"))

            detail_content.update(content)
        else:
            detail_content.update(
                "\n  No application selected.\n\n  Select an application from the list or add a new one.")

    def on_app_selected_message(self, message: AppSelectedMessage) -> None:
        """Handle app selection"""
        try:
            self.selected_app_id = message.app_id
            app = self.app_manager.get_app_by_id(message.app_id)
            if app:
                self._update_app_details(app)
                self.add_log_entry(f"Selected application: {app['name']}", "info")
        except Exception as e:
            error_msg = f"Failed to display app details: {str(e)}"
            logger.error(error_msg)
            self.add_log_entry(error_msg, "error")
            self.notify(error_msg, severity="error")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle shortcut selection in the table"""
        try:
            row = event.row_key
            shortcuts = self.app_manager.get_shortcuts()

            if row < len(shortcuts):
                self.selected_shortcut_id = shortcuts[row]["id"]
                self.add_log_entry(f"Selected shortcut: {shortcuts[row]['key']}", "info")

        except Exception as e:
            self.add_log_entry(f"Error selecting shortcut: {str(e)}", "error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        try:
            button_id = event.button.id

            if button_id == "add-app":
                self.action_add_app()
            elif button_id == "edit-app":
                self.action_edit_app()
            elif button_id == "copy-app":
                self.action_copy_app()
            elif button_id == "launch-app":
                self.action_launch_app()
            elif button_id == "add-shortcut":
                self.action_add_shortcut()
            elif button_id == "edit-shortcut":
                self._edit_selected_shortcut()
            elif button_id == "remove-shortcut":
                self._remove_selected_shortcut()

        except Exception as e:
            error_msg = f"Error handling button press: {str(e)}"
            logger.error(error_msg)
            self.add_log_entry(error_msg, "error")
            self.notify(error_msg, severity="error")

    def action_add_app(self) -> None:
        """Add a new application"""
        self.add_log_entry("Opening add application form", "info")
        self.push_screen(AppFormScreen(self, self.app_manager))

    def action_edit_app(self) -> None:
        """Edit the selected app"""
        app_id = self._get_selected_app_id()
        if app_id:
            self.add_log_entry(f"Opening edit form for app ID: {app_id}", "info")
            self.push_screen(AppFormScreen(self, self.app_manager, app_id))

    def action_copy_app(self) -> None:
        """Copy the selected app"""
        app_id = self._get_selected_app_id()
        if app_id:
            try:
                new_app = self.app_manager.copy_app(app_id)
                if new_app:
                    message = f"Copied app: {new_app['name']}"
                    self.add_log_entry(message, "success")
                    self.notify(message, timeout=3)
                    self._refresh_app_list()
            except Exception as e:
                error_msg = f"Error copying app: {str(e)}"
                self.add_log_entry(error_msg, "error")
                self.notify(error_msg, severity="error")

    def action_launch_app(self) -> None:
        """Launch the selected app"""
        app_id = self._get_selected_app_id()
        if app_id:
            app = self.app_manager.get_app_by_id(app_id)
            if app:
                try:
                    self.add_log_entry(f"Launching application: {app['name']}", "info")
                    result, success = self.window_manager.toggle_window(
                        app["class_pattern"], app["command"]
                    )
                    log_level = "success" if success else "error"
                    self.add_log_entry(result, log_level)
                    self.notify(
                        f"Toggle result: {'Success' if success else 'Failed'}",
                        severity="error" if not success else "information",
                        timeout=3
                    )
                except Exception as e:
                    error_msg = f"Failed to launch application: {str(e)}"
                    logger.error(error_msg)
                    self.add_log_entry(error_msg, "error")
                    self.notify(error_msg, severity="error")

    def action_add_shortcut(self) -> None:
        """Add a new shortcut"""
        self.add_log_entry("Opening add shortcut form", "info")
        self.push_screen(ShortcutScreen(self, self.app_manager))

    def _edit_selected_shortcut(self) -> None:
        """Edit the selected shortcut"""
        if self.selected_shortcut_id:
            self.add_log_entry(f"Editing shortcut ID: {self.selected_shortcut_id}", "info")
            self.push_screen(ShortcutScreen(self, self.app_manager, self.selected_shortcut_id))
        else:
            self.notify("No shortcut selected", severity="warning", timeout=2)

    def _remove_selected_shortcut(self) -> None:
        """Remove the selected shortcut"""
        if self.selected_shortcut_id:
            try:
                shortcuts = self.app_manager.get_shortcuts()
                shortcut = next((s for s in shortcuts if s["id"] == self.selected_shortcut_id), None)

                if shortcut:
                    key = shortcut.get("key", "")
                    self.app_manager.remove_shortcut(self.selected_shortcut_id)
                    message = f"Removed shortcut: {key}"
                    self.add_log_entry(message, "success")
                    self.notify(message, timeout=3)
                    self._refresh_shortcut_list()
                    self.selected_shortcut_id = None

            except Exception as e:
                error_msg = f"Error removing shortcut: {str(e)}"
                self.add_log_entry(error_msg, "error")
                self.notify(error_msg, severity="error")
        else:
            self.notify("No shortcut selected", severity="warning", timeout=2)

    def action_refresh(self) -> None:
        """Manually refresh the app list"""
        self.add_log_entry("Manually refreshing application list", "info")
        self._refresh_app_list()
        self._refresh_shortcut_list()

    def _get_selected_app_id(self) -> Optional[str]:
        """Get the ID of the selected app"""
        if self.selected_app_id:
            return self.selected_app_id

        try:
            if self.app_list.index is not None:
                selected_item = self.app_list.children[self.app_list.index]
                if isinstance(selected_item, AppListItemData):
                    self.selected_app_id = selected_item.app_data["id"]
                    return self.selected_app_id
        except (IndexError, AttributeError):
            pass

        warning_msg = "No application selected"
        self.add_log_entry(warning_msg, "warning")
        self.notify(warning_msg, severity="warning", timeout=2)
        return None

    def on_screen_resume(self, event: events.ScreenResume) -> None:
        """Called when returning to the main screen"""
        # Check if the modal screen passed a value indicating changes were made
        if hasattr(event, 'value') and event.value and event.value.get('changes_made', False):
            self.add_log_entry("Changes detected, refreshing data", "info")
            self._refresh_app_list()
            self._refresh_shortcut_list()


def run_tui():
    """Run the Kayland TUI"""
    try:
        app = KaylandTUI()
        app.run()
    except Exception as e:
        logger.error(f"Error running TUI: {str(e)}")
        print(f"Error running TUI: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    run_tui()