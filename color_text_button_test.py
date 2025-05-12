#!/usr/bin/env python3
# color_text_button_test.py - Testing different text color approaches

import sys
from textual.app import App
from textual.widgets import Button, Static, Label
from textual.containers import Container, Vertical


class ColorButtonApp(App):
    """Test different button text color approaches"""

    # Try several different CSS approaches
    CSS = """
    Screen {
        background: #2b213a;
    }

    Container {
        height: auto;
        border: solid green;
        padding: 1;
        margin: 1;
    }

    #basic-buttons {
        border: solid red;
    }

    #styled-buttons {
        border: solid blue;
    }

    /* Basic button with foreground color set directly */
    .basic-button {
        background: #555555;
        color: #ffffff;  /* White */
    }

    /* Style the button label explicitly */
    .styled-button {
        background: #555555;
    }

    .styled-button > .button--label {
        color: #ffffff;  /* White */
    }

    /* A more contrasting approach */
    .contrast-button {
        background: #000000;  /* Black background */
        color: #ffff00;       /* Yellow text */
    }

    /* Force label to be visible */
    .force-visible-button {
        background: #000000;
    }

    .force-visible-button .button--label {
        color: #ff0000 !important;  /* Bright red with !important */
        text-style: bold;
    }

    /* Explicitly style text */
    Label {
        color: white;
    }

    Static {
        color: white;
    }
    """

    def compose(self):
        yield Static("Button Text Color Test", id="title")

        with Container(id="basic-buttons"):
            yield Label("Basic Buttons:")
            yield Button("Default Button")
            yield Button("Basic White", classes="basic-button")
            yield Button("High Contrast", classes="contrast-button")

        with Container(id="styled-buttons"):
            yield Label("Styled Label Buttons:")
            yield Button("Styled Label", classes="styled-button")
            yield Button("FORCE VISIBLE", classes="force-visible-button")

    def on_button_pressed(self, event):
        """Handle button press"""
        print(f"Button pressed: {event.button.label}")
        self.notify(f"Button pressed: {event.button.label}")


if __name__ == "__main__":
    print("Starting color button test app...")
    app = ColorButtonApp()
    app.run()
    print("App finished.")