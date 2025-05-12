#!/bin/bash
# install.sh - Installer for Kayland

set -e

REPO_URL="https://raw.githubusercontent.com/eraxe/kayland/main"
INSTALL_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/kayland"
SCRIPT_DIR="$HOME/.local/share/kayland"
CURRENT_DIR="$(pwd)"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running on KDE Wayland
check_environment() {
    if ! echo "$XDG_SESSION_TYPE" | grep -q "wayland"; then
        echo -e "${YELLOW}Warning: Kayland is designed for Wayland. Current session: $XDG_SESSION_TYPE${NC}"
        # Not failing, just warning
    fi

    if ! echo "$XDG_CURRENT_DESKTOP" | grep -q -i "kde"; then
        echo -e "${YELLOW}Warning: Kayland is designed for KDE. Current desktop: $XDG_CURRENT_DESKTOP${NC}"
        # Not failing, just warning
    fi

    if ! command -v kdotool &> /dev/null; then
        echo -e "${YELLOW}Warning: kdotool is recommended but not found.${NC}"
        echo "Some functionality may be limited without kdotool"
        # Not failing, just warning
    fi
}

# Check if Python dependencies are installed
check_python_dependencies() {
    echo "Checking Python dependencies..."

    # Check for Python 3
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: Python 3 is required but not found${NC}"
        exit 1
    fi

    # Check for pip
    if ! command -v pip3 &> /dev/null; then
        echo -e "${YELLOW}Warning: pip3 is not found. Will attempt to install dependencies without it.${NC}"
        HAS_PIP=false
    else
        HAS_PIP=true
    fi

    # Install Textual if not already installed
    if ! python3 -c "import textual" &> /dev/null; then
        echo "Installing Textual package..."
        if [ "$HAS_PIP" = true ]; then
            pip3 install --user textual
        else
            echo -e "${YELLOW}Cannot install Textual. Please install it manually: pip3 install --user textual${NC}"
        fi
    fi
}

# Create necessary directories
create_directories() {
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$SCRIPT_DIR"
    mkdir -p "$SCRIPT_DIR/logs"
}

# Try to fetch from GitHub, if fails use local files
install_files() {
    echo "Installing Kayland files..."

    # Try to fetch from GitHub first
    ONLINE_INSTALL=false

    if command -v curl &> /dev/null; then
        # Test if the repo exists and is accessible
        if curl -s --head "$REPO_URL/kayland.py" | grep "200 OK" > /dev/null; then
            ONLINE_INSTALL=true
            echo "Using online installation from GitHub..."

            # Download Python files
            curl -sSL "$REPO_URL/kayland.py" -o "$SCRIPT_DIR/kayland.py"
            curl -sSL "$REPO_URL/window_manager.py" -o "$SCRIPT_DIR/window_manager.py"
            curl -sSL "$REPO_URL/app_manager.py" -o "$SCRIPT_DIR/app_manager.py"
            curl -sSL "$REPO_URL/tui.py" -o "$SCRIPT_DIR/tui.py"
        fi
    fi

    # If online install failed, use local files if available
    if [ "$ONLINE_INSTALL" = false ]; then
        echo "Using local installation..."

        if [ -f "$CURRENT_DIR/kayland.py" ] && \
           [ -f "$CURRENT_DIR/window_manager.py" ] && \
           [ -f "$CURRENT_DIR/app_manager.py" ] && \
           [ -f "$CURRENT_DIR/tui.py" ]; then

            cp "$CURRENT_DIR/kayland.py" "$SCRIPT_DIR/kayland.py"
            cp "$CURRENT_DIR/window_manager.py" "$SCRIPT_DIR/window_manager.py"
            cp "$CURRENT_DIR/app_manager.py" "$SCRIPT_DIR/app_manager.py"
            cp "$CURRENT_DIR/tui.py" "$SCRIPT_DIR/tui.py"
        else
            echo -e "${RED}Error: Cannot find required files for installation.${NC}"
            echo "Please ensure the following files are in the current directory:"
            echo "  - kayland.py"
            echo "  - window_manager.py"
            echo "  - app_manager.py"
            echo "  - tui.py"
            exit 1
        fi
    fi

    # Make files executable
    chmod +x "$SCRIPT_DIR/kayland.py"

    # Create launcher script
    cat > "$INSTALL_DIR/kayland" << EOF
#!/bin/bash
# Kayland launcher
python3 "$SCRIPT_DIR/kayland.py" "\$@"
EOF

    # Make launcher executable
    chmod +x "$INSTALL_DIR/kayland"

    echo -e "${GREEN}Kayland installation completed.${NC}"
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

# Clean previous installation
clean_install() {
    echo "Cleaning previous installation..."
    rm -rf "$SCRIPT_DIR"
    rm -f "$INSTALL_DIR/kayland"

    # Optionally remove config
    if [ "$1" = "--purge" ]; then
        rm -rf "$CONFIG_DIR"
        echo "Configuration removed."
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

    echo -e "${GREEN}Kayland has been uninstalled.${NC}"
    exit 0
}

# Show help
show_help() {
    echo "Kayland - KDE Wayland Window Manager Installer"
    echo ""
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  --help          Show this help message"
    echo "  --uninstall     Uninstall Kayland"
    echo "  --update        Update Kayland"
    echo "  --clean         Clean previous installation before installing"
    echo "  --purge         Clean previous installation including configuration"
    echo ""
}

# Main installation process
main() {
    echo -e "${GREEN}Kayland - KDE Wayland Window Manager${NC}"

    # Check for help flag
    if [ "$1" == "--help" ]; then
        show_help
        exit 0
    fi

    # Check for uninstall flag
    if [ "$1" == "--uninstall" ]; then
        uninstall
    fi

    # Check for clean flag
    if [ "$1" == "--clean" ]; then
        clean_install
        shift
    fi

    # Check for purge flag
    if [ "$1" == "--purge" ]; then
        clean_install "--purge"
        shift
    fi

    # Check for update flag
    if [ "$1" == "--update" ]; then
        echo "Updating Kayland..."
        clean_install
    else
        echo "Installing Kayland..."
    fi

    check_environment
    check_python_dependencies
    create_directories
    install_files
    create_initial_config

    if [ "$1" == "--update" ]; then
        echo -e "${GREEN}Kayland has been updated successfully!${NC}"
    else
        echo -e "${GREEN}Kayland has been installed successfully!${NC}"
    fi

    echo "Run 'kayland' to start the TUI or 'kayland --help' for command-line options."
}

main "$@"