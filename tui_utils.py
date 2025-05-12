#!/usr/bin/env python3
# tui_utils.py - Utilities and helpers for Kayland TUI

import os
import json
import logging
import configparser
import re
from typing import Dict, List, Any, Optional, Set, Tuple

logger = logging.getLogger("kayland.tui.utils")

# Constants
DEFAULT_SETTINGS = {
    "desktop_file_dir": "~/.local/share/applications",
    "theme": "synthwave",
    "confirm_delete": "True"
}

# CSS for TUI
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
    min-height: 20;
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
    min-width: 30;
}

Input:focus {
    border: solid #f615f6;
}

ListView {
    border: solid #00ccff;
    background: #150a2d;
    height: 100%;
    margin-bottom: 1;
    min-height: 10;
}

ListItem {
    background: #150a2d;
    color: #ffffff;
    height: 1;
    padding: 0 1;
}

ListItem:hover {
    background: #3b1f5f;
    border: solid #f615f6;
}

ListItem:focus {
    background: #3b1f5f;
    border: solid #f615f6;
}

.selected {
    background: #3b1f5f !important;
    border: solid #f615f6 !important;
    color: #ffffff !important;
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
    height: 3;
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
    background: #2b213a;
    border: solid #00ccff;
}

Tab {
    background: #150a2d;
    color: #00fff5;
    padding: 1 2;
    height: 3;
}

Tab:hover {
    background: #3b1f5f;
    color: #ffffff;
}

Tab.-active {
    background: #f615f6;
    color: #ffffff;
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
    min-height: 10;
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
    min-height: 10;
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
"""

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