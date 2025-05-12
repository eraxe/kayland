#!/usr/bin/env python3
# tui_service.py - Service management for Kayland TUI

import subprocess
import logging
from typing import Optional, Callable

from textual.app import App
from textual.containers import Container, Horizontal
from textual.widgets import Static, Button
from rich.text import Text

logger = logging.getLogger("kayland.tui.service")


class ServiceStatusWidget(Container):
    """Widget showing systemd service status and controls"""

    def __init__(self, parent_app):
        super().__init__(id="service-status-widget")
        self.parent_app = parent_app
        self.status_timer = 0
        self.service_running = False

    def compose(self):
        with Container(classes="status-container"):
            yield Static("Kayland Service", classes="subheading")
            yield Static(id="service-status", classes="status-text")

            with Horizontal(classes="service-controls"):
                yield Button("Check Status", id="check-status")
                yield Button("Start Service", id="start-service")
                yield Button("Stop Service", id="stop-service")
                yield Button("Restart Service", id="restart-service")

    def on_button_pressed(self, event):
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

            # Update buttons based on service status
            try:
                start_btn = self.query_one("#start-service", Button)
                stop_btn = self.query_one("#stop-service", Button)

                if self.service_running:
                    start_btn.disabled = True
                    stop_btn.disabled = False
                else:
                    start_btn.disabled = False
                    stop_btn.disabled = True
            except Exception as e:
                self.parent_app.add_log_entry(f"Error updating service buttons: {str(e)}", "error")

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