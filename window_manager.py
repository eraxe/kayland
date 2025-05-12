#!/usr/bin/env python3
# window_manager.py - Core window management functionality for Kayland

import subprocess
import logging
import shlex
import re
import os
from typing import List, Dict, Optional, Tuple

class WindowManager:
    """Handles window management operations using kdotool"""
    
    def __init__(self):
        self.logger = logging.getLogger("kayland.window_manager")
    
    def _run_kdotool(self, command: List[str]) -> Tuple[str, bool]:
        """Run kdotool with the given command and return the output"""
        try:
            cmd = ["kdotool"] + command
            self.logger.debug(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode != 0:
                self.logger.error(f"Command failed: {result.stderr}")
                return (result.stderr, False)
            
            return (result.stdout.strip(), True)
        except Exception as e:
            self.logger.error(f"Error running kdotool: {str(e)}")
            return (str(e), False)
    
    def get_all_windows(self) -> List[str]:
        """Get all window IDs"""
        output, success = self._run_kdotool(["search", "--class", ".*"])
        if not success:
            return []
        
        # Parse window IDs, filtering out any invalid values
        windows = []
        for line in output.splitlines():
            if re.match(r'^\{?[a-zA-Z0-9-]+\}?$', line.strip()):
                windows.append(line.strip())
        
        return windows
    
    def get_active_window(self) -> Optional[str]:
        """Get the currently active window ID"""
        output, success = self._run_kdotool(["getactivewindow"])
        if not success or not output:
            return None
        return output.strip()
    
    def get_window_class(self, window_id: str) -> Optional[str]:
        """Get the class of a window"""
        output, success = self._run_kdotool(["getwindowclassname", window_id])
        if not success:
            return None
        return output.strip()
    
    def check_window_state(self, window_id: str, property_name: str) -> bool:
        """Check if a window has a particular state property"""
        output, _ = self._run_kdotool(["windowstate", "--add", property_name, window_id, "--debug"])
        return "is already set" in output
    
    def activate_window(self, window_id: str) -> bool:
        """Activate (focus) a window"""
        _, success = self._run_kdotool(["windowactivate", window_id])
        return success
    
    def minimize_window(self, window_id: str) -> bool:
        """Minimize a window"""
        _, success = self._run_kdotool(["windowminimize", window_id])
        return success
    
    def launch_application(self, command: str) -> bool:
        """Launch an application using the given command"""
        try:
            # Split the command into args and use Popen to avoid blocking
            args = shlex.split(command)
            proc = subprocess.Popen(
                args, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to launch application: {str(e)}")
            return False
    
    def toggle_window(self, class_pattern: str, launch_command: str) -> Tuple[str, bool]:
        """
        Toggle a window based on its state:
        - If window exists and is active: minimize it
        - If window exists and is not active: activate it
        - If window doesn't exist: launch the application
        """
        windows = self.get_all_windows()
        active_window = self.get_active_window()
        found_window = False
        
        for window_id in windows:
            window_class = self.get_window_class(window_id)
            if not window_class:
                continue
                
            # Check if window class matches the pattern
            if re.search(class_pattern, window_class):
                found_window = True
                is_active = (window_id == active_window)
                
                if is_active:
                    # Window is active, minimize it
                    self.minimize_window(window_id)
                    return (f"Window {window_id} minimized", True)
                else:
                    # Window is not active, activate it
                    self.activate_window(window_id)
                    return (f"Window {window_id} activated", True)
        
        # No matching window found, launch the application
        if not found_window:
            success = self.launch_application(launch_command)
            if success:
                return (f"Launched application: {launch_command}", True)
            else:
                return ("Failed to launch application", False)
                
        return ("No action taken", False)
