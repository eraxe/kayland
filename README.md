# Kayland - KDE Wayland Window Manager

<img src="/api/placeholder/600/120" alt="Kayland Logo" />

Kayland is a powerful window management tool for KDE Plasma on Wayland that allows you to quickly switch between applications, toggle window states, and create shortcuts for your most-used programs. It's designed to enhance your workflow by providing a fast way to access applications across virtual desktops without cluttering your taskbar or dock.

[![Kayland Demo](/api/placeholder/800/500)](https://github.com/eraxe/kayland)

## Features

- **Application Toggling**: Launch or focus applications with a single command
- **Smart Window Management**: Minimizes active windows and activates inactive ones
- **Background Service**: Run as a systemd service with global shortcuts
- **Browser Extension Support**: Works with browser extensions, PWAs, and web apps
- **Terminal UI**: Beautiful TUI interface for managing applications
- **CLI Commands**: For scripting and terminal enthusiasts
- **Resource Name Detection**: Finds windows even when identifiers are in resource names
- **Cross-Desktop Support**: Works in KDE on both Wayland and X11

## Requirements

- KDE Plasma 5 or 6
- Wayland or X11 session
- Python 3.6+
- [kdotool](https://github.com/jinliu/kdotool) - xdotool-like utility for KDE

## Installation

1. Make sure you have kdotool installed
2. Clone the repository
3. Install the required Python packages:
   ```bash
   pip install --user textual
   ```
4. Run the installer script:
   ```bash
   ./install.sh
   ```

## Usage

### Command Line Interface

```bash
# Launch the TUI
kayland

# Launch/toggle an application by alias
kayland launch brave

# Add a new application
kayland add --name "Browser" --alias brave --class "brave-browser" --command "/usr/bin/brave-browser"

# List defined applications
kayland list

# Show debug information
kayland debug --window-info
```

### Terminal User Interface (TUI)

Launch the TUI with `kayland` and use these key commands:

- `q` - Quit
- `a` - Add application
- `e` - Edit selected application
- `c` - Copy selected application
- `l` - Launch selected application
- `r` - Refresh application list

### Service Mode & Shortcuts

Kayland can run as a systemd service, providing global shortcuts for all your applications:

```bash
# Install and start the service
kayland service install

# Check service status
kayland service status

# Add a shortcut (Alt+B for browser)
kayland shortcut add --app browser --key "alt+b"

# List registered shortcuts
kayland shortcut list

# Remove a shortcut
kayland shortcut remove "alt+b"

# Uninstall service
kayland service uninstall
```

## Supported Application Types

Kayland works with most types of applications:

### Strong Support

- **Native Linux Applications**: KDE, GNOME, GTK, Qt
- **Electron Applications**: VS Code, Discord, Slack
- **Web Applications**: PWAs, browser extensions, Chrome/Firefox apps
- **Firefox Progressive Web Apps**: Great for web apps you use frequently
- **Chrome Extensions and Apps**: Gemini, Google Meet, etc.

### Moderate Support

- **Wine/Proton Applications**: Windows apps running on Linux
- **Java Applications**: IntelliJ IDEA, Eclipse, etc.
- **XWayland Applications**: Legacy X11 apps on Wayland

### Other Compatibility

Most other applications with window classes or resource names are supported.

## How It Works

Kayland uses a combination of direct KWin scripting and kdotool commands to:

1. Find windows matching patterns in class, resource name, or title
2. Determine their active state
3. Take appropriate action (minimize active windows, activate inactive windows)
4. Launch applications when no matching windows are found

## Examples

### Basic Example - Adding a Browser

```bash
kayland add --name "Firefox" --alias ff --class "firefox" --command "/usr/bin/firefox"
kayland launch ff  # Launch Firefox or activate its window if running
```

### Web App Example

```bash
# For Gmail PWA created with Firefox PWA extension
kayland add --name "Gmail" --alias gmail --class "gmail.IDENTIFIER" --command "firefoxpwa site launch IDENTIFIER"

# Launch Gmail with one command
kayland launch gmail
```

### Switching Between Code and Terminal

```bash
# Create shortcut for VSCode
kayland shortcut add --app vscode --key "alt+c"

# Create shortcut for Terminal
kayland shortcut add --app konsole --key "alt+t"

# Now press Alt+C to switch to VSCode, Alt+T for terminal
```

## Configuration

Configuration files are stored in `~/.config/kayland/`:

- `apps.json` - Defined applications
- `shortcuts.json` - Keyboard shortcuts
- `config.json` - General configuration

Logs are stored in `~/.local/share/kayland/logs/`.

## Debugging

If you have issues with window detection:

```bash
# Show detailed information about all windows
kayland debug --window-info

# Search for windows matching a pattern
kayland debug --search "Firefox"

# Check logs
less ~/.local/share/kayland/logs/kayland.log
```

## Advanced Usage

### Using Regex for Window Matching

You can use regex patterns for more complex window matching:

```bash
kayland add --name "All Terminals" --alias terms --class ".*terminal.*" --command "konsole"
```

### Custom Launch Commands

Add parameters to your launch commands:

```bash
kayland add --name "Firefox Private" --alias ffp --class "firefox" --command "/usr/bin/firefox --private-window"
```

### Service Logs

View service logs with systemd:

```bash
journalctl --user -u kayland.service -f
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [kdotool](https://github.com/jinliu/kdotool) - For providing the window control functionality
- [Textual](https://github.com/Textualize/textual) - For the beautiful TUI
- All contributors who have helped improve Kayland

---

<p align="center">Made with ❤️ for KDE Plasma users</p>