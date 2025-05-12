#!/usr/bin/env python3
# tui_widgets.py - Custom widget classes for Kayland TUI

import logging
from typing import Dict, Any, Optional

from textual import events
from textual.widgets import Static, ListItem
from textual.reactive import reactive
from textual.widget import Widget
from textual.containers import Container, Horizontal, Vertical
from rich.text import Text

logger = logging.getLogger("kayland.tui.widgets")


class AppListItemData(ListItem):
    """A list item representing an application"""

    def __init__(self, app_data: Dict[str, Any]):
        super().__init__()
        self._app_data = app_data
        self.can_focus = True

    @property
    def app_data(self) -> Dict[str, Any]:
        return self._app_data

    def compose(self):
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


class LogDisplay(Widget):
    """A widget to display log entries"""

    log_entries = reactive([])
    max_entries = reactive(100)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auto_scroll = True

    def compose(self):
        yield Static(id="log-content")

    def on_mount(self):
        self._update_display()

    def add_entry(self, message: str, level: str = "info") -> None:
        """Add a log entry to the log panel"""
        import time

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

            # Trim log entries if needed
            if len(self.log_entries) > self.max_entries:
                self.log_entries = self.log_entries[:self.max_entries]

            self._update_display()

        except Exception as e:
            # If we can't update the log UI, log to system logger
            logger.error(f"Failed to update log UI: {str(e)}")
            # And print to console as a fallback
            print(f"LOG ERROR: {str(e)}")
            print(f"[{level.upper()}] {message}")

    def _update_display(self) -> None:
        """Update the log content display"""
        try:
            log_content = self.query_one("#log-content", Static)
            if log_content:
                log_text = Text("\n").join(self.log_entries[:self.max_entries])
                log_content.update(log_text)
        except Exception as e:
            logger.error(f"Error updating log display: {str(e)}")

    def watch_log_entries(self) -> None:
        """Watch for changes to log entries"""
        self._update_display()