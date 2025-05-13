#!/usr/bin/env python3
# button_text_fix.py - Test script to fix button text visibility

from textual.app import App
from textual.widgets import Button, Static
from textual.containers import Container, Vertical


class ButtonTestApp(App):
    """Test app for button text visibility"""

    # CSS with explicit styling for button labels
    CSS = """
    Screen {
        background: #2b213a;
    }

    Button {
        background: #00fff5;
        color: #3b1f5f;  /* Button text color */
        margin: 0 1;
        height: 1;
    }

    /* This is the key fix - explicitly style the button label */
    Button > .button--label {
        color: #3b1f5f;  /* Ensure label text is visible */
        text-style: bold;
    }

    Static {
        color: #ffffff;
    }

    #container {
        width: 50%;
        height: 50%;
        border: solid #ff00ff;
        align: center middle;
    }
    """

    def compose(self):
        with Container(id="container"):
            with Vertical(id="buttons"):
                yield Static("Button Test", id="title")
                yield Button("Test Button 1", id="btn1", variant="primary")
                yield Button("Test Button 2", id="btn2", variant="success")
                yield Button("Test Button 3", id="btn3", variant="error")
                yield Static("If you can see button text, the fix worked!")

    def on_button_pressed(self, event):
        """Handle button press"""
        self.notify(f"Button clicked: {event.button.label}")


if __name__ == "__main__":
    app = ButtonTestApp()
    app.run()