#!/usr/bin/env python3
# gui_app.py - Main GUI application for Kayland

import os
import sys
import logging
import subprocess
import time
from typing import Dict, List, Any, Optional, Tuple

from PySide6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QSplitter, QStatusBar,
    QMenu, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QStackedWidget, QToolButton
)
from PySide6.QtCore import Qt, QSize, Signal, Slot, QTimer
from PySide6.QtGui import QIcon, QAction, QKeySequence, QGuiApplication

from gui_widgets import (
    AppListItem, LogWidget, AppDetailWidget, ServiceStatusWidget,
    StatusBarWithProgress, CopyButton, KeySequenceEdit
)
from gui_dialogs import (
    ConfirmDialog, AppFormDialog, DesktopFileDialog, ShortcutDialog,
    SettingsDialog, AboutDialog
)
from gui_utils import apply_synthwave_theme, SYNTHWAVE_COLORS

logger = logging.getLogger("kayland.gui.app")


class KaylandGUI(QMainWindow):
    """Main window for Kayland GUI"""

    def __init__(self, window_manager, app_manager, settings):
        super().__init__()  # Use system title bar

        self.window_manager = window_manager
        self.app_manager = app_manager
        self.settings = settings

        self.selected_app_id = None
        self.selected_shortcut_id = None

        # Set window title
        self.setWindowTitle("Kayland - KDE Wayland Window Manager")

        # Set up UI
        self.setup_ui()

        # Apply synthwave theme
        apply_synthwave_theme(QApplication.instance())

        # Initial data loading
        self.refresh_app_list()
        self.refresh_shortcut_list()

        # Log startup
        self.add_log_entry("Kayland GUI started successfully", "info", log_to_ui=False)

        # Set window properties
        self.resize(1035, 748)  # 15% larger than original 900x650

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

    def setup_ui(self):
        """Set up the main window UI"""
        # Create central widget
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Set window icon
        icon_path = self.get_asset_path("kayland.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Create tab widget
        tabs = QTabWidget()

        # Apps tab
        apps_tab = QWidget()
        apps_layout = QVBoxLayout(apps_tab)

        # Create horizontal split layout
        app_splitter = QSplitter(Qt.Horizontal)

        # Left panel - app list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)

        # App list header
        app_header_layout = QHBoxLayout()
        app_header = QLabel("Applications")
        app_header.setProperty("heading", True)
        app_header_layout.addWidget(app_header)

        # Add button
        add_button = QPushButton("+NEW")
        add_button.setToolTip("Add Application")
        add_button.clicked.connect(self.show_add_menu)
        app_header_layout.addWidget(add_button)

        left_layout.addLayout(app_header_layout)

        # App list
        self.app_list = QListWidget()
        self.app_list.setSelectionMode(QListWidget.SingleSelection)
        self.app_list.itemSelectionChanged.connect(self.on_app_selected)
        self.app_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.app_list.customContextMenuRequested.connect(self.show_app_context_menu)
        left_layout.addWidget(self.app_list)

        # App buttons
        app_buttons_layout = QHBoxLayout()

        edit_app_button = QPushButton("Edit")
        edit_app_button.clicked.connect(self.edit_app)
        app_buttons_layout.addWidget(edit_app_button)

        copy_app_button = QPushButton("Copy")
        copy_app_button.clicked.connect(self.copy_app)
        app_buttons_layout.addWidget(copy_app_button)

        launch_app_button = QPushButton("Launch")
        launch_app_button.clicked.connect(self.launch_app)
        app_buttons_layout.addWidget(launch_app_button)

        # Delete button
        delete_app_button = QPushButton("Delete")
        delete_app_button.setStyleSheet(f"background-color: #e464ff; color: #150a2d;")
        delete_app_button.clicked.connect(self.delete_app)
        app_buttons_layout.addWidget(delete_app_button)

        left_layout.addLayout(app_buttons_layout)

        # Right panel - details and logs
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)

        # App details header with copy button
        details_header_layout = QHBoxLayout()
        details_header = QLabel("Application Details")
        details_header.setProperty("heading", True)
        details_header_layout.addWidget(details_header)

        details_copy_btn = QToolButton()
        details_copy_btn.setText("Copy ▼")
        details_copy_btn.setPopupMode(QToolButton.InstantPopup)
        details_copy_menu = QMenu(details_copy_btn)
        details_copy_btn.setMenu(details_copy_menu)

        # Add copy actions to details menu
        copy_launch_action = QAction("Copy 'kayland launch' Command", self)
        copy_launch_action.triggered.connect(lambda: self.copy_app_attribute("launch_command"))
        details_copy_menu.addAction(copy_launch_action)

        copy_name_action = QAction("Copy Name", self)
        copy_name_action.triggered.connect(lambda: self.copy_app_attribute("name"))
        details_copy_menu.addAction(copy_name_action)

        copy_cmd_action = QAction("Copy Command", self)
        copy_cmd_action.triggered.connect(lambda: self.copy_app_attribute("command"))
        details_copy_menu.addAction(copy_cmd_action)

        copy_class_action = QAction("Copy Class Pattern", self)
        copy_class_action.triggered.connect(lambda: self.copy_app_attribute("class_pattern"))
        details_copy_menu.addAction(copy_class_action)

        copy_aliases_action = QAction("Copy Aliases", self)
        copy_aliases_action.triggered.connect(lambda: self.copy_app_attribute("aliases"))
        details_copy_menu.addAction(copy_aliases_action)

        copy_desktop_action = QAction("Copy Desktop File Path", self)
        copy_desktop_action.triggered.connect(lambda: self.copy_app_attribute("desktop_file"))
        details_copy_menu.addAction(copy_desktop_action)

        copy_id_action = QAction("Copy ID", self)
        copy_id_action.triggered.connect(lambda: self.copy_app_attribute("id"))
        details_copy_menu.addAction(copy_id_action)

        copy_script_action = QAction("Copy Script Path", self)
        copy_script_action.triggered.connect(lambda: self.copy_app_attribute("script_path"))
        details_copy_menu.addAction(copy_script_action)

        details_header_layout.addWidget(details_copy_btn)
        right_layout.addLayout(details_header_layout)

        # Vertical splitter for details and logs
        details_log_splitter = QSplitter(Qt.Vertical)

        # App details
        self.app_details = AppDetailWidget()
        details_log_splitter.addWidget(self.app_details)

        # Logs
        self.log_display = LogWidget()
        details_log_splitter.addWidget(self.log_display)

        # Set initial sizes (60% details, 40% logs)
        details_log_splitter.setSizes([300, 200])

        right_layout.addWidget(details_log_splitter)

        # Add panels to splitter
        app_splitter.addWidget(left_panel)
        app_splitter.addWidget(right_panel)

        # Set splitter sizes (30% left, 70% right)
        app_splitter.setSizes([270, 630])

        apps_layout.addWidget(app_splitter)

        # Shortcuts tab
        shortcuts_tab = QWidget()
        shortcuts_layout = QVBoxLayout(shortcuts_tab)

        # Shortcuts header
        shortcuts_header = QLabel("Keyboard Shortcuts")
        shortcuts_header.setProperty("heading", True)
        shortcuts_layout.addWidget(shortcuts_header)

        # Shortcuts table
        self.shortcut_table = QTableWidget()
        self.shortcut_table.setColumnCount(3)
        self.shortcut_table.setHorizontalHeaderLabels(["App", "Key", "Description"])
        self.shortcut_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.shortcut_table.setSelectionMode(QTableWidget.SingleSelection)
        self.shortcut_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.shortcut_table.verticalHeader().setVisible(False)
        self.shortcut_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.shortcut_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.shortcut_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.shortcut_table.itemSelectionChanged.connect(self.on_shortcut_selected)
        self.shortcut_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.shortcut_table.customContextMenuRequested.connect(self.show_shortcut_context_menu)

        shortcuts_layout.addWidget(self.shortcut_table)

        # Shortcut buttons
        shortcut_buttons_layout = QHBoxLayout()

        add_shortcut_button = QPushButton("Add Shortcut")
        add_shortcut_button.clicked.connect(self.add_shortcut)
        shortcut_buttons_layout.addWidget(add_shortcut_button)

        edit_shortcut_button = QPushButton("Edit Shortcut")
        edit_shortcut_button.clicked.connect(self.edit_shortcut)
        shortcut_buttons_layout.addWidget(edit_shortcut_button)

        remove_shortcut_button = QPushButton("Remove Shortcut")
        remove_shortcut_button.clicked.connect(self.remove_shortcut)
        shortcut_buttons_layout.addWidget(remove_shortcut_button)

        shortcuts_layout.addLayout(shortcut_buttons_layout)

        # Service tab
        service_tab = QWidget()
        service_layout = QVBoxLayout(service_tab)

        # Service status header
        service_header = QLabel("Kayland Service Management")
        service_header.setProperty("heading", True)
        service_layout.addWidget(service_header)

        # Service status widget
        self.service_status = ServiceStatusWidget(self)
        service_layout.addWidget(self.service_status)

        # Settings tab
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)

        # Settings header
        settings_header = QLabel("Kayland Settings")
        settings_header.setProperty("heading", True)
        settings_layout.addWidget(settings_header)

        # Settings buttons
        settings_buttons_layout = QHBoxLayout()

        edit_settings_button = QPushButton("Edit Settings")
        edit_settings_button.clicked.connect(self.edit_settings)
        settings_buttons_layout.addWidget(edit_settings_button)

        about_button = QPushButton("About Kayland")
        about_button.clicked.connect(self.show_about)
        settings_buttons_layout.addWidget(about_button)

        settings_layout.addLayout(settings_buttons_layout)

        # Add tabs
        tabs.addTab(apps_tab, "Applications")
        tabs.addTab(shortcuts_tab, "Shortcuts")
        tabs.addTab(service_tab, "Service")
        tabs.addTab(settings_tab, "Settings")

        main_layout.addWidget(tabs)

        # Set central widget
        self.setCentralWidget(central_widget)

        # Create status bar
        self.status_bar = StatusBarWithProgress(self)
        self.setStatusBar(self.status_bar)

        # Create actions and menu
        self.create_actions()
        self.create_menus()

        # Store references to important widgets
        self.tabs = tabs

    def create_actions(self):
        """Create the application actions"""
        # File menu actions
        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcut(QKeySequence.Quit)
        self.exit_action.triggered.connect(self.close)

        # App menu actions
        self.add_app_action = QAction("Add Application", self)
        self.add_app_action.setShortcut(QKeySequence("Ctrl+N"))
        self.add_app_action.triggered.connect(self.add_app)

        self.add_desktop_action = QAction("Add from Desktop File", self)
        self.add_desktop_action.triggered.connect(self.add_from_desktop)

        self.edit_app_action = QAction("Edit Application", self)
        self.edit_app_action.setShortcut(QKeySequence("Ctrl+E"))
        self.edit_app_action.triggered.connect(self.edit_app)

        self.copy_app_action = QAction("Copy Application", self)
        self.copy_app_action.setShortcut(QKeySequence("Ctrl+D"))
        self.copy_app_action.triggered.connect(self.copy_app)

        self.launch_app_action = QAction("Launch Application", self)
        self.launch_app_action.setShortcut(QKeySequence("Ctrl+L"))
        self.launch_app_action.triggered.connect(self.launch_app)

        self.generate_script_action = QAction("Generate App Script", self)
        self.generate_script_action.triggered.connect(self.generate_app_script)

        self.refresh_action = QAction("Refresh", self)
        self.refresh_action.setShortcut(QKeySequence("F5"))
        self.refresh_action.triggered.connect(self.refresh_all)

        # Shortcut menu actions
        self.add_shortcut_action = QAction("Add Shortcut", self)
        self.add_shortcut_action.setShortcut(QKeySequence("Ctrl+Shift+N"))
        self.add_shortcut_action.triggered.connect(self.add_shortcut)

        self.edit_shortcut_action = QAction("Edit Shortcut", self)
        self.edit_shortcut_action.triggered.connect(self.edit_shortcut)

        self.remove_shortcut_action = QAction("Remove Shortcut", self)
        self.remove_shortcut_action.triggered.connect(self.remove_shortcut)

        # Service menu actions
        self.service_status_action = QAction("Check Service Status", self)
        self.service_status_action.triggered.connect(self.check_service_status)

        self.service_start_action = QAction("Start Service", self)
        self.service_start_action.triggered.connect(lambda: self.service_status.manage_service("start"))

        self.service_stop_action = QAction("Stop Service", self)
        self.service_stop_action.triggered.connect(lambda: self.service_status.manage_service("stop"))

        self.service_restart_action = QAction("Restart Service", self)
        self.service_restart_action.triggered.connect(lambda: self.service_status.manage_service("restart"))

        # Settings menu actions
        self.edit_settings_action = QAction("Edit Settings", self)
        self.edit_settings_action.triggered.connect(self.edit_settings)

        self.about_action = QAction("About Kayland", self)
        self.about_action.triggered.connect(self.show_about)

    def create_menus(self):
        """Create the application menus"""
        # Main menu bar
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet(f"""
            QMenuBar {{
                background-color: {SYNTHWAVE_COLORS["dark_bg"]};
                color: {SYNTHWAVE_COLORS["accent2"]};
                font-size: 12pt;
                min-height: 28px;
            }}
        """)

        # File menu
        file_menu = menu_bar.addMenu("File")
        file_menu.addAction(self.exit_action)

        # Apps menu
        apps_menu = menu_bar.addMenu("Apps")
        apps_menu.addAction(self.add_app_action)
        apps_menu.addAction(self.add_desktop_action)
        apps_menu.addSeparator()
        apps_menu.addAction(self.edit_app_action)
        apps_menu.addAction(self.copy_app_action)
        apps_menu.addAction(self.launch_app_action)
        apps_menu.addAction(self.generate_script_action)
        apps_menu.addSeparator()
        apps_menu.addAction(self.refresh_action)

        # Shortcuts menu
        shortcuts_menu = menu_bar.addMenu("Shortcuts")
        shortcuts_menu.addAction(self.add_shortcut_action)
        shortcuts_menu.addAction(self.edit_shortcut_action)
        shortcuts_menu.addAction(self.remove_shortcut_action)

        # Service menu
        service_menu = menu_bar.addMenu("Service")
        service_menu.addAction(self.service_status_action)
        service_menu.addSeparator()
        service_menu.addAction(self.service_start_action)
        service_menu.addAction(self.service_stop_action)
        service_menu.addAction(self.service_restart_action)

        # Settings menu
        settings_menu = menu_bar.addMenu("Settings")
        settings_menu.addAction(self.edit_settings_action)
        settings_menu.addSeparator()
        settings_menu.addAction(self.about_action)

    def show_file_menu(self):
        """Show the file menu"""
        file_menu = QMenu(self)
        file_menu.addAction(self.exit_action)

        sender = self.sender()
        if sender:
            pos = sender.mapToGlobal(sender.rect().bottomLeft())
            file_menu.exec(pos)

    def show_add_menu(self):
        """Show a popup menu for add options"""
        menu = QMenu(self)
        menu.addAction(self.add_app_action)
        menu.addAction(self.add_desktop_action)

        # Get position relative to add button
        sender_widget = self.sender()
        if sender_widget:
            menu.exec(sender_widget.mapToGlobal(sender_widget.rect().bottomLeft()))

    def show_app_context_menu(self, pos):
        """Show context menu for application list items"""
        global_pos = self.app_list.mapToGlobal(pos)
        selected_items = self.app_list.selectedItems()

        if not selected_items:
            return

        item = selected_items[0]
        app_data = item.data(Qt.UserRole)

        if not app_data:
            return

        # Create menu
        menu = QMenu(self)

        # Add actions
        copy_launch_action = QAction("Copy 'kayland launch' Command", self)
        copy_launch_action.triggered.connect(lambda: self.copy_app_attribute("launch_command", app_data))
        menu.addAction(copy_launch_action)

        copy_name_action = QAction("Copy Name", self)
        copy_name_action.triggered.connect(lambda: self.copy_app_attribute("name", app_data))
        menu.addAction(copy_name_action)

        copy_cmd_action = QAction("Copy Command", self)
        copy_cmd_action.triggered.connect(lambda: self.copy_app_attribute("command", app_data))
        menu.addAction(copy_cmd_action)

        copy_class_action = QAction("Copy Class Pattern", self)
        copy_class_action.triggered.connect(lambda: self.copy_app_attribute("class_pattern", app_data))
        menu.addAction(copy_class_action)

        aliases = app_data.get("aliases", [])
        if aliases:
            copy_aliases_action = QAction("Copy Aliases", self)
            copy_aliases_action.triggered.connect(lambda: self.copy_app_attribute("aliases", app_data))
            menu.addAction(copy_aliases_action)

        desktop_file = app_data.get("desktop_file")
        if desktop_file:
            copy_desktop_action = QAction("Copy Desktop File Path", self)
            copy_desktop_action.triggered.connect(lambda: self.copy_app_attribute("desktop_file", app_data))
            menu.addAction(copy_desktop_action)

        copy_id_action = QAction("Copy ID", self)
        copy_id_action.triggered.connect(lambda: self.copy_app_attribute("id", app_data))
        menu.addAction(copy_id_action)

        script_path = app_data.get("script_path")
        if script_path:
            copy_script_action = QAction("Copy Script Path", self)
            copy_script_action.triggered.connect(lambda: self.copy_app_attribute("script_path", app_data))
            menu.addAction(copy_script_action)

        menu.addSeparator()

        # Add regular actions
        edit_action = QAction("Edit", self)
        edit_action.triggered.connect(self.edit_app)
        menu.addAction(edit_action)

        copy_action = QAction("Duplicate", self)
        copy_action.triggered.connect(self.copy_app)
        menu.addAction(copy_action)

        launch_action = QAction("Launch", self)
        launch_action.triggered.connect(self.launch_app)
        menu.addAction(launch_action)

        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self.delete_app)
        menu.addAction(delete_action)

        # Show menu
        menu.exec(global_pos)

    def show_shortcut_context_menu(self, pos):
        """Show context menu for shortcut table items"""
        global_pos = self.shortcut_table.mapToGlobal(pos)
        selected_indexes = self.shortcut_table.selectedIndexes()

        if not selected_indexes:
            return

        row = selected_indexes[0].row()
        app_item = self.shortcut_table.item(row, 0)
        key_item = self.shortcut_table.item(row, 1)
        desc_item = self.shortcut_table.item(row, 2)

        if not app_item or not key_item:
            return

        shortcut_id = app_item.data(Qt.UserRole)
        app_name = app_item.text()
        key = key_item.text()
        description = desc_item.text() if desc_item else ""

        # Create menu
        menu = QMenu(self)

        # Add copy actions
        copy_key_action = QAction(f"Copy Key: {key}", self)
        copy_key_action.triggered.connect(lambda: self.copy_to_clipboard(key))
        menu.addAction(copy_key_action)

        copy_app_action = QAction(f"Copy App: {app_name}", self)
        copy_app_action.triggered.connect(lambda: self.copy_to_clipboard(app_name))
        menu.addAction(copy_app_action)

        if description:
            copy_desc_action = QAction(f"Copy Description", self)
            copy_desc_action.triggered.connect(lambda: self.copy_to_clipboard(description))
            menu.addAction(copy_desc_action)

        menu.addSeparator()

        # Add regular actions
        edit_action = QAction("Edit Shortcut", self)
        edit_action.triggered.connect(self.edit_shortcut)
        menu.addAction(edit_action)

        remove_action = QAction("Remove Shortcut", self)
        remove_action.triggered.connect(self.remove_shortcut)
        menu.addAction(remove_action)

        # Show menu
        menu.exec(global_pos)

    def copy_app_attribute(self, attribute, app_data=None):
        """Copy an app attribute to clipboard"""
        if not app_data:
            # Get currently selected app
            selected_items = self.app_list.selectedItems()
            if not selected_items:
                self.show_status_message("No application selected", 3000)
                return

            item = selected_items[0]
            app_data = item.data(Qt.UserRole)

        if not app_data:
            self.show_status_message("No application data available", 3000)
            return

        # Handle special case for launch command - use alias if available, otherwise name
        if attribute == "launch_command":
            aliases = app_data.get("aliases", [])
            if aliases:
                # Use the first alias if available
                launch_cmd = f"kayland launch {aliases[0]}"
            else:
                launch_cmd = f"kayland launch {app_data['name']}"
            self.copy_to_clipboard(launch_cmd)
            self.show_status_message(f"Copied launch command to clipboard", 3000)
            return

        # Handle special case for aliases
        if attribute == "aliases":
            aliases = app_data.get("aliases", [])
            aliases_text = ", ".join(aliases) if aliases else "None"
            self.copy_to_clipboard(aliases_text)
            self.show_status_message(f"Copied aliases to clipboard", 3000)
            return

        # Regular attribute
        value = app_data.get(attribute, "")
        if value:
            self.copy_to_clipboard(value)
            self.show_status_message(f"Copied {attribute} to clipboard", 3000)
        else:
            self.show_status_message(f"No {attribute} available", 3000)

    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(text)

    def refresh_app_list(self):
        """Refresh the application list"""
        try:
            # Get apps from manager
            apps = self.app_manager.get_all_apps()

            # Log debug info
            self.add_log_entry(f"Refreshing app list, found {len(apps)} apps", "info", log_to_ui=False)

            # Clear current list
            self.app_list.clear()

            if not apps:
                # Add placeholder item
                placeholder = QListWidgetItem("No applications defined yet")
                placeholder.setFlags(placeholder.flags() & ~Qt.ItemIsSelectable)
                self.app_list.addItem(placeholder)
                return

            # Add apps to list
            for app in apps:
                item = AppListItem(app)
                self.app_list.addItem(item)

                # If this was previously selected, select it again
                if self.selected_app_id and app.get("id") == self.selected_app_id:
                    self.app_list.setCurrentItem(item)

            # Update details if we had a selection
            if self.selected_app_id:
                app = self.app_manager.get_app_by_id(self.selected_app_id)
                if app:
                    self.app_details.update_details(app)
                    # Also update shortcuts info
                    shortcuts = self.app_manager.get_shortcuts()
                    self.app_details.update_shortcuts(shortcuts, self.selected_app_id)
                else:
                    self.selected_app_id = None
                    self.app_details.update_details(None)

        except Exception as e:
            error_msg = f"Failed to refresh app list: {str(e)}"
            logger.error(error_msg)
            self.add_log_entry(error_msg, "error")
            self.show_status_message(error_msg, 5000)

    def refresh_shortcut_list(self):
        """Refresh the shortcut list table"""
        try:
            # Clear existing rows
            self.shortcut_table.setRowCount(0)

            # Get shortcuts and apps
            shortcuts = self.app_manager.get_shortcuts()
            all_apps = {app["id"]: app for app in self.app_manager.get_all_apps()}

            if not shortcuts:
                # Add placeholder row
                self.shortcut_table.insertRow(0)
                placeholder = QTableWidgetItem("No shortcuts defined")
                placeholder.setFlags(placeholder.flags() & ~Qt.ItemIsSelectable)
                self.shortcut_table.setItem(0, 0, placeholder)
                self.shortcut_table.setItem(0, 1, QTableWidgetItem(""))
                self.shortcut_table.setItem(0, 2, QTableWidgetItem(""))
                return

            # Add shortcuts to table
            for i, shortcut in enumerate(shortcuts):
                self.shortcut_table.insertRow(i)

                app_id = shortcut.get("app_id", "")
                app_name = "Unknown"

                # Get app name if available
                app = all_apps.get(app_id)
                if app:
                    app_name = app["name"]

                # Add to table
                app_item = QTableWidgetItem(app_name)
                key_item = QTableWidgetItem(shortcut.get("key", ""))
                desc_item = QTableWidgetItem(shortcut.get("description", ""))

                # Store shortcut ID in the app item
                app_item.setData(Qt.UserRole, shortcut.get("id", ""))

                self.shortcut_table.setItem(i, 0, app_item)
                self.shortcut_table.setItem(i, 1, key_item)
                self.shortcut_table.setItem(i, 2, desc_item)

                # If this was previously selected, select it again
                if self.selected_shortcut_id and shortcut.get("id") == self.selected_shortcut_id:
                    self.shortcut_table.selectRow(i)

        except Exception as e:
            error_msg = f"Failed to refresh shortcut list: {str(e)}"
            logger.error(error_msg)
            self.add_log_entry(error_msg, "error")
            self.show_status_message(error_msg, 5000)

    def add_log_entry(self, message: str, level: str = "info", log_to_ui: bool = True) -> None:
        """Add a log entry to the log display"""
        try:
            # Always log to system logger
            if level == "info":
                logger.info(message)
            elif level == "error":
                logger.error(message)
            elif level == "warning":
                logger.warning(message)
            else:
                logger.debug(message)

            # Only add to UI if explicitly requested
            if log_to_ui:
                self.log_display.add_entry(message, level)
        except Exception as e:
            # If we can't update the log UI, log to system logger
            logger.error(f"Failed to update log UI: {str(e)}")
            # Print to console as fallback
            print(f"LOG ERROR: {str(e)}")
            print(f"[{level.upper()}] {message}")

    def show_status_message(self, message: str, timeout: int = 3000) -> None:
        """Show a message in the status bar"""
        self.status_bar.showMessage(message, timeout)

    def on_app_selected(self):
        """Handle app selection in the list"""
        try:
            selected_items = self.app_list.selectedItems()

            if selected_items:
                item = selected_items[0]
                app_data = item.data(Qt.UserRole)

                if app_data:
                    self.selected_app_id = app_data.get("id")
                    self.app_details.update_details(app_data)

                    # Update shortcuts info
                    shortcuts = self.app_manager.get_shortcuts()
                    self.app_details.update_shortcuts(shortcuts, self.selected_app_id)

                    # Don't log selection to UI
                    self.add_log_entry(f"Selected application: {app_data.get('name')}", "info", log_to_ui=False)
            else:
                self.selected_app_id = None
                self.app_details.update_details(None)

        except Exception as e:
            error_msg = f"Failed to display app details: {str(e)}"
            logger.error(error_msg)
            self.add_log_entry(error_msg, "error")

    def on_shortcut_selected(self):
        """Handle shortcut selection in the table"""
        try:
            selected_items = self.shortcut_table.selectedItems()

            if selected_items:
                # Get selected row
                row = selected_items[0].row()

                # Get shortcut ID from the app item (column 0)
                app_item = self.shortcut_table.item(row, 0)
                if app_item:
                    shortcut_id = app_item.data(Qt.UserRole)
                    self.selected_shortcut_id = shortcut_id

                    # Get shortcut info for logging
                    shortcuts = self.app_manager.get_shortcuts()
                    shortcut = next((s for s in shortcuts if s.get("id") == shortcut_id), None)

                    if shortcut:
                        # Don't log selection to UI
                        self.add_log_entry(f"Selected shortcut: {shortcut.get('key', '')}", "info", log_to_ui=False)
            else:
                self.selected_shortcut_id = None

        except Exception as e:
            self.add_log_entry(f"Error selecting shortcut: {str(e)}", "error")
            self.selected_shortcut_id = None

    def add_app(self):
        """Open dialog to add a new application"""
        try:
            dialog = AppFormDialog(self.app_manager, parent=self)

            if dialog.exec():
                self.refresh_app_list()  # Refresh on success
        except Exception as e:
            self.add_log_entry(f"Error adding application: {str(e)}", "error")

    def add_from_desktop(self):
        """Open dialog to add an application from a desktop file"""
        try:
            # First open the desktop file browser
            desktop_dir = self.settings.get("desktop_file_dir", "~/.local/share/applications")
            dialog = DesktopFileDialog(self, desktop_dir)

            if dialog.exec():
                # If a desktop file was selected, open the app form with the data
                if dialog.selected_data:
                    app_dialog = AppFormDialog(
                        self.app_manager,
                        desktop_file=dialog.selected_data,
                        parent=self
                    )

                    if app_dialog.exec():
                        self.refresh_app_list()  # Refresh on success
        except Exception as e:
            self.add_log_entry(f"Error adding from desktop file: {str(e)}", "error")

    def edit_app(self):
        """Edit the selected application"""
        if not self.selected_app_id:
            self.show_status_message("No application selected", 3000)
            return

        try:
            dialog = AppFormDialog(self.app_manager, self.selected_app_id, parent=self)

            if dialog.exec():
                self.refresh_app_list()  # Refresh on success
                self.refresh_shortcut_list()  # Shortcuts might have changed
        except Exception as e:
            self.add_log_entry(f"Error editing application: {str(e)}", "error")

    def delete_app(self):
        """Delete the selected application"""
        if not self.selected_app_id:
            self.show_status_message("No application selected", 3000)
            return

        try:
            # Get the app data
            app = self.app_manager.get_app_by_id(self.selected_app_id)
            if not app:
                return

            # Confirm deletion
            confirm_delete = self.settings.get("confirm_delete", "True") == "True"
            if confirm_delete:
                confirm = QMessageBox.question(
                    self, "Confirm Delete",
                    f"Are you sure you want to delete {app['name']}?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )

                if confirm != QMessageBox.Yes:
                    return

            # Delete any associated shortcuts first
            shortcuts = self.app_manager.get_shortcuts()
            for shortcut in shortcuts:
                if shortcut.get("app_id") == self.selected_app_id:
                    self.app_manager.remove_shortcut(shortcut["id"])

            # Delete the app
            self.app_manager.delete_app(self.selected_app_id)
            message = f"Deleted app: {app['name']}"
            self.add_log_entry(message, "success")
            self.show_status_message(message)

            # Clear selection and refresh
            self.selected_app_id = None
            self.refresh_app_list()
            self.refresh_shortcut_list()

        except Exception as e:
            self.add_log_entry(f"Error deleting application: {str(e)}", "error")

    def copy_app(self):
        """Copy the selected application"""
        if not self.selected_app_id:
            self.show_status_message("No application selected", 3000)
            return

        try:
            # Get the app data
            app = self.app_manager.get_app_by_id(self.selected_app_id)
            if app:
                # Create a copy
                new_app = self.app_manager.copy_app(self.selected_app_id)
                if new_app:
                    message = f"Copied app: {new_app['name']}"
                    self.add_log_entry(message, "success")
                    self.show_status_message(message)
                    self.refresh_app_list()
        except Exception as e:
            self.add_log_entry(f"Error copying application: {str(e)}", "error")

    def launch_app(self):
        """Launch the selected application"""
        if not self.selected_app_id:
            self.show_status_message("No application selected", 3000)
            return

        try:
            app = self.app_manager.get_app_by_id(self.selected_app_id)
            if app:
                self.add_log_entry(f"Launching application: {app['name']}", "info")
                result, success = self.window_manager.toggle_window(
                    app["class_pattern"], app["command"]
                )
                log_level = "success" if success else "error"
                self.add_log_entry(result, log_level)
                self.show_status_message(
                    f"Toggle result: {'Success' if success else 'Failed'}",
                    5000 if not success else 3000
                )
        except Exception as e:
            error_msg = f"Failed to launch application: {str(e)}"
            logger.error(error_msg)
            self.add_log_entry(error_msg, "error")
            self.show_status_message(error_msg, 5000)

    def generate_app_script(self):
        """Generate a shell script for the selected application"""
        if not self.selected_app_id:
            self.show_status_message("No application selected", 3000)
            return

        try:
            app = self.app_manager.get_app_by_id(self.selected_app_id)
            if app:
                script_path = self.app_manager.generate_app_script(self.selected_app_id)
                message = f"Generated script for {app['name']}: {script_path}"
                self.add_log_entry(message, "success")
                self.show_status_message(f"Script generated: {os.path.basename(script_path)}")

                # Copy path to clipboard
                clipboard = QGuiApplication.clipboard()
                clipboard.setText(script_path)
                self.show_status_message(f"Script path copied to clipboard", 3000)

                # Refresh app details to show script path
                self.refresh_app_list()
        except Exception as e:
            error_msg = f"Failed to generate script: {str(e)}"
            logger.error(error_msg)
            self.add_log_entry(error_msg, "error")
            self.show_status_message(error_msg, 5000)

    def add_shortcut(self):
        """Open dialog to add a new shortcut"""
        try:
            # Check if there are any apps defined first
            all_apps = self.app_manager.get_all_apps()
            if not all_apps:
                self.show_status_message("Please add at least one application before creating shortcuts", 5000)
                self.add_log_entry("Cannot add shortcut: No applications defined", "warning")
                return

            dialog = ShortcutDialog(self.app_manager, parent=self)

            if dialog.exec():
                self.refresh_shortcut_list()  # Refresh on success

                # Also refresh app details if current app has a new shortcut
                if self.selected_app_id:
                    shortcuts = self.app_manager.get_shortcuts()
                    self.app_details.update_shortcuts(shortcuts, self.selected_app_id)
        except Exception as e:
            self.add_log_entry(f"Error adding shortcut: {str(e)}", "error")

    def edit_shortcut(self):
        """Edit the selected shortcut"""
        if not self.selected_shortcut_id:
            self.show_status_message("No shortcut selected", 3000)
            return

        try:
            dialog = ShortcutDialog(self.app_manager, self.selected_shortcut_id, parent=self)

            if dialog.exec():
                self.refresh_shortcut_list()  # Refresh on success

                # Also refresh app details if current app's shortcut was edited
                if self.selected_app_id:
                    shortcuts = self.app_manager.get_shortcuts()
                    self.app_details.update_shortcuts(shortcuts, self.selected_app_id)
        except Exception as e:
            self.add_log_entry(f"Error editing shortcut: {str(e)}", "error")

    def remove_shortcut(self):
        """Remove the selected shortcut"""
        if not self.selected_shortcut_id:
            self.show_status_message("No shortcut selected", 3000)
            return

        # Check if confirm deletions is enabled
        confirm_deletions = self.settings.get("confirm_delete", "True") == "True"

        try:
            shortcuts = self.app_manager.get_shortcuts()
            shortcut = next((s for s in shortcuts if s.get("id") == self.selected_shortcut_id), None)

            if not shortcut:
                return

            # Confirm deletion if needed
            if confirm_deletions:
                confirm = QMessageBox.question(
                    self, "Confirm Delete",
                    f"Are you sure you want to delete the shortcut '{shortcut.get('key', '')}'?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )

                if confirm != QMessageBox.Yes:
                    return

            # Delete shortcut
            self.app_manager.remove_shortcut(self.selected_shortcut_id)
            message = f"Deleted shortcut: {shortcut.get('key', '')}"
            self.add_log_entry(message, "success")
            self.show_status_message(message)

            # Refresh shortcuts
            self.selected_shortcut_id = None
            self.refresh_shortcut_list()

            # Also refresh app details if current app's shortcut was removed
            if self.selected_app_id:
                shortcuts = self.app_manager.get_shortcuts()
                self.app_details.update_shortcuts(shortcuts, self.selected_app_id)

        except Exception as e:
            self.add_log_entry(f"Error removing shortcut: {str(e)}", "error")

    def edit_settings(self):
        """Open dialog to edit settings"""
        try:
            dialog = SettingsDialog(self.settings, parent=self)

            if dialog.exec():
                # Settings were changed
                self.add_log_entry("Settings updated", "success")
        except Exception as e:
            self.add_log_entry(f"Error editing settings: {str(e)}", "error")

    def show_about(self):
        """Show the about dialog"""
        try:
            dialog = AboutDialog(parent=self)
            dialog.exec()
        except Exception as e:
            self.add_log_entry(f"Error showing about dialog: {str(e)}", "error")

    def check_service_status(self):
        """Check the Kayland service status"""
        try:
            self.service_status.check_service_status()
        except Exception as e:
            self.add_log_entry(f"Error checking service status: {str(e)}", "error")

    def refresh_all(self):
        """Refresh all data"""
        self.add_log_entry("Refreshing data", "info")
        self.refresh_app_list()
        self.refresh_shortcut_list()
        self.check_service_status()

    def closeEvent(self, event):
        """Handle window close event"""
        # Add log entry before closing
        self.add_log_entry("Kayland GUI shutting down", "info", log_to_ui=False)

        # Accept the event to close the window
        event.accept()