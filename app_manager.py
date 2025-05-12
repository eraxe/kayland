#!/usr/bin/env python3
# app_manager.py - Manages application definitions for Kayland

import json
import os
import logging
import uuid
from typing import Dict, List, Optional, Any

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
                    return data.get("apps", [])
            else:
                self.logger.warning(f"Config file not found: {self.config_file}")
                return []
        except Exception as e:
            self.logger.error(f"Failed to load config: {str(e)}")
            return []
    
    def _save_apps(self) -> bool:
        """Save application definitions to the config file"""
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump({"apps": self.apps}, f, indent=4)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save config: {str(e)}")
            return False
    
    def get_all_apps(self) -> List[Dict[str, Any]]:
        """Get all application definitions"""
        return self.apps
    
    def get_app_by_id(self, app_id: str) -> Optional[Dict[str, Any]]:
        """Get application definition by ID"""
        for app in self.apps:
            if app.get("id") == app_id:
                return app
        return None
    
    def get_app_by_alias(self, alias: str) -> Optional[Dict[str, Any]]:
        """Get application definition by alias"""
        for app in self.apps:
            if alias.lower() in [a.lower() for a in app.get("aliases", [])]:
                return app
        return None
    
    def add_app(self, name: str, class_pattern: str, command: str, 
                aliases: List[str] = None) -> Dict[str, Any]:
        """Add a new application definition"""
        if aliases is None:
            aliases = []
            
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
