#!/usr/bin/env python3
# tui_app.py - Main Kayland TUI application

import sys
import logging
import os
import time
import subprocess
import re
from typing import Dict, List, Optional, Any, Set, Tuple, Union

from textual.app import App
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, Grid, VerticalScroll
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widgets import (
    Header, Footer, Button, Static, Input, ListView, ListItem, Label,
    Switch, DataTable, TextArea, Tab
)
from textual import events
from textual.widgets import TabbedContent, TabPane
from rich.text import Text

# Import custom widgets and screens
from tui_service import ServiceStatusWidget
from tui_widgets import AppListItemData, AppSelectedMessage, LogDisplay
from tui_screens import (
    AppAddOptions, ConfirmDialog, AppFormScreen,
    DesktopFileScreen, ShortcutScreen, SettingsScreen
)

# Import styling
from tui_utils import SYNTHWAVE_CSS

logger = logging.getLogger("kayland.tui.app")


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
        Binding("f1", "toggle_debug", "Debug"),
    ]

    def __init__(self, window_manager=None, app_manager=None, settings=None):
        super().__init__()

        try:
            self.window_manager = window_manager
            self.app_manager = app_manager
            self.settings = settings
            self.selected_app_id = None
            self.selected_shortcut_id = None
            self._debug_mode = False
            self.log_display = LogDisplay()
        except Exception as e:
            logger.error(f"Failed to initialize managers: {str(e)}")
            print(f"Error: Failed to initialize: {str(e)}")
            sys.exit(1)

    def compose(self):
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
                                yield self.log_display

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

    def on_mount(self):
        """Called when the app is mounted"""
        try:
            self.add_log_entry("Starting Kayland TUI...", "info")
            self._refresh_app_list()
            self._refresh_shortcut_list()
            self._update_settings_info()
            self.add_log_entry("Kayland TUI started successfully", "success")

            # Ensure tab navigation works
            tabs = self.query_one("#main-tabs", TabbedContent)
            if tabs:
                # Start with the first tab active
                tabs.active = 0
        except Exception as e:
            logger.error(f"Error in on_mount: {str(e)}")
            self.add_log_entry(f"Error during startup: {str(e)}", "error")

    def add_log_entry(self, message: str, level: str = "info") -> None:
        """Add a log entry to the log panel"""
        try:
            # Use the LogDisplay widget
            self.log_display.add_entry(message, level)
        except Exception as e:
            # If we can't update the log UI, log to system logger
            logger.error(f"Failed to update log UI: {str(e)}")
            # And print to console as a fallback
            print(f"LOG ERROR: {str(e)}")
            print(f"[{level.upper()}] {message}")

    def action_toggle_debug(self) -> None:
        """Toggle debug information display"""
        try:
            # Get current state
            is_debug = getattr(self, "_debug_mode", False)
            self._debug_mode = not is_debug

            # Update log
            self.add_log_entry(f"Debug mode: {'ON' if self._debug_mode else 'OFF'}", "info")

            if self._debug_mode:
                # Display information about the current state
                debug_info = [
                    f"Textual version: {__import__('textual').__version__}",
                    f"Current size: {self.size}",
                    f"Selected app ID: {self.selected_app_id}",
                    f"Selected shortcut ID: {self.selected_shortcut_id}",
                    f"Number of apps: {len(self.app_manager.get_all_apps())}",
                    f"Number of shortcuts: {len(self.app_manager.get_shortcuts())}",
                ]

                # Get widget information
                try:
                    app_list = self.query_one("#app-list", ListView)
                    debug_info.append(f"App list size: {app_list.size}")
                    debug_info.append(f"App list children: {len(list(app_list.children))}")
                except Exception as e:
                    debug_info.append(f"Error getting app list info: {str(e)}")

                self.add_log_entry("\n".join(debug_info), "info")
        except Exception as e:
            self.add_log_entry(f"Error toggling debug: {str(e)}", "error")

    def _refresh_app_list(self) -> None:
        """Refresh the application list"""
        try:
            # Get apps directly from app_manager
            apps = self.app_manager.get_all_apps()

            # Debug info
            self.add_log_entry(f"Refreshing app list, found {len(apps)} apps", "info")

            # Completely rebuild the list from scratch
            self.app_list.clear()

            if not apps:
                # Add a placeholder item if no apps
                self.app_list.append(ListItem(Static("No applications defined yet. Press 'a' to add.")))
                return

            # Add apps to the list
            for app in apps:
                # Create a new app list item
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

            # Explicitly refresh the app list to ensure it's visible
            self.app_list.refresh()

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

            # Add table header if needed
            if not self.shortcut_table.columns:
                self.shortcut_table.add_columns("App", "Key", "Description")

            # Get shortcuts from app manager
            shortcuts = self.app_manager.get_shortcuts()
            all_apps = {app["id"]: app for app in self.app_manager.get_all_apps()}

            if not shortcuts:
                # Add a placeholder row
                self.shortcut_table.add_row(
                    "No shortcuts defined",
                    "Press 's' to add",
                    "",
                    key="placeholder"
                )
                self.add_log_entry("No shortcuts found", "info")
                return

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

            # Ensure table is visible
            self.shortcut_table.refresh()

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
        try:
            detail_content = self.query_one("#app-detail-content")

            if app:
                # Create a formatted string with markup instead of a Text object
                content_lines = []
                content_lines.append("[#ff00a0]Name:[/] " + f"[#ffffff]{app['name']}[/]")
                content_lines.append("")
                content_lines.append("[#ff00a0]Class Pattern:[/] " + f"[#ffffff]{app['class_pattern']}[/]")
                content_lines.append("")
                content_lines.append("[#ff00a0]Command:[/] " + f"[#ffffff]{app['command']}[/]")
                content_lines.append("")

                aliases = ", ".join(app.get('aliases', []))
                content_lines.append("[#ff00a0]Aliases:[/] " + f"[#ffffff]{aliases}[/]")
                content_lines.append("")

                # Display desktop file path if available
                desktop_file = app.get('desktop_file', '')
                if desktop_file:
                    content_lines.append("[#ff00a0]Desktop File:[/] " + f"[#ffffff]{desktop_file}[/]")
                    content_lines.append("")

                content_lines.append("[#ff00a0]ID:[/] " + f"[#ffffff]{app['id']}[/]")

                # Check for shortcuts associated with this app
                shortcuts = self.app_manager.get_shortcuts()
                app_shortcuts = [s for s in shortcuts if s.get("app_id") == app["id"]]
                if app_shortcuts:
                    content_lines.append("")
                    content_lines.append("[#ff00a0]Shortcuts:[/]")
                    for shortcut in app_shortcuts:
                        shortcut_line = f"[#ffffff]{shortcut.get('key', '')}[/]"
                        if shortcut.get("description"):
                            shortcut_line += f" [#aaaaaa]- {shortcut.get('description', '')}[/]"
                        content_lines.append(shortcut_line)

                # Update the content
                detail_content.update("\n".join(content_lines))
            else:
                detail_content.update(
                    "\n  No application selected.\n\n  Select an application from the list or add a new one.")
        except Exception as e:
            logger.error(f"Error updating app details: {str(e)}")
            self.add_log_entry(f"Error updating app details: {str(e)}", "error")

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

    def on_data_table_row_selected(self, event) -> None:
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
        try:
            tabs = self.query_one("#main-tabs", TabbedContent)
            # Get current tab index
            current_index = tabs.active
            # Calculate next index
            next_index = (current_index + 1) % len(tabs.tabs)
            # Activate next tab
            tabs.active = next_index
        except Exception as e:
            self.add_log_entry(f"Error changing tab: {str(e)}", "error")

    def action_prev_tab(self) -> None:
        """Move to the previous tab"""
        try:
            tabs = self.query_one("#main-tabs", TabbedContent)
            # Get current tab index
            current_index = tabs.active
            # Calculate previous index
            prev_index = (current_index - 1) % len(tabs.tabs)
            # Activate previous tab
            tabs.active = prev_index
        except Exception as e:
            self.add_log_entry(f"Error changing tab: {str(e)}", "error")

    def action_delete_selected(self) -> None:
        """Delete the selected item based on current tab"""
        try:
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
        except Exception as e:
            self.add_log_entry(f"Error deleting selected item: {str(e)}", "error")

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
        try:
            # Show the add options dropdown
            self.push_screen(AppAddOptions())
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
        try:
            # First refresh data to ensure UI is up-to-date
            self._refresh_app_list()
            self._refresh_shortcut_list()

            # Check if the modal screen passed a value indicating changes were made
            if hasattr(event, 'value') and event.value:
                # Check for selected option from dropdown
                if isinstance(event.value, dict):
                    if event.value.get('selected', None) == "Add manually":
                        self.add_log_entry("Opening add application form", "info")
                        self.push_screen(AppFormScreen(self, self.app_manager))
                    elif event.value.get('selected', None) == "Add from .desktop":
                        self.add_log_entry("Opening desktop file browser", "info")
                        self.push_screen(DesktopFileScreen(self, self.settings.get("desktop_file_dir")))
                    # Check for desktop file selection
                    elif event.value.get('desktop_file', None):
                        self.add_log_entry(f"Adding application from desktop file", "info")
                        self.push_screen(
                            AppFormScreen(self, self.app_manager, desktop_file=event.value['desktop_file']))
                    # Check for changes to refresh
                    elif event.value.get('changes_made', False):
                        self.add_log_entry("Changes detected, refreshing data", "info")
                        self._update_settings_info()
        except Exception as e:
            self.add_log_entry(f"Error in screen resume: {str(e)}", "error")

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