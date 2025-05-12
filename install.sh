#!/bin/bash
# install.sh - Installer for Kayland

set -e

REPO_URL="https://raw.githubusercontent.com/eraxe/kayland/main"
INSTALL_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/kayland"
SCRIPT_DIR="$HOME/.local/share/kayland"

# Check if running on KDE Wayland
check_environment() {
    if ! echo "$XDG_SESSION_TYPE" | grep -q "wayland"; then
        echo "Error: Kayland requires Wayland. Current session: $XDG_SESSION_TYPE"
        exit 1
    fi
    
    if ! echo "$XDG_CURRENT_DESKTOP" | grep -q -i "kde"; then
        echo "Error: Kayland requires KDE. Current desktop: $XDG_CURRENT_DESKTOP"
        exit 1
    fi
    
    if ! command -v kdotool &> /dev/null; then
        echo "Error: kdotool is required but not found."
        echo "Please install kdotool first: https://github.com/jinliu/kdotool"
        exit 1
    fi
}

# Create necessary directories
create_directories() {
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$SCRIPT_DIR"
    mkdir -p "$SCRIPT_DIR/logs"
}

# Download Kayland files
download_files() {
    echo "Downloading Kayland files..."
    
    # Download Python files
    curl -sSL "$REPO_URL/kayland.py" -o "$SCRIPT_DIR/kayland.py"
    curl -sSL "$REPO_URL/window_manager.py" -o "$SCRIPT_DIR/window_manager.py"
    curl -sSL "$REPO_URL/app_manager.py" -o "$SCRIPT_DIR/app_manager.py"
    curl -sSL "$REPO_URL/tui.py" -o "$SCRIPT_DIR/tui.py"
    
    # Make files executable
    chmod +x "$SCRIPT_DIR/kayland.py"
    
    # Create executable symlink
    ln -sf "$SCRIPT_DIR/kayland.py" "$INSTALL_DIR/kayland"
    
    echo "Kayland installation completed."
}

# Create initial configuration if it doesn't exist
create_initial_config() {
    if [ ! -f "$CONFIG_DIR/apps.json" ]; then
        echo "Creating initial configuration..."
        cat > "$CONFIG_DIR/apps.json" << EOF
{
    "apps": []
}
EOF
    fi
}

# Uninstall Kayland
uninstall() {
    echo "Uninstalling Kayland..."
    
    # Remove executable
    rm -f "$INSTALL_DIR/kayland"
    
    # Ask if user wants to keep configuration
    read -p "Do you want to keep your configuration? (y/N): " keep_config
    if [[ "$keep_config" != "y" && "$keep_config" != "Y" ]]; then
        rm -rf "$CONFIG_DIR"
        echo "Configuration removed."
    else
        echo "Configuration kept at $CONFIG_DIR"
    fi
    
    # Remove script directory
    rm -rf "$SCRIPT_DIR"
    
    echo "Kayland has been uninstalled."
    exit 0
}

# Main installation process
main() {
    echo "Kayland - KDE Wayland Window Manager"
    
    # Check for uninstall flag
    if [ "$1" == "--uninstall" ]; then
        uninstall
    fi
    
    # Check for update flag
    if [ "$1" == "--update" ]; then
        echo "Updating Kayland..."
    else
        echo "Installing Kayland..."
    fi
    
    check_environment
    create_directories
    download_files
    create_initial_config
    
    if [ "$1" == "--update" ]; then
        echo "Kayland has been updated successfully!"
    else
        echo "Kayland has been installed successfully!"
    fi
    
    echo "Run 'kayland' to start the TUI or 'kayland --help' for command-line options."
}

main "$@"
