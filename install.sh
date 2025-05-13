#!/bin/bash
# install.sh - Installer for Kayland (Arch Linux optimized)

set -e

REPO_URL="https://raw.githubusercontent.com/eraxe/kayland/main"
INSTALL_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/kayland"
SCRIPT_DIR="$HOME/.local/share/kayland"
DESKTOP_DIR="$HOME/.local/share/applications"
ASSETS_DIR="$HOME/.local/share/kayland/assets"
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

    # Check for PySide6 (required for GUI)
    if ! python3 -c "import PySide6" &> /dev/null; then
        echo "PySide6 package not found. This is required for the GUI."

        # Check if this is Arch Linux
        if command -v pacman &> /dev/null; then
            echo "Detected Arch Linux system."
            echo "PySide6 should be installed via pacman instead of pip for better system integration."
            read -p "Do you want to try installing PySide6 with pacman? (y/N): " install_pyside6_pacman
            if [[ "$install_pyside6_pacman" == "y" || "$install_pyside6_pacman" == "Y" ]]; then
                echo "Running: sudo pacman -S python-pyside6"
                sudo pacman -S python-pyside6
            else
                echo -e "${YELLOW}Note: GUI mode will not be available without PySide6.${NC}"
                echo "You can install it later with: sudo pacman -S python-pyside6"
            fi
        else
            # Not Arch Linux, try pip
            if command -v pip3 &> /dev/null; then
                read -p "Do you want to install PySide6 now using pip? (y/N): " install_pyside6
            if [[ "$install_pyside6" == "y" || "$install_pyside6" == "Y" ]]; then
                echo "Installing PySide6 package..."
                pip3 install --user pyside6
            else
                echo -e "${YELLOW}Note: GUI mode will not be available without PySide6.${NC}"
                echo "You can install it later with: pip3 install --user pyside6"
            fi
        else
            echo -e "${YELLOW}Note: GUI mode will not be available without PySide6.${NC}"
            echo "Please install PySide6 manually using your package manager."
            fi
        fi
    fi

    # Install Textual if not already installed (for backwards compatibility)
    if ! python3 -c "import textual" &> /dev/null; then
        echo "Textual package not found. This is needed for TUI mode (deprecated)."

        # Check if this is Arch Linux
        if command -v pacman &> /dev/null; then
            echo "Detected Arch Linux system."
            echo "Textual is available in the AUR. You can install it later with:"
            echo "yay -S python-textual"
        else
            # Not Arch Linux, try pip
            if command -v pip3 &> /dev/null; then
                read -p "Do you want to install Textual now using pip? (y/N): " install_textual
            if [[ "$install_textual" == "y" || "$install_textual" == "Y" ]]; then
                echo "Installing Textual package..."
                pip3 install --user textual
            else
                echo -e "${YELLOW}Note: TUI mode will not be available without Textual.${NC}"
                echo "You can install it later with: pip3 install --user textual"
            fi
        else
            echo -e "${YELLOW}Note: TUI mode will not be available without Textual.${NC}"
                echo "Please install Textual manually using your package manager."
            fi
        fi
    fi
}

# Create necessary directories
create_directories() {
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$SCRIPT_DIR"
    mkdir -p "$SCRIPT_DIR/logs"
    mkdir -p "$DESKTOP_DIR"
    mkdir -p "$ASSETS_DIR"
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

            # Download core Python files
            curl -sSL "$REPO_URL/kayland.py" -o "$SCRIPT_DIR/kayland.py"
            curl -sSL "$REPO_URL/window_manager.py" -o "$SCRIPT_DIR/window_manager.py"
            curl -sSL "$REPO_URL/app_manager.py" -o "$SCRIPT_DIR/app_manager.py"

            # Download TUI files (deprecated but kept for compatibility)
            curl -sSL "$REPO_URL/tui.py" -o "$SCRIPT_DIR/tui.py"

            # Download GUI files
            curl -sSL "$REPO_URL/gui.py" -o "$SCRIPT_DIR/gui.py"
            curl -sSL "$REPO_URL/gui_app.py" -o "$SCRIPT_DIR/gui_app.py"
            curl -sSL "$REPO_URL/gui_dialogs.py" -o "$SCRIPT_DIR/gui_dialogs.py"
            curl -sSL "$REPO_URL/gui_widgets.py" -o "$SCRIPT_DIR/gui_widgets.py"
            curl -sSL "$REPO_URL/gui_utils.py" -o "$SCRIPT_DIR/gui_utils.py"

            # Download asset files
            curl -sSL "$REPO_URL/assets/close.svg" -o "$ASSETS_DIR/close.svg"
            curl -sSL "$REPO_URL/assets/minimize.svg" -o "$ASSETS_DIR/minimize.svg"
            curl -sSL "$REPO_URL/assets/maximize.svg" -o "$ASSETS_DIR/maximize.svg"
            curl -sSL "$REPO_URL/assets/pin.svg" -o "$ASSETS_DIR/pin.svg"
            curl -sSL "$REPO_URL/assets/unpin.svg" -o "$ASSETS_DIR/unpin.svg"
            curl -sSL "$REPO_URL/assets/kayland.svg" -o "$ASSETS_DIR/kayland.svg"
            curl -sSL "$REPO_URL/assets/kayland.png" -o "$ASSETS_DIR/kayland.png"
        fi
    fi

    # If online install failed, use local files if available
    if [ "$ONLINE_INSTALL" = false ]; then
        echo "Using local installation..."

        # Check for core files
        if [ -f "$CURRENT_DIR/kayland.py" ] && \
           [ -f "$CURRENT_DIR/window_manager.py" ] && \
           [ -f "$CURRENT_DIR/app_manager.py" ]; then

            # Copy core files
            cp "$CURRENT_DIR/kayland.py" "$SCRIPT_DIR/kayland.py"
            cp "$CURRENT_DIR/window_manager.py" "$SCRIPT_DIR/window_manager.py"
            cp "$CURRENT_DIR/app_manager.py" "$SCRIPT_DIR/app_manager.py"

            # Copy TUI files if available
            if [ -f "$CURRENT_DIR/tui.py" ]; then
                cp "$CURRENT_DIR/tui.py" "$SCRIPT_DIR/tui.py"
            fi

            # Copy GUI files if available
            if [ -f "$CURRENT_DIR/gui.py" ]; then
                cp "$CURRENT_DIR/gui.py" "$SCRIPT_DIR/gui.py"
                cp "$CURRENT_DIR/gui_app.py" "$SCRIPT_DIR/gui_app.py" 2>/dev/null || true
                cp "$CURRENT_DIR/gui_dialogs.py" "$SCRIPT_DIR/gui_dialogs.py" 2>/dev/null || true
                cp "$CURRENT_DIR/gui_widgets.py" "$SCRIPT_DIR/gui_widgets.py" 2>/dev/null || true
                cp "$CURRENT_DIR/gui_utils.py" "$SCRIPT_DIR/gui_utils.py" 2>/dev/null || true
            else
                echo -e "${YELLOW}Warning: GUI files not found in current directory.${NC}"
                echo "The GUI mode will not be available."
            fi

            # Copy asset files if available
            if [ -d "$CURRENT_DIR/assets" ]; then
                # Assets directory exists, copy all assets
                for asset in "$CURRENT_DIR/assets/"*; do
                    if [ -f "$asset" ]; then
                        cp "$asset" "$ASSETS_DIR/" 2>/dev/null || true
                    fi
                done
            fi
        else
            echo -e "${RED}Error: Cannot find required files for installation.${NC}"
            echo "Please ensure the following files are in the current directory:"
            echo "  - kayland.py"
            echo "  - window_manager.py"
            echo "  - app_manager.py"
            echo "  - gui.py (for GUI mode)"
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

    # Create desktop file
    install_desktop_file

    echo -e "${GREEN}Kayland installation completed.${NC}"
}

# Create and install desktop file
install_desktop_file() {
    echo "Creating desktop file..."
    cat > "$DESKTOP_DIR/kayland.desktop" << EOF
[Desktop Entry]
Name=Kayland
Comment=KDE Wayland Window Manager
Exec=kayland gui
Icon=$ASSETS_DIR/kayland.png
Terminal=false
Type=Application
Categories=Utility;System;
Keywords=window;manager;kde;wayland;
EOF

    # Update desktop database
    if command -v update-desktop-database &> /dev/null; then
        update-desktop-database "$DESKTOP_DIR" &> /dev/null || true
    fi

    echo "Desktop file installed at $DESKTOP_DIR/kayland.desktop"
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

    # Create shortcuts config if it doesn't exist
    if [ ! -f "$CONFIG_DIR/shortcuts.json" ]; then
        echo "Creating shortcuts configuration..."
        cat > "$CONFIG_DIR/shortcuts.json" << EOF
{
    "shortcuts": []
}
EOF
    fi
}

# Install the Kayland systemd service
install_service() {
    echo "Installing Kayland service..."
    SERVICE_DIR="$HOME/.config/systemd/user"
    SERVICE_FILE="$SERVICE_DIR/kayland.service"

    # Create directory if it doesn't exist
    mkdir -p "$SERVICE_DIR"

    # Create service file
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Kayland KDE Window Manager Service
After=network.target plasma-kwin_wayland.service plasma-kwin_x11.service
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 $SCRIPT_DIR/kayland.py service
Restart=on-failure
RestartSec=10
Environment=DISPLAY=:0
Environment=XAUTHORITY=%h/.Xauthority
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=graphical-session.target
EOF

    # Reload systemd and enable service
    systemctl --user daemon-reload
    systemctl --user enable kayland.service
    systemctl --user start kayland.service

    echo -e "${GREEN}Kayland service installed and started.${NC}"
    echo "You can check the service status with: kayland service status"
}

# Uninstall the Kayland systemd service
uninstall_service() {
    echo "Stopping and removing Kayland service..."

    # Check if service exists
    if [ -f "$HOME/.config/systemd/user/kayland.service" ]; then
        # Stop and disable service
        systemctl --user stop kayland.service 2>/dev/null || true
        systemctl --user disable kayland.service 2>/dev/null || true

        # Remove service file
        rm -f "$HOME/.config/systemd/user/kayland.service"

        # Reload systemd
        systemctl --user daemon-reload

        echo -e "${GREEN}Kayland service removed.${NC}"
    else
        echo "Kayland service not installed, skipping service removal."
    fi
}

# Check the status of the Kayland service
service_status() {
    echo "Checking Kayland service status..."

    if systemctl --user is-active kayland.service >/dev/null 2>&1; then
        echo -e "${GREEN}Kayland service is running.${NC}"
        systemctl --user status kayland.service
        return 0
    else
        echo -e "${RED}Kayland service is not running.${NC}"
        systemctl --user status kayland.service
        return 1
    fi
}

# Clean previous installation
clean_install() {
    echo "Cleaning previous installation..."
    rm -rf "$SCRIPT_DIR"
    rm -f "$INSTALL_DIR/kayland"
    rm -f "$DESKTOP_DIR/kayland.desktop"

    # Optionally remove config
    if [ "$1" = "--purge" ]; then
        rm -rf "$CONFIG_DIR"
        echo "Configuration removed."
    fi
}

# Uninstall Kayland
uninstall() {
    echo "Uninstalling Kayland..."

    # Remove systemd service
    uninstall_service

    # Remove executable
    rm -f "$INSTALL_DIR/kayland"

    # Remove desktop file
    rm -f "$DESKTOP_DIR/kayland.desktop"
    if command -v update-desktop-database &> /dev/null; then
        update-desktop-database "$DESKTOP_DIR" &> /dev/null || true
    fi

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
    echo "  --service       Install Kayland as a systemd service"
    echo "  --no-service    Do not install the systemd service"
    echo "  --service-only  Only install/update the systemd service"
    echo "  --service-status Check the status of the Kayland service"
    echo "  --gui-only      Only install GUI files and dependencies"
    echo ""
}

# Main installation process
main() {
    echo -e "${GREEN}Kayland - KDE Wayland Window Manager${NC}"

    # Flag for service installation
    INSTALL_SERVICE=false
    SKIP_SERVICE=false
    SERVICE_ONLY=false
    GUI_ONLY=false
    INSTALL_MODE="install"

    # Parse arguments
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --help)
                show_help
                exit 0
                ;;
            --uninstall)
                uninstall
                ;;
            --clean)
                clean_install
                ;;
            --purge)
                clean_install "--purge"
                ;;
            --update)
                echo "Updating Kayland..."
                clean_install
                INSTALL_MODE="update"
                ;;
            --service)
                INSTALL_SERVICE=true
                ;;
            --no-service)
                SKIP_SERVICE=true
                ;;
            --service-only)
                SERVICE_ONLY=true
                INSTALL_SERVICE=true
                ;;
            --service-status)
                service_status
                exit $?
                ;;
            --gui-only)
                GUI_ONLY=true
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                show_help
                exit 1
                ;;
        esac
        shift
    done

    # Handle service-only installation
    if [ "$SERVICE_ONLY" = true ]; then
        install_service
        exit 0
    fi

    # Normal installation process
    check_environment
    check_python_dependencies
    create_directories
    install_files
    create_initial_config

    # Install service if requested
    if [ "$INSTALL_SERVICE" = true ]; then
        install_service
    elif [ "$SKIP_SERVICE" = false ] && [ "$GUI_ONLY" = false ]; then
        # Ask if user wants to install the service
        read -p "Do you want to install Kayland as a systemd service? (y/N): " install_svc
        if [[ "$install_svc" == "y" || "$install_svc" == "Y" ]]; then
            install_service
        else
            echo "Skipping service installation."
        fi
    fi

    if [ "$INSTALL_MODE" == "update" ]; then
        echo -e "${GREEN}Kayland has been updated successfully!${NC}"
    else
        echo -e "${GREEN}Kayland has been installed successfully!${NC}"
    fi

    # Check if PySide6 is installed for GUI mode
    if python3 -c "import PySide6" &> /dev/null; then
        echo "Run 'kayland gui' to start the GUI or 'kayland --help' for command-line options."
    else
        if command -v pacman &> /dev/null; then
            echo -e "${YELLOW}Note: The GUI mode requires the PySide6 package which is not installed.${NC}"
            echo "You can install it with: sudo pacman -S python-pyside6"
        else
            echo -e "${YELLOW}Note: The GUI mode requires the PySide6 package which is not installed.${NC}"
        echo "You can install it with: pip install --user pyside6"
        fi
        echo "For now, you can use 'kayland --help' for command-line options."
    fi
}

main "$@"