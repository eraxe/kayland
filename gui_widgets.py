#!/usr/bin/env python3
# gui_widgets.py - Custom widgets for Kayland GUI

import os
import logging
from typing import Dict, List, Any, Optional, Callable

from PySide6.QtCore import Qt, QSize, Signal, Slot, QTimer, QPoint
from PySide6.QtGui import QIcon, QColor, QStandardItemModel, QStandardItem, QAction
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QTextBrowser, QSplitter, QTableWidget, QTableWidgetItem,
    QGroupBox, QFormLayout, QLineEdit, QFrame, QMenu, QTextEdit,
    QListView, QAbstractItemView, QStatusBar, QProgressBar
)

from gui_utils import SYNTHWAVE_COLORS

logger = logging.getLogger("kayland.gui.widgets")


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
        self.dragPos = None

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

    def update_style(self):
        """Update the styling of the title bar"""
        dark_bg = SYNTHWAVE_COLORS["dark_bg"]
        accent = SYNTHWAVE_COLORS["accent"]

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
                background-color: rgba(255, 255, 255, 0.2);
                border-radius: 15px;
            }}
        """)

        # Try to load icons from assets, fall back to text if not available
        try:
            asset_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")

            self.close_btn.setIcon(QIcon(os.path.join(asset_path, "close.svg")))
            self.minimize_btn.setIcon(QIcon(os.path.join(asset_path, "minimize.svg")))
            self.maximize_btn.setIcon(QIcon(os.path.join(asset_path, "maximize.svg")))
            self.pin_btn.setIcon(QIcon(os.path.join(asset_path, "pin.svg") if self.is_pinned else
                                    os.path.join(asset_path, "unpin.svg")))

            self.close_btn.setIconSize(QSize(16, 16))
            self.minimize_btn.setIconSize(QSize(16, 16))
            self.maximize_btn.setIconSize(QSize(16, 16))
            self.pin_btn.setIconSize(QSize(16, 16))
        except:
            # Fallback to text if icons not available
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
            self.dragPos = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle mouse move events for dragging the window"""
        if event.buttons() == Qt.LeftButton and self.dragPos is not None:
            if self.parent:
                self.parent.move(self.parent.pos() + event.globalPosition().toPoint() - self.dragPos)
                self.dragPos = event.globalPosition().toPoint()
                event.accept()

    def mouseReleaseEvent(self, event):
        """Handle mouse release events"""
        self.dragPos = None
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

        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Application Details")
        title.setProperty("heading", True)
        layout.addWidget(title)

        # Details display
        self.detail_display = QTextBrowser()
        self.detail_display.setReadOnly(True)
        self.detail_display.setOpenExternalLinks(False)
        layout.addWidget(self.detail_display)

        # Set layout margins
        layout.setContentsMargins(0, 0, 0, 0)

    def update_details(self, app: Optional[Dict[str, Any]]) -> None:
        """Update the details display with app information"""
        try:
            if app:
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