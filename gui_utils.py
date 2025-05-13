#!/usr/bin/env python3
# gui_utils.py - Utilities and helpers for Kayland GUI

import os
import json
import logging
import configparser
import re
from typing import Dict, List, Any, Optional, Set, Tuple

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

logger = logging.getLogger("kayland.gui.utils")

# Constants
DEFAULT_SETTINGS = {
    "desktop_file_dir": "~/.local/share/applications",
    "theme": "system",
    "confirm_delete": "True"
}

# Dark theme colors for the GUI that match the synthwave feel of the TUI
SYNTHWAVE_COLORS = {
    "background": "#2b213a",
    "foreground": "#ffffff",
    "accent": "#f615f6",
    "accent2": "#00fff5",
    "accent3": "#ff00a0",
    "accent4": "#00ccff",
    "dark_bg": "#150a2d",
    "mid_bg": "#3b1f5f",
}


def apply_synthwave_theme(app):
    """Apply a synthwave-inspired dark theme to the application"""
    palette = QPalette()

    # Set color role for the application
    palette.setColor(QPalette.Window, QColor(SYNTHWAVE_COLORS["background"]))
    palette.setColor(QPalette.WindowText, QColor(SYNTHWAVE_COLORS["foreground"]))
    palette.setColor(QPalette.Base, QColor(SYNTHWAVE_COLORS["dark_bg"]))
    palette.setColor(QPalette.AlternateBase, QColor(SYNTHWAVE_COLORS["mid_bg"]))
    palette.setColor(QPalette.ToolTipBase, QColor(SYNTHWAVE_COLORS["foreground"]))
    palette.setColor(QPalette.ToolTipText, QColor(SYNTHWAVE_COLORS["background"]))
    palette.setColor(QPalette.Text, QColor(SYNTHWAVE_COLORS["foreground"]))
    palette.setColor(QPalette.Button, QColor(SYNTHWAVE_COLORS["accent2"]))
    palette.setColor(QPalette.ButtonText, QColor(SYNTHWAVE_COLORS["mid_bg"]))
    palette.setColor(QPalette.BrightText, QColor(SYNTHWAVE_COLORS["accent3"]))
    palette.setColor(QPalette.Link, QColor(SYNTHWAVE_COLORS["accent2"]))
    palette.setColor(QPalette.Highlight, QColor(SYNTHWAVE_COLORS["accent"]))
    palette.setColor(QPalette.HighlightedText, QColor(SYNTHWAVE_COLORS["foreground"]))

    # Apply the palette to the application
    app.setPalette(palette)

    # Set stylesheet for additional controls that aren't covered by the palette
    stylesheet = f"""
    QMainWindow, QDialog {{
        background-color: {SYNTHWAVE_COLORS["background"]};
    }}

    QTabWidget::pane {{
        border: 1px solid {SYNTHWAVE_COLORS["accent4"]};
        background-color: {SYNTHWAVE_COLORS["background"]};
    }}

    QTabBar::tab {{
        background-color: {SYNTHWAVE_COLORS["dark_bg"]};
        color: {SYNTHWAVE_COLORS["accent2"]};
        padding: 8px 16px;
        border: 1px solid {SYNTHWAVE_COLORS["accent4"]};
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }}

    QTabBar::tab:selected {{
        background-color: {SYNTHWAVE_COLORS["accent"]};
        color: {SYNTHWAVE_COLORS["foreground"]};
    }}

    QTabBar::tab:hover {{
        background-color: {SYNTHWAVE_COLORS["mid_bg"]};
    }}

    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {{
        background-color: {SYNTHWAVE_COLORS["dark_bg"]};
        color: {SYNTHWAVE_COLORS["foreground"]};
        border: 1px solid {SYNTHWAVE_COLORS["accent4"]};
        border-radius: 4px;
        padding: 4px;
    }}

    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{
        border: 1px solid {SYNTHWAVE_COLORS["accent"]};
    }}

    QPushButton {{
        background-color: {SYNTHWAVE_COLORS["accent2"]};
        color: {SYNTHWAVE_COLORS["mid_bg"]};
        border-radius: 4px;
        padding: 6px 12px;
        border: none;
    }}

    QPushButton:hover {{
        background-color: {SYNTHWAVE_COLORS["accent"]};
        color: {SYNTHWAVE_COLORS["foreground"]};
    }}

    QPushButton:pressed {{
        background-color: {SYNTHWAVE_COLORS["accent"]};
        color: {SYNTHWAVE_COLORS["foreground"]};
    }}

    QListView, QTreeView, QTableView {{
        background-color: {SYNTHWAVE_COLORS["dark_bg"]};
        color: {SYNTHWAVE_COLORS["foreground"]};
        border: 1px solid {SYNTHWAVE_COLORS["accent4"]};
        border-radius: 4px;
        selection-background-color: {SYNTHWAVE_COLORS["mid_bg"]};
        selection-color: {SYNTHWAVE_COLORS["foreground"]};
    }}

    QListView::item:selected {{
        background-color: {SYNTHWAVE_COLORS["mid_bg"]};
        border: 1px solid {SYNTHWAVE_COLORS["accent"]};
    }}

    QHeaderView::section {{
        background-color: {SYNTHWAVE_COLORS["mid_bg"]};
        color: {SYNTHWAVE_COLORS["accent2"]};
        padding: 4px;
        border: 1px solid {SYNTHWAVE_COLORS["accent4"]};
    }}

    QGroupBox {{
        border: 1px solid {SYNTHWAVE_COLORS["accent4"]};
        border-radius: 4px;
        margin-top: 16px;
    }}

    QGroupBox::title {{
        color: {SYNTHWAVE_COLORS["accent2"]};
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
    }}

    QStatusBar {{
        background-color: {SYNTHWAVE_COLORS["dark_bg"]};
        color: {SYNTHWAVE_COLORS["accent2"]};
    }}

    QLabel {{
        color: {SYNTHWAVE_COLORS["foreground"]};
    }}

    QLabel[title="true"] {{
        color: {SYNTHWAVE_COLORS["accent2"]};
        font-weight: bold;
    }}

    QLabel[heading="true"] {{
        color: {SYNTHWAVE_COLORS["accent"]};
        font-weight: bold;
        font-size: 14px;
    }}
    """

    app.setStyleSheet(stylesheet)


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