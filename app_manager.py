#!/usr/bin/env python3
# app_manager.py - Manages application definitions for Kayland

import json
import os
import logging
import uuid
import re
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
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    # Validate structure
                    if not isinstance(data, dict) or "apps" not in data:
                        self.logger.warning(f"Invalid config structure in {self.config_file}, resetting")
                        return []
                    if not isinstance(data["apps"], list):
                        self.logger.warning(f"Invalid apps data in {self.config_file}, resetting")
                        return []
                    return data.get("apps", [])
            else:
                self.logger.info(f"Config file not found: {self.config_file}, will create on first save")
                return []
        except json.JSONDecodeError as je:
            self.logger.error(f"Failed to parse config: {str(je)}")
            self.logger.info("Creating backup of corrupted config file")
            if os.path.exists(self.config_file):
                backup_file = f"{self.config_file}.bak"
                try:
                    import shutil
                    shutil.copy2(self.config_file, backup_file)
                    self.logger.info(f"Created backup at {backup_file}")
                except Exception as ex:
                    self.logger.error(f"Failed to create backup: {str(ex)}")
            return []
        except Exception as e:
            self.logger.error(f"Failed to load config: {str(e)}")
            return []

    def _save_apps(self) -> bool:
        """Save application definitions to the config file"""
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            # Create a temporary file first to avoid corruption if writing fails
            temp_file = f"{self.config_file}.tmp"
            with open(temp_file, 'w') as f:
                json.dump({"apps": self.apps}, f, indent=4)

            # If we got here, writing was successful, so move the temp file to the actual file
            import os
            if os.path.exists(self.config_file):
                os.replace(temp_file, self.config_file)
            else:
                os.rename(temp_file, self.config_file)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save config: {str(e)}")
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