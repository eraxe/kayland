#!/usr/bin/env python3
# simplified_confirm_dialog.py - A standalone implementation of a confirmation dialog

import logging
from textual.app import App
from textual.screen import ModalScreen
from textual.widgets import Button, Static
from textual.containers import Container, Horizontal

logger = logging.getLogger("kayland.confirm_dialog")


class ConfirmDialog(ModalScreen):
    """A confirmation dialog"""

    def __init__(self, title: str, message: str):
        super().__init__()
        self.title = title
        self.message = message

    def compose(self):
        with Container(id="dialog", classes="form-container"):
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


# Test application
class TestApp(App):
    CSS = """
    Screen {
        background: #2b213a;
    }

    .form-container {
        background: #2b213a;
        border: solid #ff00ff;
        padding: 2;
        margin: 2 4;
        width: 40;
        height: 10;
    }

    .heading {
        background: #f615f6;
        color: #ffffff;
        text-align: center;
        margin-bottom: 1;
    }

    .button-container {
        height: auto;
        margin-top: 1;
    }

    Button {
        background: #00fff5;
        color: #3b1f5f;
        margin: 0 1;
    }

    Static {
        color: #ffffff;
    }
    """

    def on_mount(self):
        """Show dialog when app starts"""
        self.push_screen(
            ConfirmDialog("Test Dialog", "This is a test confirmation dialog."),
            self.on_dialog_result
        )

    def on_dialog_result(self, result):
        """Handle dialog result"""
        if result:
            self.exit(message="User confirmed")
        else:
            self.exit(message="User cancelled")


# Run the test app if run directly
if __name__ == "__main__":
    app = TestApp()
    app.run()