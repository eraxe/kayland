#!/usr/bin/env python3
# gui_widgets.py - Custom widgets for Kayland GUI

import os
import logging
from typing import Dict, List, Any, Optional, Callable

from PySide6.QtCore import Qt, QSize, Signal, Slot, QTimer, QPoint
from PySide6.QtGui import QIcon, QColor, QStandardItemModel, QStandardItem, QAction, QGuiApplication
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QTextBrowser, QSplitter, QTableWidget, QTableWidgetItem,
    QGroupBox, QFormLayout, QLineEdit, QFrame, QMenu, QTextEdit,
    QListView, QAbstractItemView, QStatusBar, QProgressBar, QToolButton, QApplication
)

from gui_utils import SYNTHWAVE_COLORS

logger = logging.getLogger("kayland.gui.widgets")


class CopyButton(QPushButton):
    """Button that copies text to clipboard when clicked"""

    copied = Signal(str)

    def __init__(self, text_to_copy="", parent=None):
        super().__init__(parent)
        self.text_to_copy = text_to_copy
        self.setText("Copy")
        self.setToolTip("Copy to clipboard")
        self.clicked.connect(self.copy_to_clipboard)

    def set_text(self, text):
        """Set the text to copy"""
        self.text_to_copy = text

    def copy_to_clipboard(self):
        """Copy the text to the clipboard"""
        if self.text_to_copy:
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(self.text_to_copy)
            self.copied.emit(self.text_to_copy)

            # Show temporary feedback
            self.setText("Copied!")
            self.setEnabled(False)

            # Reset after a delay
            QTimer.singleShot(1500, self.reset_button)

    def reset_button(self):
        """Reset the button text and state"""
        self.setText("Copy")
        self.setEnabled(True)


class TitleBarWidget(QWidget):
    """Custom title bar widget with window controls"""

    closeClicked = Signal()
    minimizeClicked = Signal()
    maximizeClicked = Signal()
    pinClicked = Signal()

    def __init__(self, title="Kayland", parent=None):
        super().__init__(parent)
        self.parent = parent
        self.title_text = title
        self.is_pinned = False
        self.dragPosition = None

        # Set up layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)

        # Window controls (left side)
        btn_size = QSize(30, 30)

        self.close_btn = QPushButton()
        self.close_btn.setFixedSize(btn_size)
        self.close_btn.setToolTip("Close")
        self.close_btn.clicked.connect(self.closeClicked.emit)

        self.minimize_btn = QPushButton()
        self.minimize_btn.setFixedSize(btn_size)
        self.minimize_btn.setToolTip("Minimize")
        self.minimize_btn.clicked.connect(self.minimizeClicked.emit)

        self.maximize_btn = QPushButton()
        self.maximize_btn.setFixedSize(btn_size)
        self.maximize_btn.setToolTip("Maximize")
        self.maximize_btn.clicked.connect(self.maximizeClicked.emit)

        # Title label (center)
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 13pt; color: #00fff5;")

        # Pin button (right side)
        self.pin_btn = QPushButton()
        self.pin_btn.setFixedSize(btn_size)
        self.pin_btn.setToolTip("Pin on Top")
        self.pin_btn.clicked.connect(self.toggle_pin)

        # Add widgets to layout
        layout.addWidget(self.close_btn)
        layout.addWidget(self.minimize_btn)
        layout.addWidget(self.maximize_btn)
        layout.addStretch(1)
        layout.addWidget(self.title_label)
        layout.addStretch(1)
        layout.addWidget(self.pin_btn)

        # Set styling
        self.setAutoFillBackground(True)
        self.update_style()

        # Set fixed height for title bar (scaled up by 15%)
        self.setFixedHeight(40)

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

    def update_style(self):
        """Update the styling of the title bar"""
        dark_bg = SYNTHWAVE_COLORS["dark_bg"]
        accent = SYNTHWAVE_COLORS["accent"]
        hover_purple = SYNTHWAVE_COLORS["hover_purple"]
        active_text = SYNTHWAVE_COLORS["active_text"]

        self.setStyleSheet(f"""
            TitleBarWidget {{
                background-color: {dark_bg};
                border-bottom: 1px solid {accent};
            }}

            QPushButton {{
                background-color: transparent;
                border: none;
                font-size: 16px;
            }}

            QPushButton:hover {{
                background-color: {hover_purple};
                color: {active_text};
                border-radius: 15px;
            }}
        """)

        # Try to load icons from assets, fall back to text if not available
        try:
            # Close button
            close_icon_path = self.get_asset_path("close.svg")
            if os.path.exists(close_icon_path):
                self.close_btn.setIcon(QIcon(close_icon_path))
                self.close_btn.setIconSize(QSize(16, 16))
            else:
                self.close_btn.setText("✕")

            # Minimize button
            minimize_icon_path = self.get_asset_path("minimize.svg")
            if os.path.exists(minimize_icon_path):
                self.minimize_btn.setIcon(QIcon(minimize_icon_path))
                self.minimize_btn.setIconSize(QSize(16, 16))
            else:
                self.minimize_btn.setText("_")

            # Maximize button
            maximize_icon_path = self.get_asset_path("maximize.svg")
            if os.path.exists(maximize_icon_path):
                self.maximize_btn.setIcon(QIcon(maximize_icon_path))
                self.maximize_btn.setIconSize(QSize(16, 16))
            else:
                self.maximize_btn.setText("□")

            # Pin button
            pin_icon_path = self.get_asset_path("pin.svg" if self.is_pinned else "unpin.svg")
            if os.path.exists(pin_icon_path):
                self.pin_btn.setIcon(QIcon(pin_icon_path))
                self.pin_btn.setIconSize(QSize(16, 16))
            else:
                self.pin_btn.setText("📌" if self.is_pinned else "📍")
        except Exception as e:
            logger.error(f"Error loading title bar icons: {str(e)}")
            # Fallback to text
            self.close_btn.setText("✕")
            self.minimize_btn.setText("_")
            self.maximize_btn.setText("□")
            self.pin_btn.setText("📌" if self.is_pinned else "📍")

    def toggle_pin(self):
        """Toggle the pin state"""
        self.is_pinned = not self.is_pinned
        self.update_style()
        self.pinClicked.emit()

    def mousePressEvent(self, event):
        """Handle mouse press events for dragging the window"""
        if event.button() == Qt.LeftButton:
            # Store the global click position relative to window top-left corner
            self.dragPosition = event.globalPosition().toPoint() - self.parent.frameGeometry().topLeft()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle mouse move events for dragging the window"""
        if event.buttons() == Qt.LeftButton and self.dragPosition is not None:
            # Calculate new position based on difference between current position and stored offset
            newPos = event.globalPosition().toPoint() - self.dragPosition
            if self.parent:
                self.parent.move(newPos)
            event.accept()

    def mouseReleaseEvent(self, event):
        """Handle mouse release events"""
        self.dragPosition = None
        self.setCursor(Qt.ArrowCursor)
        event.accept()

    def mouseDoubleClickEvent(self, event):
        """Handle double clicks to maximize/restore"""
        if event.button() == Qt.LeftButton:
            self.maximizeClicked.emit()
            event.accept()


class AppListItem(QListWidgetItem):
    """Custom list item for applications"""

    def __init__(self, app_data: Dict[str, Any]):
        self._app_data = app_data

        # Create display text
        name = app_data.get("name", "Unknown")
        aliases = app_data.get("aliases", [])
        alias_text = f" ({', '.join(aliases)})" if aliases else ""
        display_text = f"{name}{alias_text}"

        super().__init__(display_text)

        # Store app data for later retrieval
        self.setData(Qt.UserRole, app_data)

    @property
    def app_data(self) -> Dict[str, Any]:
        """Get the app data"""
        return self._app_data


class LogWidget(QWidget):
    """Widget for displaying logs"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.log_entries = []
        self.max_entries = 100

        layout = QVBoxLayout(self)

        # Title
        title = QLabel("System Logs")
        title.setProperty("heading", True)
        layout.addWidget(title)

        # Log display
        self.log_display = QTextBrowser()
        self.log_display.setReadOnly(True)
        self.log_display.setOpenExternalLinks(False)
        layout.addWidget(self.log_display)

        # Set layout margins
        layout.setContentsMargins(0, 0, 0, 0)

    def add_entry(self, message: str, level: str = "info") -> None:
        """Add a log entry"""
        import time

        try:
            timestamp = time.strftime("%H:%M:%S")

            # HTML color based on level
            color = {
                "info": SYNTHWAVE_COLORS["accent2"],
                "error": "#ff0000",
                "warning": "#ffff00",
                "success": "#00ff00"
            }.get(level, SYNTHWAVE_COLORS["foreground"])

            # Format multi-line messages
            if "\n" in message:
                lines = message.split("\n")
                html = f'<span style="color: #aaaaaa">[{timestamp}]</span> <span style="color: {color}">{lines[0]}</span><br>'

                # Format remaining lines with indentation
                for line in lines[1:]:
                    html += f'<span style="color: {color}">&nbsp;&nbsp;&nbsp;&nbsp;{line}</span><br>'
            else:
                html = f'<span style="color: #aaaaaa">[{timestamp}]</span> <span style="color: {color}">{message}</span><br>'

            # Insert at the beginning (newest first)
            self.log_entries.insert(0, html)

            # Always log to console for debugging
            print(f"[{level.upper()}] {message}")

            # Trim log entries if needed
            if len(self.log_entries) > self.max_entries:
                self.log_entries = self.log_entries[:self.max_entries]

            # Update display
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
            html = "".join(self.log_entries)
            self.log_display.setHtml(html)
        except Exception as e:
            logger.error(f"Error updating log display: {str(e)}")


class AppDetailWidget(QWidget):
    """Widget for displaying application details"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.current_app = None

        layout = QVBoxLayout(self)

        # Title
        self.title_layout = QHBoxLayout()
        self.title = QLabel("Application Details")
        self.title.setProperty("heading", True)
        self.title_layout.addWidget(self.title)

        # Add copy dropdown to the title bar
        self.copy_btn = QToolButton()
        self.copy_btn.setText("Copy ▼")
        self.copy_btn.setPopupMode(QToolButton.InstantPopup)
        self.copy_btn.setVisible(False)  # Hide initially
        self.copy_menu = QMenu(self.copy_btn)
        self.copy_btn.setMenu(self.copy_menu)
        self.title_layout.addWidget(self.copy_btn)

        layout.addLayout(self.title_layout)

        # Details display
        self.detail_display = QTextBrowser()
        self.detail_display.setReadOnly(True)
        self.detail_display.setOpenExternalLinks(False)
        self.detail_display.setContextMenuPolicy(Qt.CustomContextMenu)
        self.detail_display.customContextMenuRequested.connect(self.show_detail_context_menu)
        layout.addWidget(self.detail_display)

        # Set layout margins
        layout.setContentsMargins(0, 0, 0, 0)

    def update_details(self, app: Optional[Dict[str, Any]]) -> None:
        """Update the details display with app information"""
        self.current_app = app
        self.copy_btn.setVisible(bool(app))  # Show copy button only if app exists

        try:
            if app:
                # Update copy menu
                self.update_copy_menu(app)

                # Build HTML content
                html = "<table width='100%'>"

                # Add app properties
                html += self._create_detail_row("Name", app["name"], SYNTHWAVE_COLORS["accent3"])
                html += self._create_detail_row("Class Pattern", app["class_pattern"], SYNTHWAVE_COLORS["accent3"])
                html += self._create_detail_row("Command", app["command"], SYNTHWAVE_COLORS["accent3"])

                # Add aliases if any
                aliases = app.get("aliases", [])
                aliases_text = ", ".join(aliases) if aliases else "None"
                html += self._create_detail_row("Aliases", aliases_text, SYNTHWAVE_COLORS["accent3"])

                # Add desktop file if any
                desktop_file = app.get("desktop_file", "")
                if desktop_file:
                    html += self._create_detail_row("Desktop File", desktop_file, SYNTHWAVE_COLORS["accent3"])

                # Add ID
                html += self._create_detail_row("ID", app["id"], SYNTHWAVE_COLORS["accent3"])

                # Add launch command
                launch_cmd = f"kayland launch {app['name']}"
                html += self._create_detail_row("Launch Command", launch_cmd, SYNTHWAVE_COLORS["accent3"])

                # Add script path if any
                script_path = app.get("script_path", "")
                if script_path:
                    html += self._create_detail_row("Script Path", script_path, SYNTHWAVE_COLORS["accent3"])

                html += "</table>"

                # Check for shortcuts associated with this app
                # Note: This would require access to the shortcuts - we'll need to pass them separately
                # We'll implement this in the main class

                self.detail_display.setHtml(html)
            else:
                self.detail_display.setHtml(
                    "<p>No application selected.</p>"
                    "<p>Select an application from the list or add a new one.</p>"
                )
        except Exception as e:
            logger.error(f"Error updating app details: {str(e)}")
            self.detail_display.setHtml(f"<p>Error displaying details: {str(e)}</p>")

    def update_copy_menu(self, app: Dict[str, Any]) -> None:
        """Update the copy menu items"""
        self.copy_menu.clear()

        # Add copy actions
        launch_action = QAction("Copy 'kayland launch' Command", self)
        launch_action.triggered.connect(lambda: self.copy_attribute("launch_command"))
        self.copy_menu.addAction(launch_action)

        name_action = QAction("Copy Name", self)
        name_action.triggered.connect(lambda: self.copy_attribute("name"))
        self.copy_menu.addAction(name_action)

        cmd_action = QAction("Copy Command", self)
        cmd_action.triggered.connect(lambda: self.copy_attribute("command"))
        self.copy_menu.addAction(cmd_action)

        class_action = QAction("Copy Class Pattern", self)
        class_action.triggered.connect(lambda: self.copy_attribute("class_pattern"))
        self.copy_menu.addAction(class_action)

        if app.get("aliases"):
            aliases_action = QAction("Copy Aliases", self)
            aliases_action.triggered.connect(lambda: self.copy_attribute("aliases"))
            self.copy_menu.addAction(aliases_action)

        if app.get("desktop_file"):
            desktop_action = QAction("Copy Desktop File Path", self)
            desktop_action.triggered.connect(lambda: self.copy_attribute("desktop_file"))
            self.copy_menu.addAction(desktop_action)

        id_action = QAction("Copy ID", self)
        id_action.triggered.connect(lambda: self.copy_attribute("id"))
        self.copy_menu.addAction(id_action)

        if app.get("script_path"):
            script_action = QAction("Copy Script Path", self)
            script_action.triggered.connect(lambda: self.copy_attribute("script_path"))
            self.copy_menu.addAction(script_action)

    def copy_attribute(self, attribute: str) -> None:
        """Copy an app attribute to clipboard"""
        if not self.current_app:
            return

        if attribute == "launch_command":
            text = f"kayland launch {self.current_app['name']}"
        elif attribute == "aliases":
            aliases = self.current_app.get("aliases", [])
            text = ", ".join(aliases) if aliases else "None"
        else:
            text = self.current_app.get(attribute, "")

        if text:
            # Copy to clipboard
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(text)

            # Show status message if parent app is available
            if hasattr(self.parent_app, "show_status_message"):
                self.parent_app.show_status_message(f"Copied {attribute} to clipboard", 3000)

    def show_detail_context_menu(self, pos):
        """Show context menu for the detail display"""
        if not self.current_app:
            return

        menu = QMenu(self)

        # Add actions to copy different attributes
        launch_action = QAction("Copy 'kayland launch' Command", self)
        launch_action.triggered.connect(lambda: self.copy_attribute("launch_command"))
        menu.addAction(launch_action)

        name_action = QAction("Copy Name", self)
        name_action.triggered.connect(lambda: self.copy_attribute("name"))
        menu.addAction(name_action)

        cmd_action = QAction("Copy Command", self)
        cmd_action.triggered.connect(lambda: self.copy_attribute("command"))
        menu.addAction(cmd_action)

        class_action = QAction("Copy Class Pattern", self)
        class_action.triggered.connect(lambda: self.copy_attribute("class_pattern"))
        menu.addAction(class_action)

        if self.current_app.get("aliases"):
            aliases_action = QAction("Copy Aliases", self)
            aliases_action.triggered.connect(lambda: self.copy_attribute("aliases"))
            menu.addAction(aliases_action)

        if self.current_app.get("desktop_file"):
            desktop_action = QAction("Copy Desktop File Path", self)
            desktop_action.triggered.connect(lambda: self.copy_attribute("desktop_file"))
            menu.addAction(desktop_action)

        id_action = QAction("Copy ID", self)
        id_action.triggered.connect(lambda: self.copy_attribute("id"))
        menu.addAction(id_action)

        if self.current_app.get("script_path"):
            script_action = QAction("Copy Script Path", self)
            script_action.triggered.connect(lambda: self.copy_attribute("script_path"))
            menu.addAction(script_action)

        # Show menu at cursor position
        global_pos = self.detail_display.mapToGlobal(pos)
        menu.exec(global_pos)

    def _create_detail_row(self, label: str, value: str, label_color: str) -> str:
        """Create an HTML row for the details table"""
        return f"""
        <tr>
            <td style="color: {label_color}; padding: 5px; vertical-align: top; white-space: nowrap;">{label}:</td>
            <td style="padding: 5px; vertical-align: top;">{value}</td>
        </tr>
        """

    def update_shortcuts(self, shortcuts: List[Dict[str, Any]], app_id: str) -> None:
        """Update the shortcuts section of the details display"""
        try:
            # Filter shortcuts for the current app
            app_shortcuts = [s for s in shortcuts if s.get("app_id") == app_id]

            if app_shortcuts:
                # Get current HTML content
                current_html = self.detail_display.toHtml()

                # Remove any existing shortcuts section
                if "<h3>Shortcuts" in current_html:
                    current_html = current_html.split("<h3>Shortcuts")[0]

                # Add shortcuts section
                shortcuts_html = "<h3>Shortcuts:</h3><ul>"
                for shortcut in app_shortcuts:
                    key = shortcut.get("key", "")
                    description = shortcut.get("description", "")
                    description_text = f" - {description}" if description else ""
                    shortcuts_html += f"<li>{key}{description_text}</li>"
                shortcuts_html += "</ul>"

                # Set updated HTML
                self.detail_display.setHtml(current_html + shortcuts_html)
        except Exception as e:
            logger.error(f"Error updating shortcuts: {str(e)}")

class ServiceStatusWidget(QWidget):
    """Widget showing systemd service status and controls"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.service_running = False
        self.parent_app = parent

        # Create layout
        layout = QVBoxLayout(self)

        # Status group box
        status_group = QGroupBox("Kayland Service")
        status_layout = QVBoxLayout()

        # Status indicator
        self.status_label = QLabel("● SERVICE STATUS UNKNOWN")
        self.status_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.status_label)

        # Controls
        controls_layout = QHBoxLayout()
        self.check_button = QPushButton("Check Status")
        self.start_button = QPushButton("Start Service")
        self.stop_button = QPushButton("Stop Service")
        self.restart_button = QPushButton("Restart Service")

        # Connect buttons
        self.check_button.clicked.connect(self.check_service_status)
        self.start_button.clicked.connect(lambda: self.manage_service("start"))
        self.stop_button.clicked.connect(lambda: self.manage_service("stop"))
        self.restart_button.clicked.connect(lambda: self.manage_service("restart"))

        controls_layout.addWidget(self.check_button)
        controls_layout.addWidget(self.start_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addWidget(self.restart_button)

        status_layout.addLayout(controls_layout)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # Service information
        info_group = QGroupBox("Service Information")
        info_layout = QVBoxLayout()

        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setPlainText(
            "The Kayland service allows shortcuts to work in the background.\n\n"
            "When running, you can use your configured shortcuts from anywhere\n"
            "without having to manually launch the app.\n\n"
            "Service logs can be viewed with:\n"
            "journalctl --user -u kayland.service -f"
        )
        info_layout.addWidget(info_text)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Check status on init
        QTimer.singleShot(500, self.check_service_status)

    @Slot()
    def check_service_status(self) -> None:
        """Check the status of the Kayland service"""
        try:
            import subprocess
            result = subprocess.run(
                ["systemctl", "--user", "is-active", "kayland.service"],
                capture_output=True,
                text=True
            )

            if result.stdout.strip() == "active":
                self.service_running = True
                self.status_label.setText("● SERVICE RUNNING")
                self.status_label.setStyleSheet(f"color: #00ff00; font-weight: bold;")
                if hasattr(self.parent_app, "add_log_entry"):
                    self.parent_app.add_log_entry("Kayland service is running", "success")
            else:
                self.service_running = False
                self.status_label.setText("● SERVICE STOPPED")
                self.status_label.setStyleSheet(f"color: #ff0000; font-weight: bold;")
                if hasattr(self.parent_app, "add_log_entry"):
                    self.parent_app.add_log_entry("Kayland service is not running", "warning")

            # Update buttons based on service status
            self.start_button.setEnabled(not self.service_running)
            self.stop_button.setEnabled(self.service_running)

            # Also get the full status for the log
            full_status = subprocess.run(
                ["systemctl", "--user", "status", "kayland.service"],
                capture_output=True,
                text=True
            )

            if hasattr(self.parent_app, "add_log_entry"):
                self.parent_app.add_log_entry(full_status.stdout, "info")
        except Exception as e:
            self.service_running = False
            self.status_label.setText("● SERVICE STATUS ERROR")
            self.status_label.setStyleSheet(f"color: #ff0000; font-weight: bold;")
            if hasattr(self.parent_app, "add_log_entry"):
                self.parent_app.add_log_entry(f"Error checking service status: {str(e)}", "error")

    @Slot(str)
    def manage_service(self, action: str) -> None:
        """Start, stop or restart the service"""
        try:
            import subprocess
            command = ["systemctl", "--user", action, "kayland.service"]
            result = subprocess.run(command, capture_output=True, text=True)

            if result.returncode == 0:
                message = f"Service {action} successful"
                if hasattr(self.parent_app, "add_log_entry"):
                    self.parent_app.add_log_entry(message, "success")
                if hasattr(self.parent_app, "show_status_message"):
                    self.parent_app.show_status_message(message, 3000)

                # Wait a moment for the service to change state
                QTimer.singleShot(1000, self.check_service_status)
            else:
                error = result.stderr or f"Unknown error during service {action}"
                if hasattr(self.parent_app, "add_log_entry"):
                    self.parent_app.add_log_entry(error, "error")
                if hasattr(self.parent_app, "show_status_message"):
                    self.parent_app.show_status_message(f"Service {action} failed", 3000)

        except Exception as e:
            if hasattr(self.parent_app, "add_log_entry"):
                self.parent_app.add_log_entry(f"Error during service {action}: {str(e)}", "error")


class StatusBarWithProgress(QStatusBar):
    """Status bar with built-in progress bar"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Create progress bar but don't add it to layout yet
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedWidth(150)

        # Timer for temporary messages
        self.message_timer = QTimer(self)
        self.message_timer.setSingleShot(True)
        self.message_timer.timeout.connect(self.clearMessage)

    def showMessage(self, message: str, timeout: int = 0) -> None:
        """Show a message in the status bar"""
        super().showMessage(message)

        if timeout > 0:
            self.message_timer.stop()
            self.message_timer.start(timeout)

    def showProgress(self, visible: bool = True) -> None:
        """Show or hide the progress bar"""
        if visible and self.progress_bar not in self.findChildren(QProgressBar):
            self.addPermanentWidget(self.progress_bar)
            self.progress_bar.show()
        elif not visible and self.progress_bar in self.findChildren(QProgressBar):
            self.removeWidget(self.progress_bar)

    def setProgress(self, value: int) -> None:
        """Set the progress bar value"""
        self.progress_bar.setValue(value)


class KeySequenceEdit(QLineEdit):
    """Custom widget to capture key sequences directly"""

    keySequenceChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setPlaceholderText("Click and press shortcut keys")
        self.key_sequence = ""

    def keyPressEvent(self, event):
        """Capture key presses and convert to shortcut format"""
        key = event.key()
        modifiers = event.modifiers()

        # Skip some keys that shouldn't be used in shortcuts
        if key in (Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt, Qt.Key_Meta):
            return

        sequence = []

        # Add modifiers
        if modifiers & Qt.ControlModifier:
            sequence.append("ctrl")
        if modifiers & Qt.AltModifier:
            sequence.append("alt")
        if modifiers & Qt.ShiftModifier:
            sequence.append("shift")
        if modifiers & Qt.MetaModifier:
            sequence.append("meta")

        # Add the key
        key_text = ""
        if Qt.Key_A <= key <= Qt.Key_Z:
            key_text = chr(key).lower()
        elif Qt.Key_0 <= key <= Qt.Key_9:
            key_text = chr(key)
        elif Qt.Key_F1 <= key <= Qt.Key_F12:
            key_text = f"f{key - Qt.Key_F1 + 1}"
        elif key == Qt.Key_Space:
            key_text = "space"
        elif key == Qt.Key_Tab:
            key_text = "tab"
        elif key == Qt.Key_Return or key == Qt.Key_Enter:
            key_text = "return"
        elif key == Qt.Key_Escape:
            key_text = "escape"
        elif key == Qt.Key_Home:
            key_text = "home"
        elif key == Qt.Key_End:
            key_text = "end"
        elif key == Qt.Key_Left:
            key_text = "left"
        elif key == Qt.Key_Right:
            key_text = "right"
        elif key == Qt.Key_Up:
            key_text = "up"
        elif key == Qt.Key_Down:
            key_text = "down"
        elif key == Qt.Key_PageUp:
            key_text = "pageup"
        elif key == Qt.Key_PageDown:
            key_text = "pagedown"
        elif key == Qt.Key_Insert:
            key_text = "insert"
        elif key == Qt.Key_Delete:
            key_text = "delete"

        if key_text:
            sequence.append(key_text)

        # Create shortcut text
        if sequence:
            self.key_sequence = "+".join(sequence)
            self.setText(self.key_sequence)
            self.keySequenceChanged.emit(self.key_sequence)

        event.accept()

    def clear(self):
        """Clear the key sequence"""
        super().clear()
        self.key_sequence = ""