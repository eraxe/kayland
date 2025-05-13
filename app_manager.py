#!/usr/bin/env python3
# app_manager.py - Manages application definitions for Kayland

import json
import os
import logging
import uuid
import re
import subprocess
from typing import Dict, List, Optional, Any, Union


class AppManager:
    """Manages application definitions for Kayland"""

    def __init__(self, config_dir: str = None):
        """Initialize the app manager with the config directory"""
        self.logger = logging.getLogger("kayland.app_manager")

        if config_dir is None:
            self.config_dir = os.path.expanduser("~/.config/kayland")
        else:
            self.config_dir = config_dir

        self.config_file = os.path.join(self.config_dir, "apps.json")
        self.apps = self._load_apps()

    def _load_apps(self) -> List[Dict[str, Any]]:
        """Load application definitions from the config file"""
        try:
            self.logger.debug(f"Attempting to load apps from {self.config_file}")

            if os.path.exists(self.config_file):
                # Check if file is empty
                if os.path.getsize(self.config_file) == 0:
                    self.logger.warning(f"Config file is empty: {self.config_file}")
                    return []

                with open(self.config_file, 'r') as f:
                    file_content = f.read()
                    self.logger.debug(f"Loaded file content: {file_content[:200]}...")  # First 200 chars

                    try:
                        data = json.loads(file_content)

                        # Validate structure
                        if not isinstance(data, dict):
                            self.logger.warning(
                                f"Invalid config structure (not a dict) in {self.config_file}, resetting")
                            return []

                        if "apps" not in data:
                            self.logger.warning(
                                f"Invalid config structure (no 'apps' key) in {self.config_file}, resetting")
                            return []

                        if not isinstance(data["apps"], list):
                            self.logger.warning(f"Invalid apps data (not a list) in {self.config_file}, resetting")
                            return []

                        self.logger.info(f"Successfully loaded {len(data['apps'])} apps from {self.config_file}")
                        return data.get("apps", [])
                    except json.JSONDecodeError as je:
                        self.logger.error(f"Failed to parse config: {str(je)}")

                        # Log the actual content that failed to parse
                        self.logger.error(f"Content that failed to parse: {file_content}")

                        # Check for backup
                        backup_file = f"{self.config_file}.bak"
                        if os.path.exists(backup_file):
                            self.logger.info(f"Attempting to load from backup: {backup_file}")
                            try:
                                with open(backup_file, 'r') as bf:
                                    backup_data = json.load(bf)
                                    if isinstance(backup_data, dict) and "apps" in backup_data:
                                        self.logger.info(
                                            f"Successfully loaded {len(backup_data['apps'])} apps from backup")
                                        return backup_data.get("apps", [])
                            except Exception as be:
                                self.logger.error(f"Failed to load from backup: {str(be)}")

                        # Create backup of corrupted file
                        corrupted_file = f"{self.config_file}.corrupted"
                        import shutil
                        try:
                            shutil.copy2(self.config_file, corrupted_file)
                            self.logger.info(f"Created backup of corrupted config at {corrupted_file}")
                        except Exception as ex:
                            self.logger.error(f"Failed to create backup of corrupted file: {str(ex)}")

                        return []
            else:
                self.logger.info(f"Config file not found: {self.config_file}, will create on first save")
                return []
        except Exception as e:
            self.logger.error(f"Failed to load config: {str(e)}")
            return []

    def _save_apps(self) -> bool:
        """Save application definitions to the config file"""
        try:
            # Create config directory if it doesn't exist
            os.makedirs(self.config_dir, exist_ok=True)

            # Log what we're saving
            self.logger.debug(f"Saving {len(self.apps)} apps to {self.config_file}")

            # Create a temporary file first to avoid corruption if writing fails
            temp_file = f"{self.config_file}.tmp"
            try:
                with open(temp_file, 'w') as f:
                    json_data = {"apps": self.apps}
                    json.dump(json_data, f, indent=4)

                    # Ensure data is written to disk
                    f.flush()
                    os.fsync(f.fileno())

                # Log the temp file content for debugging
                with open(temp_file, 'r') as f:
                    temp_content = f.read()
                    self.logger.debug(f"Temp file content: {temp_content[:200]}...")  # First 200 chars

                # If we got here, writing was successful, so move the temp file to the actual file
                if os.path.exists(self.config_file):
                    # Create a backup of the current file
                    backup_file = f"{self.config_file}.bak"
                    if os.path.exists(backup_file):
                        os.remove(backup_file)
                    os.rename(self.config_file, backup_file)
                    self.logger.debug(f"Created backup at {backup_file}")

                # Now rename the temp file to the actual file
                os.rename(temp_file, self.config_file)
                self.logger.info(f"Successfully saved apps to {self.config_file}")

                # Verify the file was saved correctly
                if os.path.exists(self.config_file):
                    with open(self.config_file, 'r') as f:
                        saved_data = json.load(f)
                        self.logger.debug(f"Verified saved data: {len(saved_data.get('apps', []))} apps")

                return True
            except Exception as e:
                self.logger.error(f"Failed to save config: {str(e)}")
                # Try a direct write as fallback
                with open(self.config_file, 'w') as f:
                    json.dump({"apps": self.apps}, f, indent=4)
                self.logger.info("Used fallback direct save method")
                return True
        except Exception as e:
            self.logger.error(f"Failed to save config: {str(e)}")
            # Last resort: print the data that should have been saved
            print(f"ERROR saving apps: {str(e)}")
            print(f"Apps data: {json.dumps({'apps': self.apps}, indent=2)}")
            return False

    def validate_app_data(self, name: str, class_pattern: str) -> Union[None, str]:
        """Validate app data and return error message if invalid"""
        if not name or not name.strip():
            return "App name cannot be empty"

        # Validate regex pattern
        try:
            re.compile(class_pattern)
        except re.error:
            return f"Invalid regular expression: {class_pattern}"

        return None

    def get_all_apps(self) -> List[Dict[str, Any]]:
        """Get all application definitions"""
        return self.apps

    def get_app_by_id(self, app_id: str) -> Optional[Dict[str, Any]]:
        """Get application definition by ID"""
        if not app_id:
            return None

        for app in self.apps:
            if app.get("id") == app_id:
                return app
        return None

    def get_app_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get application definition by name (case insensitive)"""
        if not name:
            return None

        name_lower = name.lower()
        for app in self.apps:
            if app.get("name", "").lower() == name_lower:
                return app
        return None

    def get_app_by_alias(self, alias: str) -> Optional[Dict[str, Any]]:
        """Get application definition by alias (case insensitive)"""
        if not alias:
            return None

        alias_lower = alias.lower()

        # First check exact matches
        for app in self.apps:
            if alias_lower in [a.lower() for a in app.get("aliases", [])]:
                return app

        # If no exact match, check if alias is in app name
        for app in self.apps:
            if alias_lower in app.get("name", "").lower():
                return app

        return None

    def add_app(self, name: str, class_pattern: str, command: str,
                aliases: List[str] = None) -> Dict[str, Any]:
        """Add a new application definition"""
        if aliases is None:
            aliases = []

        # Validate app data
        error = self.validate_app_data(name, class_pattern)
        if error:
            raise ValueError(error)

        # Create a new app definition
        app = {
            "id": str(uuid.uuid4()),
            "name": name,
            "class_pattern": class_pattern,
            "command": command,
            "aliases": aliases
        }

        self.apps.append(app)
        self._save_apps()
        return app

    def update_app(self, app_id: str, name: str = None, class_pattern: str = None,
                   command: str = None, aliases: List[str] = None) -> Optional[Dict[str, Any]]:
        """Update an existing application definition"""
        app = self.get_app_by_id(app_id)
        if not app:
            return None

        # Validate updated data
        if name is not None and class_pattern is not None:
            error = self.validate_app_data(name, class_pattern)
        elif class_pattern is not None and name is None:
            error = self.validate_app_data(app["name"], class_pattern)
        elif name is not None and class_pattern is None:
            error = self.validate_app_data(name, app["class_pattern"])
        else:
            error = None

        if error:
            raise ValueError(error)

        if name is not None:
            app["name"] = name
        if class_pattern is not None:
            app["class_pattern"] = class_pattern
        if command is not None:
            app["command"] = command
        if aliases is not None:
            app["aliases"] = aliases

        self._save_apps()
        return app

    def update_app_attribute(self, app_id: str, attribute: str, value: Any) -> Optional[Dict[str, Any]]:
        """Update a specific attribute of an app"""
        app = self.get_app_by_id(app_id)
        if not app:
            return None

        app[attribute] = value
        self._save_apps()
        return app

    def delete_app(self, app_id: str) -> bool:
        """Delete an application definition"""
        app = self.get_app_by_id(app_id)
        if not app:
            return False

        self.apps.remove(app)
        self._save_apps()
        return True

    def copy_app(self, app_id: str, new_name: str = None) -> Optional[Dict[str, Any]]:
        """Copy an application definition"""
        app = self.get_app_by_id(app_id)
        if not app:
            return None

        # Create a copy with a new ID
        new_app = app.copy()
        new_app["id"] = str(uuid.uuid4())

        if new_name:
            new_app["name"] = new_name
        else:
            new_app["name"] = f"{app['name']} (Copy)"

        # Modify aliases to avoid conflicts
        if "aliases" in new_app and new_app["aliases"]:
            new_app["aliases"] = [f"{alias}_copy" for alias in new_app["aliases"]]

        self.apps.append(new_app)
        self._save_apps()
        return new_app

    def import_apps(self, apps_data: List[Dict[str, Any]]) -> int:
        """Import application definitions from external data
        Returns the number of apps successfully imported"""
        imported_count = 0

        for app_data in apps_data:
            try:
                if "name" in app_data and "class_pattern" in app_data and "command" in app_data:
                    name = app_data["name"]
                    class_pattern = app_data["class_pattern"]
                    command = app_data["command"]
                    aliases = app_data.get("aliases", [])

                    # Don't import duplicates
                    existing = self.get_app_by_name(name)
                    if existing:
                        continue

                    self.add_app(name, class_pattern, command, aliases)
                    imported_count += 1
            except Exception as e:
                self.logger.error(f"Failed to import app: {str(e)}")
                continue

        if imported_count > 0:
            self._save_apps()

        return imported_count

    def export_apps(self, file_path: str = None) -> Union[str, List[Dict[str, Any]]]:
        """Export application definitions to a file or return as data
        If file_path is specified, saves to file and returns the path,
        otherwise returns the data structure"""
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump({"apps": self.apps}, f, indent=4)
                return file_path
            except Exception as e:
                self.logger.error(f"Failed to export apps: {str(e)}")
                raise
        else:
            return self.apps

    def generate_app_script(self, app_id: str, output_path: str = None) -> str:
        """Generate a shell script to launch or toggle the application"""
        app = self.get_app_by_id(app_id)
        if not app:
            raise ValueError(f"App not found with ID: {app_id}")

        # If no output path specified, use config dir
        if output_path is None:
            output_path = os.path.join(self.config_dir, "scripts")
            os.makedirs(output_path, exist_ok=True)

        # Create script filename
        script_filename = f"{app['name'].lower().replace(' ', '_').replace('/', '_')}_toggle.sh"
        script_path = os.path.join(output_path, script_filename)

        # Create script content
        script_content = f"""#!/bin/bash
# Auto-generated script to toggle {app['name']}
# Generated by Kayland

CLASS_PATTERN="{app['class_pattern']}"
COMMAND="{app['command']}"

# Check if window exists and is active
WINDOW_ID=$(kdotool search --class "$CLASS_PATTERN" | head -n 1)
ACTIVE_WINDOW=$(kdotool getactivewindow)

if [ -n "$WINDOW_ID" ]; then
    if [ "$WINDOW_ID" = "$ACTIVE_WINDOW" ]; then
        # Window exists and is active, minimize it
        kdotool windowminimize "$WINDOW_ID"
    else
        # Window exists but is not active, activate it
        kdotool windowactivate "$WINDOW_ID"
    fi
else
    # Window doesn't exist, launch the application
    $COMMAND &
fi
"""

        # Write script to file
        with open(script_path, 'w') as f:
            f.write(script_content)

        # Make script executable
        os.chmod(script_path, 0o755)

        # Store the script path in the app object for easy reference
        app["script_path"] = script_path
        self._save_apps()

        return script_path

    # Shortcut Management Methods
    def get_shortcuts(self) -> List[Dict[str, Any]]:
        """Get all configured shortcuts"""
        try:
            shortcuts_file = os.path.join(self.config_dir, "shortcuts.json")
            if os.path.exists(shortcuts_file):
                with open(shortcuts_file, 'r') as f:
                    data = json.load(f)
                    return data.get("shortcuts", [])
            return []
        except Exception as e:
            self.logger.error(f"Failed to load shortcuts: {str(e)}")
            return []

    def get_shortcut_by_id(self, shortcut_id: str) -> Optional[Dict[str, Any]]:
        """Get shortcut by ID"""
        if not shortcut_id:
            return None

        shortcuts = self.get_shortcuts()
        for shortcut in shortcuts:
            if shortcut.get("id") == shortcut_id:
                return shortcut
        return None

    def add_shortcut(self, app_id: str, key: str, description: str = "") -> Dict[str, Any]:
        """Add a keyboard shortcut for an application"""
        app = self.get_app_by_id(app_id)
        if not app:
            raise ValueError(f"App not found with ID: {app_id}")

        # Validate shortcut format (e.g., ctrl+alt+a)
        if not re.match(r'^[a-z0-9+]+$', key.lower()):
            raise ValueError(f"Invalid shortcut format: {key}")

        # Check for duplicate
        shortcuts = self.get_shortcuts()
        if any(s.get("key", "").lower() == key.lower() for s in shortcuts):
            raise ValueError(f"Shortcut '{key}' already exists")

        shortcut = {
            "id": str(uuid.uuid4()),
            "app_id": app_id,
            "key": key,
            "description": description
        }

        shortcuts.append(shortcut)

        try:
            shortcuts_file = os.path.join(self.config_dir, "shortcuts.json")
            with open(shortcuts_file, 'w') as f:
                json.dump({"shortcuts": shortcuts}, f, indent=4)

            # Try to register with kdotool if possible
            try:
                self._register_kdotool_shortcut(shortcut, app)
            except Exception as e:
                self.logger.warning(f"Failed to register shortcut with kdotool: {str(e)}")

            # Notify the service if it's running
            self._notify_service("reload")

        except Exception as e:
            self.logger.error(f"Failed to save shortcut: {str(e)}")
            raise

        return shortcut

    def update_shortcut(self, shortcut_id: str, app_id: str = None, key: str = None,
                        description: str = None) -> Optional[Dict[str, Any]]:
        """Update an existing shortcut"""
        shortcuts = self.get_shortcuts()
        shortcut = None

        # Find the shortcut to update
        for i, s in enumerate(shortcuts):
            if s.get("id") == shortcut_id:
                shortcut = s
                shortcut_index = i
                break

        if not shortcut:
            return None

        # Validate new key if provided
        if key and key != shortcut.get("key"):
            if not re.match(r'^[a-z0-9+]+$', key.lower()):
                raise ValueError(f"Invalid shortcut format: {key}")

            # Check for duplicate
            if any(s.get("key", "").lower() == key.lower() and s.get("id") != shortcut_id
                   for s in shortcuts):
                raise ValueError(f"Shortcut '{key}' already exists")

        # Validate app_id if provided
        if app_id and app_id != shortcut.get("app_id"):
            app = self.get_app_by_id(app_id)
            if not app:
                raise ValueError(f"App not found with ID: {app_id}")

        # Update fields
        if app_id is not None:
            shortcut["app_id"] = app_id
        if key is not None:
            shortcut["key"] = key
        if description is not None:
            shortcut["description"] = description

        # Save changes
        try:
            shortcuts[shortcut_index] = shortcut
            shortcuts_file = os.path.join(self.config_dir, "shortcuts.json")
            with open(shortcuts_file, 'w') as f:
                json.dump({"shortcuts": shortcuts}, f, indent=4)

            # Try to update registration with kdotool
            if app_id is not None or key is not None:
                try:
                    app = self.get_app_by_id(shortcut["app_id"])
                    self._register_kdotool_shortcut(shortcut, app)
                except Exception as e:
                    self.logger.warning(f"Failed to update shortcut with kdotool: {str(e)}")

            # Notify the service if it's running
            self._notify_service("reload")

            return shortcut

        except Exception as e:
            self.logger.error(f"Failed to update shortcut: {str(e)}")
            raise

    def remove_shortcut(self, shortcut_id: str) -> bool:
        """Remove a keyboard shortcut"""
        shortcuts = self.get_shortcuts()
        for i, shortcut in enumerate(shortcuts):
            if shortcut.get("id") == shortcut_id:
                removed = shortcuts.pop(i)

                try:
                    shortcuts_file = os.path.join(self.config_dir, "shortcuts.json")
                    with open(shortcuts_file, 'w') as f:
                        json.dump({"shortcuts": shortcuts}, f, indent=4)

                    # Try to unregister with kdotool
                    try:
                        self._unregister_kdotool_shortcut(removed)
                    except Exception as e:
                        self.logger.warning(f"Failed to unregister shortcut with kdotool: {str(e)}")

                    # Notify the service if it's running
                    self._notify_service("reload")
                    return True

                except Exception as e:
                    self.logger.error(f"Failed to remove shortcut: {str(e)}")
                    raise

        return False

    def _register_kdotool_shortcut(self, shortcut: Dict[str, Any], app: Dict[str, Any]) -> bool:
        """Register a shortcut with kdotool"""
        try:
            shortcut_name = f"kayland_{shortcut['id']}"
            key = shortcut["key"]
            app_id = app["id"]
            class_pattern = app["class_pattern"]
            command = app["command"]

            # Use kdotool to register the shortcut
            cmd = [
                "kdotool",
                "--shortcut", key,
                "--name", shortcut_name,
                "search", "--class", class_pattern
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0

        except Exception as e:
            self.logger.error(f"Failed to register shortcut with kdotool: {str(e)}")
            return False

    def _unregister_kdotool_shortcut(self, shortcut: Dict[str, Any]) -> bool:
        """Unregister a shortcut with kdotool"""
        try:
            shortcut_name = f"kayland_{shortcut['id']}"

            # Use kdotool to unregister the shortcut
            cmd = ["kdotool", "--remove", shortcut_name]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0

        except Exception as e:
            self.logger.error(f"Failed to unregister shortcut with kdotool: {str(e)}")
            return False

    def _notify_service(self, command: str) -> bool:
        """Send a command to the service if it's running"""
        try:
            socket_path = os.path.expanduser("~/.cache/kayland/kayland.sock")
            if not os.path.exists(socket_path):
                return False

            import socket
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.connect(socket_path)
            client.sendall(f"{command}:".encode('utf-8'))
            client.close()
            return True

        except Exception as e:
            self.logger.error(f"Failed to notify service: {str(e)}")
            return False