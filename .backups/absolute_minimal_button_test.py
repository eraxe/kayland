#!/usr/bin/env python3
# absolute_minimal_button_test.py - Bare minimum button test with debugging

import sys
from textual.app import App
from textual.widgets import Button, Static
from textual.containers import Container

# Print debug information
print(f"Python version: {sys.version}")
try:
    import textual

    print(f"Textual version: {textual.__version__}")
except Exception as e:
    print(f"Error getting Textual version: {e}")


class MinimalButtonApp(App):
    """Absolutely minimal button test"""

    # No CSS to start with - let's use Textual defaults

    def compose(self):
        """Create the simplest possible UI with buttons"""
        yield Static("Button Test")
        # Test multiple button variants
        yield Button("Default Button")
        yield Button("Primary Button", variant="primary")
        yield Button("Error Button", variant="error")
        yield Button("Success Button", variant="success")
        yield Button("Just Text", classes="just-text")

        # Add a static with the same text for comparison
        yield Static("Text in Static: Default Button")

    def on_mount(self):
        """Debug when mounted"""
        # Print out window dimensions and other useful info
        print(f"Window size: {self.size}")
        print("UI components mounted")

    def on_button_pressed(self, event):
        """Handle button press to see if they're functional"""
        # Print to console for debugging
        print(f"Button pressed: {event.button.label}")
        # Show in UI
        self.notify(f"Button pressed: {event.button.label}")


if __name__ == "__main__":
    print("Starting minimal button test app...")
    app = MinimalButtonApp()
    app.run()
    print("App finished.")