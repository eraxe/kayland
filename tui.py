#!/usr/bin/env python3
# tui.py - Terminal UI for Kayland using Textual

import sys
import logging
import os
import time
import subprocess
import re
import configparser
from typing import Dict, Any, Optional, List, Set
from pathlib import Path

# Set up logging
logger = logging.getLogger("kayland.tui")

# Check for Textual package
try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, Vertical, Grid, VerticalScroll
    from textual import events
    from textual.binding import Binding
    from textual.widgets import (
        Header, Footer, Button, Static, Input, ListView, ListItem, Label,
        Switch, DataTable, TextArea, Tab, Tree
    )
    from textual.events import Mount
    from textual.reactive import reactive
    from textual.widget import Widget
    from textual.css.query import NoMatches

    # Import Select with proper error handling
    try:
        from textual.widgets import Select
    except ImportError:
        try:
            from textual.widgets.select import Select
        except ImportError:
            # Last resort fallback
            class Select(Widget):
                """Simple placeholder for Select"""
                def __init__(self, options=None, **kwargs):
                    super().__init__(**kwargs)
                    self.options = options or []
                    self.value = options[0][0] if options else None

    # For newer Textual versions, TabPane and TabbedContent might be in different locations
    # Try different import paths
    try:
        from textual.widgets import TabPane, TabbedContent
    except ImportError:
        try:
            from textual.containers import TabPane, TabbedContent
        except ImportError:
            # Last resort, try from a different location
            try:
                from textual.widgets.tabs import TabPane, TabbedContent
            except ImportError:
                # Really simple implementation as a last resort
                class TabPane(Widget):
                    """Simple tab pane placeholder"""
                    def __init__(self, title, id=None, **kwargs):
                        super().__init__(id=id, **kwargs)
                        self.title = title

                class TabbedContent(Widget):
                    """Simple tabbed content placeholder"""
                    def __init__(self, **kwargs):
                        super().__init__(**kwargs)
                        self.active = 0
                        self.tabs = []
    from textual.screen import Screen, ModalScreen
    from rich.text import Text
    from rich.console import RenderableType

    # Try to import Dropdown widget (not available in all versions)
    try:
        from textual.widgets import Dropdown

        HAS_DROPDOWN = True
    except ImportError:
        HAS_DROPDOWN = False
        logger.warning("Dropdown widget not available in this Textual version")

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

try:
    from window_manager import WindowManager
    from app_manager import AppManager
except ImportError as e:
    logger.error(f"Failed to import required modules: {str(e)}")
    print(f"Error: Failed to import required modules: {str(e)}")
    sys.exit(1)

# Enhanced Synthwave theme CSS with improved spacing and more compact elements
SYNTHWAVE_CSS = """
Screen {
    background: #2b213a;
}

.heading {
    background: #f615f6;
    color: #ffffff;
    text-align: center;
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
    border: solid #ff00a0;
    background: #2b213a;
}

#app-details-container {
    width: 60%;
    height: 100%;
    border: solid #00ccff;
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
    margin: 0 1;
    height: 1;
}

Button:hover {
    background: #f615f6;
    color: #ffffff;
}

Button:focus {
    background: #f615f6;
    color: #ffffff;
    border: solid #ffffff;
}

.add-button {
    background: #f615f6;
    color: #ffffff;
    width: 3;
    margin-left: 1;
}

Input {
    background: #150a2d;
    color: #ffffff;
    border: solid #00ccff;
    margin-bottom: 1;
}

Input:focus {
    border: solid #f615f6;
}

ListItem {
    background: #150a2d;
    color: #ffffff;
    height: 1;
}

ListItem:hover {
    background: #3b1f5f;
    border: solid #f615f6;
}

ListItem:focus {
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
    margin: 0;
    width: 100%;
    height: 1;
}

.action-buttons {
    margin-top: 1;
    height: auto;
}

.selected {
    background: #3b1f5f;
    border: solid #f615f6;
}

.focused {
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
    border: solid #ff00ff;
    padding: 2;
    margin: 2 4;
    height: auto;
}

.form-row {
    margin-bottom: 1;
}

.button-container {
    height: auto;
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
    border: solid #f615f6;
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

.dropdown-container {
    background: #150a2d;
    border: solid #00ccff;
    width: 30;
}

.dropdown-option {
    background: #150a2d;
    color: #00fff5;
    height: 1;
}

.dropdown-option-selected {
    background: #3b1f5f;
    color: #ffffff;
}

.settings-container {
    height: 100%;
    padding: 1;
}

.file-list {
    height: 100%;
    border: solid #00ccff;
    background: #150a2d;
}

.file-preview {
    height: 100%;
    border: solid #00ccff;
    background: #150a2d;
    padding: 1;
}

.preview-content {
    padding: 1;
    color: #ffffff;
}

Tree {
    background: #150a2d;
    color: #ffffff;
}

Tree:focus {
    border: solid #f615f6;
}

Static {
    color: #ffffff;
}

#app-list {
    border: solid #00ccff;
}

Tab {
    background: #150a2d;
    color: #00fff5;
}

Tab:hover {
    background: #3b1f5f;
    color: #ffffff;
}

Tab.-active {
    background: #f615f6;
    color: #ffffff;
}
"""

# Default settings
DEFAULT_SETTINGS = {
    "desktop_file_dir": "~/.local/share/applications",
    "theme": "synthwave",
    "confirm_delete": "True"
}

# Utility functions
def safe_select_value(select_widget, default=None):
    """Safely get the value from a Select widget, handling possible errors"""
    if not select_widget:
        return default

    try:
        # Check if the widget has a value and it's not None
        if hasattr(select_widget, 'value') and select_widget.value is not None:
            return select_widget.value
    except Exception as e:
        logger.error(f"Error getting select value: {str(e)}")

    return default

def parse_desktop_file(file_path: str) -> Dict[str, Any]:
    """Parse a .desktop file and return its contents as a dictionary"""
    result = {
        "name": "",
        "exec": "",
        "class": "",
        "icon": "",
        "comment": "",
        "path": file_path
    }

    try:
        parser = configparser.ConfigParser(strict=False)
        parser.read(file_path)

        if "Desktop Entry" in parser:
            section = parser["Desktop Entry"]
            result["name"] = section.get("Name", "")
            result["exec"] = section.get("Exec", "")
            result["icon"] = section.get("Icon", "")
            result["comment"] = section.get("Comment", "")

            # Try to get class from different sources
            result["class"] = (
                    section.get("StartupWMClass", "") or
                    section.get("X-KDE-WMClass", "") or
                    ""
            )

            # If no class found but it's a Chrome/Chromium app, extract from the app ID
            if not result["class"] and "chrome" in result["exec"].lower() and "--app-id=" in result["exec"]:
                app_id_match = re.search(r'--app-id=([a-z0-9]+)', result["exec"])
                if app_id_match:
                    app_id = app_id_match.group(1)
                    result["class"] = f"crx_{app_id}"
    except Exception as e:
        logger.error(f"Error parsing desktop file {file_path}: {str(e)}")

    return result


def find_desktop_files(directory: str) -> List[str]:
    """Find all .desktop files in the given directory"""
    desktop_files = []
    try:
        directory = os.path.expanduser(directory)
        for file in os.listdir(directory):
            if file.endswith(".desktop"):
                desktop_files.append(os.path.join(directory, file))
    except Exception as e:
        logger.error(f"Error finding desktop files in {directory}: {str(e)}")

    return desktop_files


class Settings:
    """Class to manage application settings"""

    def __init__(self):
        self.settings_file = os.path.expanduser("~/.config/kayland/settings.json")
        self.settings = DEFAULT_SETTINGS.copy()
        self._load_settings()

    def _load_settings(self):
        """Load settings from file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    import json
                    loaded_settings = json.load(f)
                    # Update with loaded settings, keeping defaults for missing keys
                    self.settings.update(loaded_settings)
        except Exception as e:
            logger.error(f"Error loading settings: {str(e)}")

    def save_settings(self):
        """Save settings to file"""
        try:
            config_dir = os.path.dirname(self.settings_file)
            os.makedirs(config_dir, exist_ok=True)

            with open(self.settings_file, 'w') as f:
                import json
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")

    def get(self, key, default=None):
        """Get a setting value"""
        return self.settings.get(key, default)

    def set(self, key, value):
        """Set a setting value"""
        self.settings[key] = value
        self.save_settings()


class AppListItemData(ListItem):
    """A list item representing an application"""

    def __init__(self, app_data: Dict[str, Any]):
        super().__init__()
        self._app_data = app_data
        self.can_focus = True

    @property
    def app_data(self) -> Dict[str, Any]:
        return self._app_data

    def compose(self) -> ComposeResult:
        aliases = self._app_data.get('aliases', [])
        alias_text = f" ({', '.join(aliases)})" if aliases else ""
        yield Static(Text(f"{self._app_data['name']}", style="#00fff5") +
                     Text(alias_text, style="#ff00a0"))

    def on_click(self) -> None:
        self._select_app()

    def on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            self._select_app()
        else:
            # Pass other keys to parent for navigation
            event.prevent_default(False)

    def _select_app(self) -> None:
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


class AppAddOptions(ModalScreen):
    """Modal screen showing add options"""
    BINDINGS = [("escape", "close_screen", "Close"),
                ("up", "previous_option", "Previous"),
                ("down", "next_option", "Next"),
                ("enter", "select_option", "Select")]

    def __init__(self):
        super().__init__()
        self.selected_option = 0
        self.options = ["Add from .desktop", "Add manually"]

    def compose(self) -> ComposeResult:
        with Container(classes="dropdown-container"):
            for i, option in enumerate(self.options):
                option_class = "dropdown-option"
                if i == self.selected_option:
                    option_class += " dropdown-option-selected"
                yield Static(option, classes=option_class, id=f"option-{i}")

    def on_mount(self) -> None:
        """Position the dropdown near the button and highlight first option"""
        self._highlight_option(0)

    def action_previous_option(self) -> None:
        """Move selection to previous option"""
        self.selected_option = max(0, self.selected_option - 1)
        self._highlight_option(self.selected_option)

    def action_next_option(self) -> None:
        """Move selection to next option"""
        self.selected_option = min(len(self.options) - 1, self.selected_option + 1)
        self._highlight_option(self.selected_option)

    def action_select_option(self) -> None:
        """Select the current option"""
        self.dismiss({"selected": self.options[self.selected_option]})

    def action_close_screen(self) -> None:
        """Close the screen without selecting"""
        self.dismiss()

    def _highlight_option(self, index: int) -> None:
        """Highlight the selected option"""
        for i in range(len(self.options)):
            option = self.query_one(f"#option-{i}", Static)
            if i == index:
                option.add_class("dropdown-option-selected")
                option.remove_class("dropdown-option")
                option.add_class("dropdown-option")
            else:
                option.remove_class("dropdown-option-selected")


class ConfirmDialog(ModalScreen):
    """A confirmation dialog"""
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, title: str, message: str):
        super().__init__()
        self.title = title
        self.message = message

    def compose(self) -> ComposeResult:
        with Container(classes="form-container"):
            yield Static(self.title, classes="heading")
            yield Static(self.message, id="confirm-message")

            with Horizontal(classes="button-container"):
                yield Button("Cancel", id="cancel", variant="primary")
                yield Button("Confirm", id="confirm", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "cancel":
            self.dismiss(False)
        elif event.button.id == "confirm":
            self.dismiss(True)

    def action_cancel(self) -> None:
        """Cancel the confirmation"""
        self.dismiss(False)


class AppFormScreen(ModalScreen):
    """Screen for adding or editing an app"""
    BINDINGS = [("escape", "close_screen", "Close"),
                ("f1", "toggle_shortcut", "Shortcut")]

    def __init__(self, parent_app: App, app_manager: AppManager, app_id: str = None, desktop_file: Dict[str, Any] = None):
        super().__init__()
        self.parent_app = parent_app
        self.app_manager = app_manager
        self.app_id = app_id
        self.app_data = None
        self.desktop_file = desktop_file
        self.show_shortcut = False

        if app_id:
            self.app_data = app_manager.get_app_by_id(app_id)

    def compose(self) -> ComposeResult:
        is_edit = self.app_data is not None
        title = "Edit Application" if is_edit else "Add Application"

        with Container(classes="form-container"):
            yield Static(title, classes="heading")

            # Use Vertical + Horizontal for form layout
            with Vertical():
                with Horizontal(classes="form-row"):
                    yield Label("Name:")
                    if self.desktop_file:
                        yield Input(
                            id="name",
                            value=self.desktop_file.get("name", ""),
                            placeholder="Application name"
                        )
                    else:
                        yield Input(
                            id="name",
                            value=self.app_data["name"] if is_edit else "",
                            placeholder="Application name"
                        )

                with Horizontal(classes="form-row"):
                    yield Label("Class Pattern:")
                    if self.desktop_file:
                        yield Input(
                            id="class_pattern",
                            value=self.desktop_file.get("class", ""),
                            placeholder="Window class pattern (substring to match)"
                        )
                    else:
                        yield Input(
                            id="class_pattern",
                            value=self.app_data["class_pattern"] if is_edit else "",
                            placeholder="Window class pattern (substring to match)"
                        )

                with Horizontal(classes="form-row"):
                    yield Label("Command:")
                    if self.desktop_file:
                        yield Input(
                            id="command",
                            value=self.desktop_file.get("exec", ""),
                            placeholder="Launch command"
                        )
                    else:
                        yield Input(
                            id="command",
                            value=self.app_data["command"] if is_edit else "",
                            placeholder="Launch command"
                        )

                with Horizontal(classes="form-row"):
                    yield Label("Aliases:")
                    yield Input(
                        id="aliases",
                        value=",".join(self.app_data.get("aliases", [])) if is_edit else "",
                        placeholder="app,app-alias,etc (comma-separated)"
                    )

                with Horizontal(classes="form-row"):
                    yield Label("Desktop File:")
                    if self.desktop_file:
                        yield Input(
                            id="desktop_file",
                            value=self.desktop_file.get("path", ""),
                            placeholder="Path to .desktop file (optional)"
                        )
                    else:
                        yield Input(
                            id="desktop_file",
                            value=self.app_data.get("desktop_file", "") if is_edit else "",
                            placeholder="Path to .desktop file (optional)"
                        )

            # Conditionally show shortcut section
            with Container(id="shortcut-section"):
                if self.show_shortcut or is_edit:
                    yield Static("Shortcut Settings", classes="subheading")

                    with Vertical():
                        with Horizontal(classes="form-row"):
                            yield Label("Shortcut Key:")
                            yield Input(
                                id="shortcut_key",
                                placeholder="e.g. alt+b, ctrl+shift+g",
                                value=self._get_existing_shortcut() if is_edit else ""
                            )

                        with Horizontal(classes="form-row"):
                            yield Label("Description:")
                            yield Input(
                                id="shortcut_description",
                                placeholder="Optional shortcut description",
                                value=self._get_existing_shortcut_description() if is_edit else ""
                            )

            with Horizontal(classes="button-container"):
                yield Button("Cancel", id="cancel")
                yield Button("Save", id="save")
                if is_edit:
                    yield Button("Delete", id="delete")

    def _get_existing_shortcut(self) -> str:
        """Get existing shortcut for this app if any"""
        if not self.app_id:
            return ""

        shortcuts = self.app_manager.get_shortcuts()
        for shortcut in shortcuts:
            if shortcut.get("app_id") == self.app_id:
                return shortcut.get("key", "")

        return ""

    def _get_existing_shortcut_description(self) -> str:
        """Get existing shortcut description for this app if any"""
        if not self.app_id:
            return ""

        shortcuts = self.app_manager.get_shortcuts()
        for shortcut in shortcuts:
            if shortcut.get("app_id") == self.app_id:
                return shortcut.get("description", "")

        return ""

    def _get_existing_shortcut_id(self) -> str:
        """Get existing shortcut ID for this app if any"""
        if not self.app_id:
            return ""

        shortcuts = self.app_manager.get_shortcuts()
        for shortcut in shortcuts:
            if shortcut.get("app_id") == self.app_id:
                return shortcut.get("id", "")

        return ""

    def action_close_screen(self) -> None:
        """Close the screen"""
        self.dismiss()

    def action_toggle_shortcut(self) -> None:
        """Toggle shortcut section visibility"""
        self.show_shortcut = not self.show_shortcut

        # Re-render the screen
        shortcut_section = self.query_one("#shortcut-section")
        shortcut_section.remove_children()

        is_edit = self.app_data is not None

        if self.show_shortcut or is_edit:
            shortcut_section.mount(Static("Shortcut Settings", classes="subheading"))

            form_grid = Vertical()

            # First row
            h_row1 = Horizontal(classes="form-row")
            h_row1.mount(Label("Shortcut Key:"))
            h_row1.mount(Input(
                id="shortcut_key",
                placeholder="e.g. alt+b, ctrl+shift+g",
                value=self._get_existing_shortcut() if is_edit else ""
            ))
            form_grid.mount(h_row1)

            # Second row
            h_row2 = Horizontal(classes="form-row")
            h_row2.mount(Label("Description:"))
            h_row2.mount(Input(
                id="shortcut_description",
                placeholder="Optional shortcut description",
                value=self._get_existing_shortcut_description() if is_edit else ""
            ))
            form_grid.mount(h_row2)

            shortcut_section.mount(form_grid)

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
            desktop_file = self.query_one("#desktop_file").value

            # Basic validation
            if not name or not class_pattern or not command:
                self.parent_app.notify("All fields except aliases and desktop file are required", severity="error")
                return

            # Process aliases, removing empty entries
            aliases = [a.strip() for a in aliases_text.split(",") if a.strip()]

            # Get shortcut data if present
            shortcut_key = ""
            shortcut_description = ""
            try:
                shortcut_key = self.query_one("#shortcut_key").value
                shortcut_description = self.query_one("#shortcut_description").value
            except NoMatches:
                # Shortcut section might not be visible
                pass

            # Update or create app
            try:
                if self.app_id:
                    # Update existing app
                    app = self.app_manager.update_app(
                        self.app_id, name, class_pattern, command, aliases
                    )

                    # Also update desktop_file attribute
                    if hasattr(self.app_manager, 'update_app_attribute'):
                        self.app_manager.update_app_attribute(self.app_id, "desktop_file", desktop_file)
                    else:
                        # Fallback if the method doesn't exist
                        for app_data in self.app_manager.apps:
                            if app_data.get("id") == self.app_id:
                                app_data["desktop_file"] = desktop_file
                        self.app_manager._save_apps()

                    message = f"Updated app: {name}"
                    self.parent_app.add_log_entry(message, "success")
                    self.parent_app.notify(message, timeout=3)

                    # Handle shortcut update/creation
                    if shortcut_key:
                        shortcut_id = self._get_existing_shortcut_id()
                        if shortcut_id:
                            # Update existing shortcut
                            self.app_manager.update_shortcut(
                                shortcut_id, self.app_id, shortcut_key, shortcut_description
                            )
                            self.parent_app.add_log_entry(f"Updated shortcut: {shortcut_key}", "success")
                        else:
                            # Create new shortcut
                            self.app_manager.add_shortcut(self.app_id, shortcut_key, shortcut_description)
                            self.parent_app.add_log_entry(f"Added shortcut: {shortcut_key}", "success")

                else:
                    # Create new app
                    app = self.app_manager.add_app(name, class_pattern, command, aliases)

                    # Add desktop_file attribute
                    if hasattr(self.app_manager, 'update_app_attribute'):
                        self.app_manager.update_app_attribute(app["id"], "desktop_file", desktop_file)
                    else:
                        # Fallback if the method doesn't exist
                        for app_data in self.app_manager.apps:
                            if app_data.get("id") == app["id"]:
                                app_data["desktop_file"] = desktop_file
                        self.app_manager._save_apps()

                    message = f"Added app: {name} with ID: {app['id']}"
                    self.parent_app.add_log_entry(message, "success")
                    self.parent_app.notify(message, timeout=3)

                    # Create shortcut if provided
                    if shortcut_key:
                        self.app_manager.add_shortcut(app["id"], shortcut_key, shortcut_description)
                        self.parent_app.add_log_entry(f"Added shortcut: {shortcut_key}", "success")

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

            # Delete any associated shortcuts first
            shortcuts = self.app_manager.get_shortcuts()
            for shortcut in shortcuts:
                if shortcut.get("app_id") == self.app_id:
                    self.app_manager.remove_shortcut(shortcut["id"])
                    self.parent_app.add_log_entry(f"Removed shortcut for: {name}", "success")

            # Delete the app
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


class DesktopFileScreen(ModalScreen):
    """Screen for browsing .desktop files"""
    BINDINGS = [("escape", "close_screen", "Close"),
                ("enter", "select_file", "Select")]

    def __init__(self, parent_app: App, desktop_dir: str = None):
        super().__init__()
        self.parent_app = parent_app
        self.desktop_dir = desktop_dir or os.path.expanduser("~/.local/share/applications")
        self.selected_file = None

    def compose(self) -> ComposeResult:
        with Container(classes="form-container"):
            yield Static("Select Desktop File", classes="heading")

            with Horizontal():
                # Left side: file browser
                with Vertical(classes="file-list"):
                    yield Static("Desktop Files", classes="subheading")
                    with VerticalScroll():
                        yield Tree("Desktop Files", id="desktop-file-tree")

                # Right side: file preview
                with Vertical(classes="file-preview"):
                    yield Static("File Preview", classes="subheading")
                    with VerticalScroll():
                        yield Static(id="preview-content", classes="preview-content")

            # Bottom: buttons
            with Horizontal(classes="button-container"):
                yield Button("Cancel", id="cancel")
                yield Button("Select Desktop Dir", id="change-dir")
                yield Button("Select File", id="select")

    def on_mount(self) -> None:
        """Populate the tree with desktop files"""
        self._populate_tree()

    def _populate_tree(self) -> None:
        """Populate the tree with desktop files"""
        try:
            tree = self.query_one("#desktop-file-tree", Tree)
            tree.reset()

            # Create a root node for the desktop directory
            root_node = tree.root
            root_node.label = os.path.basename(self.desktop_dir)
            root_node.data = {"path": self.desktop_dir, "type": "dir"}

            # Add .desktop files
            desktop_files = find_desktop_files(self.desktop_dir)

            for file_path in sorted(desktop_files):
                # Try to parse the desktop file to get the name
                desktop_data = parse_desktop_file(file_path)
                display_name = desktop_data["name"] or os.path.basename(file_path)

                # Add to tree
                node = root_node.add(display_name)
                node.data = {"path": file_path, "type": "file", "data": desktop_data}

            # Expand the root node
            root_node.expanded = True
        except Exception as e:
            logger.error(f"Error populating desktop file tree: {str(e)}")
            self.parent_app.add_log_entry(f"Error listing desktop files: {str(e)}", "error")

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle file selection in the tree"""
        node = event.node
        if node.data and node.data.get("type") == "file":
            self.selected_file = node.data["path"]
            desktop_data = node.data.get("data", {})

            # Format the file content for preview
            preview = ""
            if desktop_data:
                preview += f"Name: {desktop_data.get('name', '')}\n"
                preview += f"Exec: {desktop_data.get('exec', '')}\n"
                preview += f"Class: {desktop_data.get('class', '')}\n"
                preview += f"Icon: {desktop_data.get('icon', '')}\n"
                preview += f"Comment: {desktop_data.get('comment', '')}\n"

            # Also show the raw file content
            try:
                with open(self.selected_file, 'r') as f:
                    preview += "\n--- Raw Content ---\n"
                    preview += f.read()
            except Exception as e:
                preview += f"\nError reading file: {str(e)}"

            # Update preview
            preview_content = self.query_one("#preview-content", Static)
            preview_content.update(preview)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "cancel":
            self.dismiss()
        elif event.button.id == "select":
            self.action_select_file()
        elif event.button.id == "change-dir":
            self._change_directory()

    def action_select_file(self) -> None:
        """Select the current file"""
        if not self.selected_file:
            self.parent_app.notify("No file selected", severity="warning")
            return

        try:
            desktop_data = parse_desktop_file(self.selected_file)
            self.dismiss({"desktop_file": desktop_data})
        except Exception as e:
            error_msg = f"Error parsing desktop file: {str(e)}"
            self.parent_app.add_log_entry(error_msg, "error")
            self.parent_app.notify(error_msg, severity="error")

    def action_close_screen(self) -> None:
        """Close the screen"""
        self.dismiss()

    def _change_directory(self) -> None:
        """Change the desktop directory"""
        # This would ideally show a directory browser, but we'll just use a simple input dialog
        # In a real implementation, you might want to use a proper file browser
        pass


class ShortcutScreen(ModalScreen):
    """Screen for adding or editing a shortcut"""
    BINDINGS = [("escape", "close_screen", "Close")]

    def __init__(self, parent_app: App, app_manager: AppManager, shortcut_id: str = None):
        super().__init__()
        self.parent_app = parent_app
        self.app_manager = app_manager
        self.shortcut_id = shortcut_id
        self.shortcut_data = None
        self.all_apps = []
        self.app_options = []

        # Pre-load all apps and validate shortcut data
        self._prepare_data()

    def _prepare_data(self):
        """Prepare and validate all data before rendering"""
        # Get all available apps
        self.all_apps = self.app_manager.get_all_apps()

        # Create options list for the Select widget
        self.app_options = []
        for app in self.all_apps:
            self.app_options.append((app["id"], app["name"]))

        # If no apps are defined, add a placeholder option
        if not self.app_options:
            self.app_options.append(("no_apps", "No applications defined"))

        # Load shortcut data if editing
        if self.shortcut_id:
            self.shortcut_data = self.app_manager.get_shortcut_by_id(self.shortcut_id)

            # If shortcut data exists, verify the app still exists
            if self.shortcut_data and "app_id" in self.shortcut_data:
                app_id = self.shortcut_data["app_id"]
                app_exists = any(app["id"] == app_id for app in self.all_apps)

                # If app no longer exists, log a warning
                if not app_exists:
                    logger.warning(f"App ID {app_id} from shortcut {self.shortcut_id} no longer exists")

    def compose(self) -> ComposeResult:
        """Compose the shortcut form"""
        is_edit = self.shortcut_data is not None
        title = "Edit Shortcut" if is_edit else "Add Shortcut"

        with Container(classes="form-container"):
            yield Static(title, classes="heading")

            with Grid(classes="form-grid"):
                yield Label("Application:")

                # Get default value - carefully ensuring it exists in options
                default_value = self._get_safe_default_value()

                # Create the select widget with safe values
                yield Select(
                    id="app_id",
                    options=self.app_options,
                    value=default_value
                )

                yield Label("Shortcut Key:")
                yield Input(
                    id="key",
                    value=self.shortcut_data["key"] if is_edit and self.shortcut_data else "",
                    placeholder="e.g. alt+b, ctrl+shift+g"
                )

                yield Label("Description:")
                yield Input(
                    id="description",
                    value=self.shortcut_data.get("description", "") if is_edit and self.shortcut_data else "",
                    placeholder="Optional description"
                )

            with Horizontal(classes="button-container"):
                yield Button("Cancel", id="cancel", variant="primary")
                yield Button("Save", id="save", variant="success")
                if is_edit:
                    yield Button("Delete", id="delete", variant="error")

    def _get_safe_default_value(self) -> str:
        """Get a safe default value that is guaranteed to be in the options list"""
        is_edit = self.shortcut_data is not None

        # No options case
        if not self.app_options:
            return ""

        # Extract all valid values from options
        valid_values = [opt[0] for opt in self.app_options]

        # For edit mode, try to use the existing app_id
        if is_edit and self.shortcut_data and "app_id" in self.shortcut_data:
            app_id = self.shortcut_data["app_id"]
            # Only use if it's in the valid values
            if app_id in valid_values:
                return app_id

        # Default to first available option
        return valid_values[0]

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
            # Safe access to the selected value
            select = self.query_one("#app_id", Select)
            app_id = safe_select_value(select)
            key = self.query_one("#key").value
            description = self.query_one("#description").value

            # Check if we have the placeholder "no_apps" value
            if app_id == "no_apps":
                self.parent_app.notify("No applications defined. Please add an application first.",
                                       severity="error")
                return

            # Basic validation
            if not app_id or not key:
                self.parent_app.notify("Application and shortcut key are required", severity="error")
                return

            # Validate shortcut format
            if not re.match(r'^[a-z0-9+]+$', key.lower()):
                self.parent_app.notify("Invalid shortcut format. Use format like 'alt+b'", severity="error")
                return

            # Confirm app still exists
            if not any(app["id"] == app_id for app in self.all_apps):
                self.parent_app.notify("Selected application no longer exists", severity="error")
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
            key = self.shortcut_data["key"] if self.shortcut_data else "unknown"
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


class SettingsScreen(ModalScreen):
    """Screen for application settings"""
    BINDINGS = [("escape", "close_screen", "Close")]

    def __init__(self, parent_app: App, settings: Settings):
        super().__init__()
        self.parent_app = parent_app
        self.settings = settings

    def compose(self) -> ComposeResult:
        with Container(classes="form-container"):
            yield Static("Kayland Settings", classes="heading")

            with VerticalScroll(classes="settings-container"):
                with Grid(classes="settings-grid"):
                    yield Label("Desktop File Directory:")
                    yield Input(
                        id="desktop_file_dir",
                        value=self.settings.get("desktop_file_dir", "~/.local/share/applications"),
                        placeholder="~/.local/share/applications"
                    )

                    yield Label("Confirm Deletions:")
                    yield Switch(
                        id="confirm_delete",
                        value=self.settings.get("confirm_delete", "True") == "True"
                    )

            with Horizontal(classes="button-container"):
                yield Button("Cancel", id="cancel", variant="primary")
                yield Button("Save", id="save", variant="success")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "cancel":
            self.dismiss()
        elif event.button.id == "save":
            self._save_settings()

    def action_close_screen(self) -> None:
        """Close the screen"""
        self.dismiss()

    def _save_settings(self) -> None:
        """Save the settings"""
        try:
            desktop_file_dir = self.query_one("#desktop_file_dir").value
            confirm_delete = str(self.query_one("#confirm_delete").value)

            # Update settings
            self.settings.set("desktop_file_dir", desktop_file_dir)
            self.settings.set("confirm_delete", confirm_delete)

            # Save settings
            self.settings.save_settings()

            message = "Settings saved successfully"
            self.parent_app.add_log_entry(message, "success")
            self.parent_app.notify(message, timeout=3)
            self.dismiss({"changes_made": True})
        except Exception as e:
            error_msg = f"Error saving settings: {str(e)}"
            self.parent_app.add_log_entry(error_msg, "error")
            self.parent_app.notify(error_msg, severity="error")
            logger.error(error_msg)


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
                yield Button("Check Status", id="check-status")
                yield Button("Start Service", id="start-service")
                yield Button("Stop Service", id="stop-service")
                yield Button("Restart Service", id="restart-service")

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
        Binding("tab", "next_tab", "Next Tab"),
        Binding("shift+tab", "prev_tab", "Previous Tab"),
        Binding("delete", "delete_selected", "Delete"),
        Binding("f2", "show_settings", "Settings"),
    ]

    def __init__(self):
        super().__init__()

        try:
            self.window_manager = WindowManager()
            self.app_manager = AppManager()
            self.settings = Settings()
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
                            with Horizontal():
                                yield Static("Applications", classes="heading")
                                yield Button("+", id="add-dropdown", classes="add-button")

                            with VerticalScroll():
                                self.app_list = ListView(id="app-list")
                                yield self.app_list

                            # Action buttons
                            with Horizontal(classes="action-buttons"):
                                yield Button("Edit", id="edit-app")
                                yield Button("Copy", id="copy-app")
                                yield Button("Launch", id="launch-app")

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
                            yield Button("Add Shortcut", id="add-shortcut")
                            yield Button("Edit Shortcut", id="edit-shortcut")
                            yield Button("Remove Shortcut", id="remove-shortcut")

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

            with TabPane("Settings", id="settings-tab"):
                with Container():
                    yield Static("Kayland Settings", classes="heading")

                    with Vertical():
                        with Horizontal(classes="action-buttons"):
                            yield Button("Edit Settings", id="edit-settings")
                            yield Button("About Kayland", id="about")

                        with VerticalScroll():
                            yield TextArea(
                                id="settings-info",
                                language="bash",
                                read_only=True,
                                text=(
                                    "This tab allows you to configure Kayland.\n\n"
                                    "Current Settings:\n"
                                    f"- Desktop File Directory: {self.settings.get('desktop_file_dir')}\n"
                                    f"- Confirm Deletions: {self.settings.get('confirm_delete')}\n\n"
                                    "Press 'Edit Settings' to modify these values."
                                )
                            )

        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted"""
        self._refresh_app_list()
        self._refresh_shortcut_list()
        self._update_settings_info()
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
            all_apps = {app["id"]: app for app in self.app_manager.get_all_apps()}

            for shortcut in shortcuts:
                app_id = shortcut.get("app_id", "")
                app_name = "Unknown"

                # Get app name if available
                app = all_apps.get(app_id)
                if app:
                    app_name = app["name"]

                # Add to table
                self.shortcut_table.add_row(
                    app_name,
                    shortcut.get("key", ""),
                    shortcut.get("description", ""),
                    key=shortcut.get("id", "")  # Store shortcut ID as row key
                )

            if not shortcuts:
                self.add_log_entry("No shortcuts found", "info")

        except Exception as e:
            error_msg = f"Failed to refresh shortcut list: {str(e)}"
            logger.error(error_msg)
            self.add_log_entry(error_msg, "error")
            self.notify(error_msg, severity="error")

    def _update_settings_info(self) -> None:
        """Update settings information display"""
        try:
            settings_info = self.query_one("#settings-info", TextArea)
            settings_text = (
                "This tab allows you to configure Kayland.\n\n"
                "Current Settings:\n"
                f"- Desktop File Directory: {self.settings.get('desktop_file_dir')}\n"
                f"- Confirm Deletions: {self.settings.get('confirm_delete')}\n\n"
                "Press 'Edit Settings' to modify these values."
            )
            settings_info.text = settings_text
        except Exception as e:
            logger.error(f"Error updating settings info: {str(e)}")

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

            # Display desktop file path if available
            desktop_file = app.get('desktop_file', '')
            if desktop_file:
                content.append(Text("Desktop File: ", style="#ff00a0"))
                content.append(Text(f"{desktop_file}\n\n", style="#ffffff"))

            content.append(Text("ID: ", style="#ff00a0"))
            content.append(Text(f"{app['id']}", style="#ffffff"))

            # Check for shortcuts associated with this app
            shortcuts = self.app_manager.get_shortcuts()
            app_shortcuts = [s for s in shortcuts if s.get("app_id") == app["id"]]
            if app_shortcuts:
                content.append(Text("\n\nShortcuts:", style="#ff00a0"))
                for shortcut in app_shortcuts:
                    content.append(Text(f"\n{shortcut.get('key', '')}", style="#ffffff"))
                    if shortcut.get("description"):
                        content.append(Text(f" - {shortcut.get('description', '')}", style="#aaaaaa"))

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
            shortcut_id = event.row_key.value
            self.selected_shortcut_id = shortcut_id

            # Get shortcut info for logging
            shortcuts = self.app_manager.get_shortcuts()
            shortcut = next((s for s in shortcuts if s.get("id") == shortcut_id), None)

            if shortcut:
                self.add_log_entry(f"Selected shortcut: {shortcut.get('key', '')}", "info")
            else:
                self.selected_shortcut_id = None

        except Exception as e:
            self.add_log_entry(f"Error selecting shortcut: {str(e)}", "error")
            self.selected_shortcut_id = None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        try:
            button_id = event.button.id

            if button_id == "add-dropdown":
                # Show the dropdown menu for add options
                self.push_screen(AppAddOptions())
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
            elif button_id == "edit-settings":
                self.action_show_settings()
            elif button_id == "about":
                self._show_about()

        except Exception as e:
            error_msg = f"Error handling button press: {str(e)}"
            logger.error(error_msg)
            self.add_log_entry(error_msg, "error")
            self.notify(error_msg, severity="error")

    def action_next_tab(self) -> None:
        """Move to the next tab"""
        tabs = self.query_one("#main-tabs", TabbedContent)
        # Get current tab index
        current_index = tabs.active
        # Calculate next index
        next_index = (current_index + 1) % len(tabs.tabs)
        # Activate next tab
        tabs.active = next_index

    def action_prev_tab(self) -> None:
        """Move to the previous tab"""
        tabs = self.query_one("#main-tabs", TabbedContent)
        # Get current tab index
        current_index = tabs.active
        # Calculate previous index
        prev_index = (current_index - 1) % len(tabs.tabs)
        # Activate previous tab
        tabs.active = prev_index

    def action_delete_selected(self) -> None:
        """Delete the selected item based on current tab"""
        tabs = self.query_one("#main-tabs", TabbedContent)
        tab_id = tabs.tabs[tabs.active].id

        # Check if confirm deletions is enabled
        confirm_deletions = self.settings.get("confirm_delete", "True") == "True"

        if tab_id == "apps-tab":
            app_id = self._get_selected_app_id()
            if app_id:
                app = self.app_manager.get_app_by_id(app_id)
                if app:
                    if confirm_deletions:
                        self.push_screen(
                            ConfirmDialog(
                                "Confirm Delete",
                                f"Are you sure you want to delete the application '{app['name']}'?"
                            ),
                            callback=self._confirm_delete_app
                        )
                    else:
                        self._delete_app(app_id)

        elif tab_id == "shortcuts-tab":
            if self.selected_shortcut_id:
                shortcuts = self.app_manager.get_shortcuts()
                shortcut = next((s for s in shortcuts if s.get("id") == self.selected_shortcut_id), None)

                if shortcut:
                    if confirm_deletions:
                        self.push_screen(
                            ConfirmDialog(
                                "Confirm Delete",
                                f"Are you sure you want to delete the shortcut '{shortcut.get('key', '')}'?"
                            ),
                            callback=self._confirm_delete_shortcut
                        )
                    else:
                        self._delete_shortcut(self.selected_shortcut_id)

    def _confirm_delete_app(self, confirmed: bool) -> None:
        """Handle confirmation for app deletion"""
        if confirmed:
            app_id = self._get_selected_app_id()
            if app_id:
                self._delete_app(app_id)

    def _confirm_delete_shortcut(self, confirmed: bool) -> None:
        """Handle confirmation for shortcut deletion"""
        if confirmed:
            if self.selected_shortcut_id:
                self._delete_shortcut(self.selected_shortcut_id)

    def _delete_app(self, app_id: str) -> None:
        """Delete an app by ID"""
        try:
            app = self.app_manager.get_app_by_id(app_id)
            if app:
                # Delete any associated shortcuts first
                shortcuts = self.app_manager.get_shortcuts()
                for shortcut in shortcuts:
                    if shortcut.get("app_id") == app_id:
                        self.app_manager.remove_shortcut(shortcut["id"])
                        self.add_log_entry(f"Removed shortcut for: {app['name']}", "success")

                # Delete the app
                self.app_manager.delete_app(app_id)
                message = f"Deleted app: {app['name']}"
                self.add_log_entry(message, "success")
                self.notify(message, timeout=3)

                # Refresh displays
                self.selected_app_id = None
                self._refresh_app_list()
                self._refresh_shortcut_list()
        except Exception as e:
            error_msg = f"Error deleting app: {str(e)}"
            self.add_log_entry(error_msg, "error")
            self.notify(error_msg, severity="error")
            logger.error(error_msg)

    def _delete_shortcut(self, shortcut_id: str) -> None:
        """Delete a shortcut by ID"""
        try:
            shortcuts = self.app_manager.get_shortcuts()
            shortcut = next((s for s in shortcuts if s.get("id") == shortcut_id), None)

            if shortcut:
                key = shortcut.get("key", "unknown")
                self.app_manager.remove_shortcut(shortcut_id)
                message = f"Deleted shortcut: {key}"
                self.add_log_entry(message, "success")
                self.notify(message, timeout=3)

                # Refresh display
                self.selected_shortcut_id = None
                self._refresh_shortcut_list()
        except Exception as e:
            error_msg = f"Error deleting shortcut: {str(e)}"
            self.add_log_entry(error_msg, "error")
            self.notify(error_msg, severity="error")
            logger.error(error_msg)

    def action_add_app(self) -> None:
        """Add a new application (show the dropdown for add options)"""
        # Get the add button position
        try:
            add_button = self.query_one("#add-dropdown", Button)
            button_rect = add_button.region
            self.push_screen(AppAddOptions(button_rect.x, button_rect.y + button_rect.height))
        except Exception as e:
            error_msg = f"Error showing add options: {str(e)}"
            logger.error(error_msg)
            self.add_log_entry(error_msg, "error")
            self.notify(error_msg, severity="error")

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
        try:
            # Check if there are any apps defined first
            all_apps = self.app_manager.get_all_apps()
            if not all_apps:
                self.notify("Please add at least one application before creating shortcuts",
                          severity="warning", timeout=5)
                self.add_log_entry("Cannot add shortcut: No applications defined", "warning")
                return

            self.add_log_entry("Opening add shortcut form", "info")
            self.push_screen(ShortcutScreen(self, self.app_manager))
        except Exception as e:
            error_msg = f"Error opening shortcut form: {str(e)}"
            self.add_log_entry(error_msg, "error")
            self.notify(error_msg, severity="error")

    def action_show_settings(self) -> None:
        """Show the settings screen"""
        self.push_screen(SettingsScreen(self, self.settings))

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
            # Check if confirm deletions is enabled
            confirm_deletions = self.settings.get("confirm_delete", "True") == "True"

            shortcuts = self.app_manager.get_shortcuts()
            shortcut = next((s for s in shortcuts if s.get("id") == self.selected_shortcut_id), None)

            if shortcut:
                if confirm_deletions:
                    self.push_screen(
                        ConfirmDialog(
                            "Confirm Delete",
                            f"Are you sure you want to delete the shortcut '{shortcut.get('key', '')}'?"
                        ),
                        callback=self._confirm_delete_shortcut
                    )
                else:
                    self._delete_shortcut(self.selected_shortcut_id)
        else:
            self.notify("No shortcut selected", severity="warning", timeout=2)

    def action_refresh(self) -> None:
        """Manually refresh the app list"""
        self.add_log_entry("Manually refreshing application list", "info")
        self._refresh_app_list()
        self._refresh_shortcut_list()
        self._update_settings_info()

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
        if hasattr(event, 'value') and event.value:
            # Check for selected option from dropdown
            if event.value.get('selected', None) == "Add manually":
                self.add_log_entry("Opening add application form", "info")
                self.push_screen(AppFormScreen(self, self.app_manager))
            elif event.value.get('selected', None) == "Add from .desktop":
                self.add_log_entry("Opening desktop file browser", "info")
                self.push_screen(DesktopFileScreen(self, self.settings.get("desktop_file_dir")))
            # Check for desktop file selection
            elif event.value.get('desktop_file', None):
                self.add_log_entry(f"Adding application from desktop file", "info")
                self.push_screen(AppFormScreen(self, self.app_manager, desktop_file=event.value['desktop_file']))
            # Check for changes to refresh
            elif event.value.get('changes_made', False):
                self.add_log_entry("Changes detected, refreshing data", "info")
                self._refresh_app_list()
                self._refresh_shortcut_list()
                self._update_settings_info()

    def _show_about(self) -> None:
        """Show information about the application"""
        about_text = """
Kayland - KDE Wayland Window Manager

A powerful window management tool for KDE Plasma on Wayland that allows you 
to quickly switch between applications, toggle window states, and create 
shortcuts for your most-used programs.

Features:
- Application Toggling
- Smart Window Management
- Global Shortcuts
- Terminal UI Interface

For more information, visit:
https://github.com/eraxe/kayland
"""
        self.notify(about_text, timeout=10)


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