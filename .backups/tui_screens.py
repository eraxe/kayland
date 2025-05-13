#!/usr/bin/env python3
# tui_screens.py - Modal screens for Kayland TUI

import logging
import os
from typing import Dict, Any, Optional, List, Set, Tuple, Union, Callable

from textual.app import App
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Static, Input, ListView, Label, Switch, Tree
from textual.widgets import Select, DataTable, TextArea
from textual.containers import Container, Horizontal, Vertical, Grid, VerticalScroll
from textual.widget import Widget
from textual import events
from textual.css.query import NoMatches

# Import utilities
from tui_utils import safe_select_value, parse_desktop_file, find_desktop_files

logger = logging.getLogger("kayland.tui.screens")

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

    def compose(self):
        with Container(classes="dropdown-container"):
            for i, option in enumerate(self.options):
                option_class = "dropdown-option"
                if i == self.selected_option:
                    option_class += " dropdown-option-selected"
                yield Static(option, classes=option_class, id=f"option-{i}")

    def on_mount(self):
        """Position the dropdown near the button and highlight first option"""
        self._highlight_option(0)

    def action_previous_option(self):
        """Move selection to previous option"""
        self.selected_option = max(0, self.selected_option - 1)
        self._highlight_option(self.selected_option)

    def action_next_option(self):
        """Move selection to next option"""
        self.selected_option = min(len(self.options) - 1, self.selected_option + 1)
        self._highlight_option(self.selected_option)

    def action_select_option(self):
        """Select the current option"""
        self.dismiss({"selected": self.options[self.selected_option]})

    def action_close_screen(self):
        """Close the screen without selecting"""
        self.dismiss()

    def _highlight_option(self, index: int):
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
        # Set a background with opacity for the modal effect
        self.styles.background = "rgba(0, 0, 0, 0.7)"

    def compose(self):
        with Container(classes="form-container"):
            yield Static(self.title, classes="heading")
            yield Static(self.message, id="confirm-message")

            with Horizontal(classes="button-container"):
                yield Button("Cancel", id="cancel", variant="primary")
                yield Button("Confirm", id="confirm", variant="error")

    def on_button_pressed(self, event):
        """Handle button presses"""
        if event.button.id == "cancel":
            self.dismiss(False)
        elif event.button.id == "confirm":
            self.dismiss(True)

    def action_cancel(self):
        """Cancel the confirmation"""
        self.dismiss(False)


class AppFormScreen(ModalScreen):
    """Screen for adding or editing an app"""
    BINDINGS = [("escape", "close_screen", "Close"),
                ("f1", "toggle_shortcut", "Shortcut")]

    def __init__(self, parent_app: App, app_manager, app_id: str = None, desktop_file: Dict[str, Any] = None):
        super().__init__()
        self.parent_app = parent_app
        self.app_manager = app_manager
        self.app_id = app_id
        self.app_data = None
        self.desktop_file = desktop_file
        self.show_shortcut = False
        # Set a background with opacity for the modal effect
        self.styles.background = "rgba(0, 0, 0, 0.7)"

        if app_id:
            self.app_data = app_manager.get_app_by_id(app_id)

    def compose(self):
        is_edit = self.app_data is not None
        title = "Edit Application" if is_edit else "Add Application"

        with Container(classes="form-container"):
            yield Static(title, classes="heading")

            # Use Vertical + Horizontal for form layout
            with Vertical():
                with Horizontal(classes="form-row"):
                    yield Label("Name:", id="name-label")
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
                    yield Label("Class Pattern:", id="class-label")
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
                    yield Label("Command:", id="command-label")
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
                    yield Label("Aliases:", id="aliases-label")
                    yield Input(
                        id="aliases",
                        value=",".join(self.app_data.get("aliases", [])) if is_edit else "",
                        placeholder="app,app-alias,etc (comma-separated)"
                    )

                with Horizontal(classes="form-row"):
                    yield Label("Desktop File:", id="desktop-file-label")
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

    def action_close_screen(self):
        """Close the screen"""
        self.dismiss()

    def action_toggle_shortcut(self):
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

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses"""
        if event.button.id == "cancel":
            self.dismiss()
        elif event.button.id == "save":
            self._save_app()
        elif event.button.id == "delete":
            self._delete_app()

    def _save_app(self):
        """Save the app definition"""
        try:
            name = self.query_one("#name").value
            class_pattern = self.query_one("#class_pattern").value
            command = self.query_one("#command").value
            aliases_text = self.query_one("#aliases").value
            desktop_file = self.query_one("#desktop_file").value

            # Basic validation
            if not name or not class_pattern or not command:
                self.parent_app.notify("All fields except aliases and desktop file are required",
                                    severity="error")
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

    def _delete_app(self):
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
        # Set a background with opacity for the modal effect
        self.styles.background = "rgba(0, 0, 0, 0.7)"

    def compose(self):
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
                yield Button("Select File", id="select")

    def on_mount(self):
        """Populate the tree with desktop files"""
        self._populate_tree()

    def _populate_tree(self):
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

    def on_tree_node_selected(self, event):
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

    def on_button_pressed(self, event):
        """Handle button presses"""
        if event.button.id == "cancel":
            self.dismiss()
        elif event.button.id == "select":
            self.action_select_file()

    def action_select_file(self):
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

    def action_close_screen(self):
        """Close the screen"""
        self.dismiss()


class ShortcutScreen(ModalScreen):
    """Screen for adding or editing a shortcut"""
    BINDINGS = [("escape", "close_screen", "Close")]

    def __init__(self, parent_app: App, app_manager, shortcut_id: str = None):
        super().__init__()
        self.parent_app = parent_app
        self.app_manager = app_manager
        self.shortcut_id = shortcut_id
        self.shortcut_data = None
        self.all_apps = []
        self.app_options = []
        # Set a background with opacity for the modal effect
        self.styles.background = "rgba(0, 0, 0, 0.7)"

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

    def compose(self):
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

    def action_close_screen(self):
        """Close the screen"""
        self.dismiss()

    def on_button_pressed(self, event):
        """Handle button presses"""
        if event.button.id == "cancel":
            self.dismiss()
        elif event.button.id == "save":
            self._save_shortcut()
        elif event.button.id == "delete":
            self._delete_shortcut()

    def _save_shortcut(self):
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
            import re
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

    def _delete_shortcut(self):
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

    def __init__(self, parent_app: App, settings):
        super().__init__()
        self.parent_app = parent_app
        self.settings = settings
        # Set a background with opacity for the modal effect
        self.styles.background = "rgba(0, 0, 0, 0.7)"

    def compose(self):
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

    def on_button_pressed(self, event):
        """Handle button presses"""
        if event.button.id == "cancel":
            self.dismiss()
        elif event.button.id == "save":
            self._save_settings()

    def action_close_screen(self):
        """Close the screen"""
        self.dismiss()

    def _save_settings(self):
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