#!/usr/bin/env python3
# button_diagnostic.py - Diagnostic tool for button text issues

import sys
import os
import platform

# Print system information
print(f"Python version: {sys.version}")
print(f"Platform: {platform.platform()}")
print(f"Terminal: {os.environ.get('TERM', 'Unknown')}")
print(f"Terminal program: {os.environ.get('TERM_PROGRAM', 'Unknown')}")

# Check Textual version
try:
    import textual

    print(f"Textual version: {textual.__version__}")

    # Check if Button widget is available
    from textual.widgets import Button

    print("Button widget imported successfully")

    # Inspect Button structure to better understand how it works
    print("\nButton class structure:")
    for attr in dir(Button):
        if not attr.startswith('__'):
            try:
                value = getattr(Button, attr)
                if callable(value):
                    print(f"  {attr}: method")
                else:
                    print(f"  {attr}: {type(value)}")
            except Exception as e:
                print(f"  {attr}: error - {e}")

    # Create and inspect a button instance if possible
    try:
        button = Button("Test")
        print("\nButton instance created")
        print(f"Button label: {button.label}")
        print(f"Button classes: {button.classes}")

        # Try to get composed classes if that's supported in this version
        if hasattr(button, '_compose') and callable(button._compose):
            print("Button uses _compose method")
        else:
            print("Button does not use _compose method")

        # Check if it has a compose method
        if hasattr(button, 'compose') and callable(button.compose):
            print("Button has compose method")
        else:
            print("Button does not have compose method")

    except Exception as e:
        print(f"Error creating button instance: {e}")

    # Print any other relevant info if available
    if hasattr(textual, '__file__'):
        print(f"\nTextual installed at: {textual.__file__}")

except ImportError as e:
    print(f"Error importing Textual: {e}")

# Check for Rich as well
try:
    import rich

    print(f"\nRich version: {rich.__version__}")
except ImportError as e:
    print(f"\nError importing Rich: {e}")

# Try to identify the terminal emulator
print("\nTerminal identification:")
for key, value in os.environ.items():
    if 'TERM' in key or 'KONSOLE' in key or 'TERMINAL' in key or 'TTY' in key:
        print(f"  {key}: {value}")

# Final instructions
print("\nINSTRUCTIONS:")
print("1. Run the minimal_button_test.py script")
print("2. Take a screenshot of what you see in the terminal")
print("3. Share the screenshot and the output of this diagnostic script")
print("4. This will help identify why buttons aren't showing text")