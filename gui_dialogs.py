#!/usr/bin/env python3
# gui_dialogs.py - Dialog classes for Kayland GUI

import os
import logging
import re
from typing import Dict, List, Any, Optional, Callable, Union, Tuple

from PySide6.QtCore import Qt, Signal, Slot, QSize
# Fix: Import QAction from QtGui, not QtWidgets
from PySide6.QtGui import QIcon, QAction, QKeySequence, QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox,
    QListWidget, QListWidgetItem, QDialogButtonBox, QFileDialog,
    QTabWidget, QWidget, QCheckBox, QMessageBox, QTreeWidget,
    QTreeWidgetItem, QSplitter, QGroupBox, QFrame, QToolButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMenu
)

from gui_widgets import LogWidget
from gui_utils import parse_desktop_file, find_desktop_files, SYNTHWAVE_COLORS

logger = logging.getLogger("kayland.gui.dialogs")


class ConfirmDialog(QDialog):
    """Simple confirmation dialog"""

    def __init__(self, title: str, message: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)

        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Add message
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)

        # Add buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setMinimumWidth(400)


class AppFormDialog(QDialog):
    """Dialog for adding or editing an application"""

    def __init__(self, app_manager, app_id=None, desktop_file=None, parent=None):
        title = "Edit Application" if app_id else "Add Application"
        super().__init__(parent)
        self.setWindowTitle(title)

        self.app_manager = app_manager
        self.app_id = app_id
        self.desktop_file = desktop_file
        self.app_data = None
        self.show_shortcut = False

        if app_id:
            self.app_data = app_manager.get_app_by_id(app_id)

        self.setup_ui()

    def setup_ui(self):
        """Set up the dialog UI"""
        is_edit = self.app_data is not None

        # Create main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Create form layout
        form_layout = QFormLayout()

        # Application name
        self.name_input = QLineEdit()
        if self.desktop_file:
            self.name_input.setText(self.desktop_file.get("name", ""))
        elif is_edit:
            self.name_input.setText(self.app_data["name"])
        form_layout.addRow("Name:", self.name_input)

        # Class pattern
        self.class_pattern_input = QLineEdit()
        if self.desktop_file:
            self.class_pattern_input.setText(self.desktop_file.get("class", ""))
        elif is_edit:
            self.class_pattern_input.setText(self.app_data["class_pattern"])
        form_layout.addRow("Class Pattern:", self.class_pattern_input)

        # Command
        self.command_input = QLineEdit()
        if self.desktop_file:
            self.command_input.setText(self.desktop_file.get("exec", ""))
        elif is_edit:
            self.command_input.setText(self.app_data["command"])
        form_layout.addRow("Command:", self.command_input)

        # Aliases
        self.aliases_input = QLineEdit()
        if is_edit:
            self.aliases_input.setText(",".join(self.app_data.get("aliases", [])))
        form_layout.addRow("Aliases:", self.aliases_input)

        # Desktop file
        self.desktop_file_input = QLineEdit()
        if self.desktop_file:
            self.desktop_file_input.setText(self.desktop_file.get("path", ""))
        elif is_edit:
            self.desktop_file_input.setText(self.app_data.get("desktop_file", ""))

        # Add browse button for desktop file
        desktop_file_layout = QHBoxLayout()
        desktop_file_layout.addWidget(self.desktop_file_input)

        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_desktop_file)
        desktop_file_layout.addWidget(browse_button)

        form_layout.addRow("Desktop File:", desktop_file_layout)

        # Add form layout to main layout
        layout.addLayout(form_layout)

        # Shortcut group
        self.shortcut_group = QGroupBox("Shortcut Settings")
        self.shortcut_group.setCheckable(True)
        self.shortcut_group.setChecked(False)

        shortcut_layout = QFormLayout()

        # Shortcut key
        self.shortcut_key_input = QLineEdit()
        if is_edit:
            self.shortcut_key_input.setText(self._get_existing_shortcut())
        shortcut_layout.addRow("Shortcut Key:", self.shortcut_key_input)

        # Shortcut description
        self.shortcut_description_input = QLineEdit()
        if is_edit:
            self.shortcut_description_input.setText(self._get_existing_shortcut_description())
        shortcut_layout.addRow("Description:", self.shortcut_description_input)

        self.shortcut_group.setLayout(shortcut_layout)
        layout.addWidget(self.shortcut_group)

        # Buttons
        button_layout = QHBoxLayout()

        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        # Save button
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_app)
        button_layout.addWidget(self.save_button)

        # Delete button (edit mode only)
        if is_edit:
            delete_button = QPushButton("Delete")
            delete_button.setStyleSheet(f"background-color: #ff4444; color: {SYNTHWAVE_COLORS['active_text']};")
            delete_button.clicked.connect(self.delete_app)
            button_layout.addWidget(delete_button)

        layout.addLayout(button_layout)

        # Set dialog size
        self.resize(500, 400)

    def get_asset_path(self, file_name):
        """Get the correct path to an asset file considering various installation scenarios"""
        # Try multiple possible locations
        potential_paths = [
            # Check for assets in the same directory as the script
            os.path.join(os.path.dirname(__file__), file_name),
            # Check for assets in the parent directory
            os.path.join(os.path.dirname(os.path.dirname(__file__)), file_name),
            # Check for assets in a dedicated assets directory
            os.path.join(os.path.dirname(__file__), "assets", file_name),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", file_name),
            # Check for system-wide installation
            os.path.expanduser(f"~/.local/share/kayland/assets/{file_name}"),
            # More general install locations
            f"/usr/share/kayland/assets/{file_name}",
            f"/usr/local/share/kayland/assets/{file_name}"
        ]

        for path in potential_paths:
            if os.path.exists(path):
                return path

        # If no file is found, log a warning but return the first path anyway
        logger.warning(f"Asset file not found: {file_name}")
        return potential_paths[0]

    def browse_desktop_file(self):
        """Open file dialog to browse for desktop files"""
        config_dir = os.path.expanduser("~/.config/kayland")
        settings_file = os.path.join(config_dir, "settings.json")

        # Try to get desktop file directory from settings
        desktop_dir = "~/.local/share/applications"
        try:
            import json
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    desktop_dir = settings.get("desktop_file_dir", desktop_dir)
        except Exception as e:
            logger.error(f"Error reading settings: {str(e)}")

        # Expand path
        desktop_dir = os.path.expanduser(desktop_dir)

        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Desktop File", desktop_dir, "Desktop Files (*.desktop)"
        )

        if file_path:
            self.desktop_file_input.setText(file_path)

            # Parse the desktop file
            desktop_data = parse_desktop_file(file_path)

            # Auto-fill fields if they're empty
            if not self.name_input.text() and desktop_data.get("name"):
                self.name_input.setText(desktop_data.get("name"))

            if not self.class_pattern_input.text() and desktop_data.get("class"):
                self.class_pattern_input.setText(desktop_data.get("class"))

            if not self.command_input.text() and desktop_data.get("exec"):
                self.command_input.setText(desktop_data.get("exec"))

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

    def save_app(self):
        """Save the app definition"""
        try:
            name = self.name_input.text()
            class_pattern = self.class_pattern_input.text()
            command = self.command_input.text()
            aliases_text = self.aliases_input.text()
            desktop_file = self.desktop_file_input.text()

            # Basic validation
            if not name or not class_pattern or not command:
                QMessageBox.warning(self, "Validation Error",
                                    "All fields except aliases and desktop file are required")
                return

            # Process aliases, removing empty entries
            aliases = [a.strip() for a in aliases_text.split(",") if a.strip()]

            # Get shortcut data if enabled
            shortcut_key = ""
            shortcut_description = ""
            if self.shortcut_group.isChecked():
                shortcut_key = self.shortcut_key_input.text()
                shortcut_description = self.shortcut_description_input.text()

                # Validate shortcut format
                if shortcut_key and not re.match(r'^[a-z0-9+]+$', shortcut_key.lower()):
                    QMessageBox.warning(self, "Validation Error",
                                        "Invalid shortcut format. Use format like 'alt+b'")
                    return

            # Update or create app
            try:
                parent = self.parent()
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
                    if hasattr(parent, "add_log_entry"):
                        parent.add_log_entry(message, "success")
                    if hasattr(parent, "show_status_message"):
                        parent.show_status_message(message)

                    # Handle shortcut update/creation
                    if shortcut_key:
                        shortcut_id = self._get_existing_shortcut_id()
                        if shortcut_id:
                            # Update existing shortcut
                            self.app_manager.update_shortcut(
                                shortcut_id, self.app_id, shortcut_key, shortcut_description
                            )
                            if hasattr(parent, "add_log_entry"):
                                parent.add_log_entry(f"Updated shortcut: {shortcut_key}", "success")
                        else:
                            # Create new shortcut
                            self.app_manager.add_shortcut(self.app_id, shortcut_key, shortcut_description)
                            if hasattr(parent, "add_log_entry"):
                                parent.add_log_entry(f"Added shortcut: {shortcut_key}", "success")
                    elif self._get_existing_shortcut_id() and not self.shortcut_group.isChecked():
                        # Remove existing shortcut if the shortcut group is unchecked
                        shortcut_id = self._get_existing_shortcut_id()
                        self.app_manager.remove_shortcut(shortcut_id)
                        if hasattr(parent, "add_log_entry"):
                            parent.add_log_entry(f"Removed shortcut", "success")

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

                    message = f"Added app: {name}"
                    if hasattr(parent, "add_log_entry"):
                        parent.add_log_entry(message, "success")
                    if hasattr(parent, "show_status_message"):
                        parent.show_status_message(message)

                    # Create shortcut if provided
                    if shortcut_key:
                        self.app_manager.add_shortcut(app["id"], shortcut_key, shortcut_description)
                        if hasattr(parent, "add_log_entry"):
                            parent.add_log_entry(f"Added shortcut: {shortcut_key}", "success")

                # Success - close dialog
                self.accept()

            except ValueError as e:
                QMessageBox.warning(self, "Error", f"Error: {str(e)}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error: {str(e)}")
            logger.error(f"Error saving app: {str(e)}")

    def delete_app(self):
        """Delete the app definition"""
        if not self.app_id:
            return

        # Confirm deletion
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete {self.app_data['name']}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            try:
                parent = self.parent()
                name = self.app_data["name"]

                # Delete any associated shortcuts first
                shortcuts = self.app_manager.get_shortcuts()
                for shortcut in shortcuts:
                    if shortcut.get("app_id") == self.app_id:
                        self.app_manager.remove_shortcut(shortcut["id"])
                        if hasattr(parent, "add_log_entry"):
                            parent.add_log_entry(f"Removed shortcut for: {name}", "success")

                # Delete the app
                self.app_manager.delete_app(self.app_id)
                message = f"Deleted app: {name}"
                if hasattr(parent, "add_log_entry"):
                    parent.add_log_entry(message, "success")
                if hasattr(parent, "show_status_message"):
                    parent.show_status_message(message)

                # Close dialog
                self.accept()

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error: {str(e)}")
                logger.error(f"Error deleting app: {str(e)}")


class DesktopFileDialog(QDialog):
    """Dialog for selecting a desktop file"""

    def __init__(self, parent=None, desktop_dir=None):
        super().__init__(parent)
        self.setWindowTitle("Select Desktop File")

        self.desktop_dir = desktop_dir or os.path.expanduser("~/.local/share/applications")
        self.selected_file = None
        self.selected_data = None

        self.setup_ui()
        self.populate_tree()

    def setup_ui(self):
        """Set up the dialog UI"""
        # Create main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Create a splitter for the file list and preview
        splitter = QSplitter(Qt.Horizontal)

        # File list
        file_list_widget = QWidget()
        file_list_layout = QVBoxLayout(file_list_widget)
        file_list_layout.setContentsMargins(0, 0, 0, 0)

        # Label for file list
        file_list_label = QLabel("Desktop Files")
        file_list_label.setProperty("heading", True)
        file_list_layout.addWidget(file_list_label)

        # Tree widget for files
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderHidden(True)
        self.file_tree.itemSelectionChanged.connect(self.on_selection_changed)
        file_list_layout.addWidget(self.file_tree)

        # Preview pane
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        # Label for preview
        preview_label = QLabel("File Preview")
        preview_label.setProperty("heading", True)
        preview_layout.addWidget(preview_label)

        # Preview content
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        preview_layout.addWidget(self.preview_text)

        # Add widgets to splitter
        splitter.addWidget(file_list_widget)
        splitter.addWidget(preview_widget)
        splitter.setSizes([200, 300])  # Initial split sizes

        layout.addWidget(splitter)

        # Buttons
        button_layout = QHBoxLayout()

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        select_button = QPushButton("Select File")
        select_button.clicked.connect(self.accept)
        select_button.setEnabled(False)
        self.select_button = select_button
        button_layout.addWidget(select_button)

        layout.addLayout(button_layout)

        # Set dialog size
        self.resize(700, 500)

    def populate_tree(self):
        """Populate the tree with desktop files"""
        try:
            self.file_tree.clear()

            # Create root item
            root_name = os.path.basename(os.path.expanduser(self.desktop_dir))
            root_item = QTreeWidgetItem([root_name])
            self.file_tree.addTopLevelItem(root_item)

            # Find desktop files
            desktop_files = find_desktop_files(self.desktop_dir)

            # Parse and add to tree
            for file_path in sorted(desktop_files):
                desktop_data = parse_desktop_file(file_path)
                display_name = desktop_data["name"] or os.path.basename(file_path)

                # Create tree item
                file_item = QTreeWidgetItem([display_name])
                file_item.setData(0, Qt.UserRole, {"path": file_path, "data": desktop_data})
                root_item.addChild(file_item)

            # Expand root
            root_item.setExpanded(True)

        except Exception as e:
            logger.error(f"Error populating desktop file tree: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error listing desktop files: {str(e)}")

    def on_selection_changed(self):
        """Handle selection changes in the tree"""
        selected_items = self.file_tree.selectedItems()

        if selected_items:
            item = selected_items[0]
            item_data = item.data(0, Qt.UserRole)

            if item_data:
                file_path = item_data.get("path")
                desktop_data = item_data.get("data")

                if file_path and desktop_data:
                    self.selected_file = file_path
                    self.selected_data = desktop_data
                    self.select_button.setEnabled(True)

                    # Update preview
                    preview = ""
                    preview += f"Name: {desktop_data.get('name', '')}\n"
                    preview += f"Exec: {desktop_data.get('exec', '')}\n"
                    preview += f"Class: {desktop_data.get('class', '')}\n"
                    preview += f"Icon: {desktop_data.get('icon', '')}\n"
                    preview += f"Comment: {desktop_data.get('comment', '')}\n"

                    # Add raw file content
                    try:
                        with open(file_path, 'r') as f:
                            preview += "\n--- Raw Content ---\n"
                            preview += f.read()
                    except Exception as e:
                        preview += f"\nError reading file: {str(e)}"

                    self.preview_text.setPlainText(preview)
                    return

        # No valid selection
        self.selected_file = None
        self.selected_data = None
        self.select_button.setEnabled(False)
        self.preview_text.setPlainText("")

    def accept(self):
        """Accept the dialog with the selected file"""
        if self.selected_file and self.selected_data:
            super().accept()
        else:
            QMessageBox.warning(self, "Selection Required", "Please select a desktop file")


class ShortcutDialog(QDialog):
    """Dialog for adding or editing shortcuts"""

    def __init__(self, app_manager, shortcut_id=None, parent=None):
        title = "Edit Shortcut" if shortcut_id else "Add Shortcut"
        super().__init__(parent)
        self.setWindowTitle(title)

        self.app_manager = app_manager
        self.shortcut_id = shortcut_id
        self.shortcut_data = None
        self.all_apps = []

        # Load shortcut data if editing
        if shortcut_id:
            self.shortcut_data = app_manager.get_shortcut_by_id(shortcut_id)

        # Pre-load all apps
        self.all_apps = app_manager.get_all_apps()

        self.setup_ui()

    def setup_ui(self):
        """Set up the dialog UI"""
        # Create main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Create form layout
        form_layout = QFormLayout()

        # Application selector
        self.app_combo = QComboBox()
        self.app_combo.setMinimumWidth(250)

        # Populate app options
        for app in self.all_apps:
            self.app_combo.addItem(app["name"], app["id"])

        # Set current app if editing
        if self.shortcut_data and "app_id" in self.shortcut_data:
            app_id = self.shortcut_data["app_id"]
            for i in range(self.app_combo.count()):
                if self.app_combo.itemData(i) == app_id:
                    self.app_combo.setCurrentIndex(i)
                    break

        form_layout.addRow("Application:", self.app_combo)

        # Shortcut key
        self.key_input = QLineEdit()
        if self.shortcut_data:
            self.key_input.setText(self.shortcut_data["key"])
        form_layout.addRow("Shortcut Key:", self.key_input)

        # Description
        self.description_input = QLineEdit()
        if self.shortcut_data:
            self.description_input.setText(self.shortcut_data.get("description", ""))
        form_layout.addRow("Description:", self.description_input)

        layout.addLayout(form_layout)

        # Help text
        help_text = QLabel("Shortcut format: alt+b, ctrl+shift+g, etc.")
        help_text.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(help_text)

        # Buttons
        button_layout = QHBoxLayout()

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_shortcut)
        button_layout.addWidget(save_button)

        if self.shortcut_id:
            delete_button = QPushButton("Delete")
            delete_button.setStyleSheet(f"background-color: #ff4444; color: {SYNTHWAVE_COLORS['active_text']};")
            delete_button.clicked.connect(self.delete_shortcut)
            button_layout.addWidget(delete_button)

        layout.addLayout(button_layout)

        # Set dialog size
        self.resize(400, 250)

    def save_shortcut(self):
        """Save the shortcut"""
        try:
            app_id = self.app_combo.currentData()
            key = self.key_input.text()
            description = self.description_input.text()

            # Validation
            if not app_id:
                QMessageBox.warning(self, "Validation Error", "Please select an application")
                return

            if not key:
                QMessageBox.warning(self, "Validation Error", "Shortcut key is required")
                return

            # Validate shortcut format
            if not re.match(r'^[a-z0-9+]+$', key.lower()):
                QMessageBox.warning(self, "Validation Error",
                                    "Invalid shortcut format. Use format like 'alt+b'")
                return

            # Update or create shortcut
            parent = self.parent()
            try:
                if self.shortcut_id:
                    self.app_manager.update_shortcut(
                        self.shortcut_id, app_id, key, description
                    )
                    message = f"Updated shortcut: {key}"
                    if hasattr(parent, "add_log_entry"):
                        parent.add_log_entry(message, "success")
                    if hasattr(parent, "show_status_message"):
                        parent.show_status_message(message)
                else:
                    shortcut = self.app_manager.add_shortcut(app_id, key, description)
                    message = f"Added shortcut: {key}"
                    if hasattr(parent, "add_log_entry"):
                        parent.add_log_entry(message, "success")
                    if hasattr(parent, "show_status_message"):
                        parent.show_status_message(message)

                # Success - close dialog
                self.accept()

            except ValueError as e:
                QMessageBox.warning(self, "Error", f"Error: {str(e)}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error: {str(e)}")
            logger.error(f"Error saving shortcut: {str(e)}")

    def delete_shortcut(self):
        """Delete the shortcut"""
        if not self.shortcut_id:
            return

        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete this shortcut?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            try:
                parent = self.parent()
                key = self.shortcut_data["key"] if self.shortcut_data else "unknown"

                self.app_manager.remove_shortcut(self.shortcut_id)
                message = f"Deleted shortcut: {key}"

                if hasattr(parent, "add_log_entry"):
                    parent.add_log_entry(message, "success")
                if hasattr(parent, "show_status_message"):
                    parent.show_status_message(message)

                # Close dialog
                self.accept()

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error: {str(e)}")
                logger.error(f"Error deleting shortcut: {str(e)}")


class SettingsDialog(QDialog):
    """Dialog for application settings"""

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kayland Settings")
        self.settings = settings
        self.setup_ui()

    def setup_ui(self):
        """Set up the dialog UI"""
        # Create main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Create form layout
        form_layout = QFormLayout()

        # Desktop file directory
        self.desktop_dir_input = QLineEdit()
        self.desktop_dir_input.setText(self.settings.get("desktop_file_dir", "~/.local/share/applications"))

        desktop_dir_layout = QHBoxLayout()
        desktop_dir_layout.addWidget(self.desktop_dir_input)

        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_desktop_dir)
        desktop_dir_layout.addWidget(browse_button)

        form_layout.addRow("Desktop File Directory:", desktop_dir_layout)

        # Log level selector
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItem("Debug", "DEBUG")
        self.log_level_combo.addItem("Info", "INFO")
        self.log_level_combo.addItem("Warning", "WARNING")
        self.log_level_combo.addItem("Error", "ERROR")

        # Set current log level
        current_log_level = self.settings.get("log_level", "INFO")
        index = self.log_level_combo.findData(current_log_level)
        if index >= 0:
            self.log_level_combo.setCurrentIndex(index)

        form_layout.addRow("Log Level:", self.log_level_combo)

        # Confirm deletions
        self.confirm_delete_check = QCheckBox("Confirm before deleting apps or shortcuts")
        self.confirm_delete_check.setChecked(self.settings.get("confirm_delete", "True") == "True")
        form_layout.addRow("", self.confirm_delete_check)

        layout.addLayout(form_layout)

        # Buttons
        button_layout = QHBoxLayout()

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_settings)
        button_layout.addWidget(save_button)

        layout.addLayout(button_layout)

        # Set dialog size
        self.resize(500, 250)

    def browse_desktop_dir(self):
        """Open dialog to select desktop file directory"""
        current_dir = os.path.expanduser(self.desktop_dir_input.text())

        # Open directory dialog
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Desktop File Directory", current_dir
        )

        if dir_path:
            self.desktop_dir_input.setText(dir_path)

    def save_settings(self):
        """Save the settings"""
        try:
            desktop_file_dir = self.desktop_dir_input.text()
            confirm_delete = str(self.confirm_delete_check.isChecked())
            log_level = self.log_level_combo.currentData()

            # Update settings
            self.settings.set("desktop_file_dir", desktop_file_dir)
            self.settings.set("confirm_delete", confirm_delete)
            self.settings.set("log_level", log_level)

            # Update logging level
            root_logger = logging.getLogger()
            root_logger.setLevel(getattr(logging, log_level))

            parent = self.parent()
            message = "Settings saved successfully"
            if hasattr(parent, "add_log_entry"):
                parent.add_log_entry(message, "success")
            if hasattr(parent, "show_status_message"):
                parent.show_status_message(message)

            # Close dialog
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving settings: {str(e)}")
            logger.error(f"Error saving settings: {str(e)}")


class AboutDialog(QDialog):
    """Dialog showing information about the application"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Kayland")
        self.setup_ui()

    def setup_ui(self):
        """Set up the dialog UI"""
        # Create main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel("Kayland - KDE Wayland Window Manager")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {SYNTHWAVE_COLORS['hover_purple']};")
        layout.addWidget(title_label)

        # Description
        desc_text = QTextEdit()
        desc_text.setReadOnly(True)
        desc_text.setHtml("""
        <div style="text-align: center; margin: 20px;">
            <p>A powerful window management tool for KDE Plasma on Wayland that allows you 
            to quickly switch between applications, toggle window states, and create 
            shortcuts for your most-used programs.</p>

            <p><b>Features:</b></p>
            <ul style="text-align: left;">
                <li>Application Toggling</li>
                <li>Smart Window Management</li>
                <li>Global Shortcuts</li>
                <li>GUI Interface</li>
            </ul>

            <p>For more information, visit:<br>
            <a href="https://github.com/eraxe/kayland">https://github.com/eraxe/kayland</a></p>

            <p style="margin-top: 30px;">Made with ❤️ for KDE Plasma users</p>
        </div>
        """)
        layout.addWidget(desc_text)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

        # Set dialog size
        self.resize(500, 400)