#!/usr/bin/env python3
# window_manager.py - Core window management functionality for Kayland

import subprocess
import logging
import shlex
import re
import os
import sys
import time
import uuid
import json
from typing import List, Dict, Optional, Tuple, Any


class WindowManager:
    """Handles window management operations using kdotool"""

    def __init__(self):
        self.logger = logging.getLogger("kayland.window_manager")

        # Verify kdotool is available
        if not self._check_kdotool():
            self.logger.error("kdotool not found in PATH")
            raise RuntimeError("kdotool not found. Please install kdotool first.")

    def _check_kdotool(self) -> bool:
        """Check if kdotool is available"""
        try:
            result = subprocess.run(
                ["which", "kdotool"],
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode == 0
        except Exception:
            return False

    def _run_kdotool(self, command: List[str]) -> Tuple[str, bool]:
        """Run kdotool with the given command and return the output"""
        try:
            cmd = ["kdotool"] + command
            cmd_str = " ".join(cmd)
            self.logger.debug(f"Running kdotool command: {cmd_str}")

            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if result.returncode != 0:
                self.logger.error(f"kdotool command failed with code {result.returncode}: {result.stderr}")
                return (f"Command '{cmd_str}' failed: {result.stderr}", False)

            if result.stdout:
                self.logger.debug(f"kdotool command output: {result.stdout.strip()}")

            return (result.stdout.strip(), True)
        except Exception as e:
            error_msg = f"Exception running kdotool: {str(e)}"
            self.logger.error(error_msg)
            return (error_msg, False)

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

    def get_window_name(self, window_id: str) -> Optional[str]:
        """Get the name/title of a window"""
        output, success = self._run_kdotool(["getwindowname", window_id])
        if not success:
            return None
        return output.strip()

    def check_window_state(self, window_id: str, property_name: str) -> bool:
        """
        Check if a window has a particular state property.
        Returns True if the property is already set, False otherwise.
        """
        try:
            output, _ = self._run_kdotool(["windowstate", "--add", property_name, window_id, "--debug"])
            return "is already set" in output
        except Exception as e:
            self.logger.error(f"Error checking window state: {str(e)}")
            return False

    def activate_window(self, window_id: str) -> bool:
        """Activate (focus) a window, ensuring the ID is properly formatted for kdotool"""
        try:
            # Clean the window ID - remove any markers or prefixes
            clean_id = window_id.strip()

            # Extract UUID if it's embedded in a longer string
            uuid_pattern = r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})'
            match = re.search(uuid_pattern, clean_id, re.IGNORECASE)
            if match:
                clean_id = match.group(1)

            # Add curly braces if not present
            if not clean_id.startswith('{'):
                clean_id = '{' + clean_id
            if not clean_id.endswith('}'):
                clean_id = clean_id + '}'

            self.logger.debug(f"Activating window with formatted ID: {clean_id}")

            # Now use kdotool with the properly formatted ID
            _, success = self._run_kdotool(["windowactivate", clean_id])
            return success

        except Exception as e:
            self.logger.error(f"Error activating window: {str(e)}")
            return False

    def minimize_window(self, window_id: str) -> bool:
        """Minimize a window"""
        try:
            # Clean the window ID - remove any markers or prefixes
            clean_id = window_id.strip()

            # Extract UUID if it's embedded in a longer string
            uuid_pattern = r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})'
            match = re.search(uuid_pattern, clean_id, re.IGNORECASE)
            if match:
                clean_id = match.group(1)

            # Add curly braces if not present
            if not clean_id.startswith('{'):
                clean_id = '{' + clean_id
            if not clean_id.endswith('}'):
                clean_id = clean_id + '}'

            self.logger.debug(f"Minimizing window with formatted ID: {clean_id}")

            _, success = self._run_kdotool(["windowminimize", clean_id])
            return success

        except Exception as e:
            self.logger.error(f"Error minimizing window: {str(e)}")
            return False

    def _find_matching_windows_direct(self, class_pattern: str) -> List[Dict[str, Any]]:
        """
        Use a direct KWin script to find matching windows.
        This searches both class and resourceName for the pattern.
        """
        found_windows = []
        class_pattern_lower = class_pattern.lower()

        try:
            # Create a temporary script to scan all windows
            import tempfile

            # Generate a unique marker for this run
            marker = str(uuid.uuid4())

            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as tmp:
                tmp_path = tmp.name
                # Write a KWin script to find matching windows
                tmp.write(f'''
// KWin script to find windows matching a pattern
const PATTERN = "{class_pattern}";
const PATTERN_LOWER = PATTERN.toLowerCase();
const MARKER = "{marker}";

function findMatchingWindows() {{
    print("SCAN_START_" + MARKER);
    var windows = workspace.windowList();
    var activeWindow = workspace.activeWindow;

    print("Found " + windows.length + " total windows");

    for (var i = 0; i < windows.length; i++) {{
        try {{
            var win = windows[i];
            var windowClass = win.resourceClass || "";
            var windowName = win.resourceName || "";  // This is the important field for IDs!
            var windowTitle = win.caption || "";
            var isActive = (win === activeWindow);
                var windowId = win.internalId || "";

            // Log complete details for debugging
            print("WINDOW_" + MARKER + "_" + i + " DETAILS:");
            print("  ID: " + windowId);
            print("  Class: " + windowClass);
            print("  ResourceName: " + windowName);
            print("  Caption: " + windowTitle);
            print("  Active: " + isActive);

            // Check for matches (case insensitive)
            var classLower = windowClass.toLowerCase();
            var nameLower = windowName.toLowerCase();
            var titleLower = windowTitle.toLowerCase();

            if (classLower.indexOf(PATTERN_LOWER) !== -1 || 
                nameLower.indexOf(PATTERN_LOWER) !== -1 || 
                titleLower.indexOf(PATTERN_LOWER) !== -1) {{

                // Determine match reason
                var matchReason = "";
                if (classLower.indexOf(PATTERN_LOWER) !== -1) {{
                    matchReason = "class contains pattern";
                }} else if (nameLower.indexOf(PATTERN_LOWER) !== -1) {{
                    matchReason = "resource name contains pattern";
                }} else {{
                    matchReason = "title contains pattern";
                }}

                    // IMPORTANT: Output the window ID as the first field, separated clearly
                    print("MATCH_" + MARKER + "|" + windowId + "|" + 
                          windowClass + "|" + windowName + "|" + windowTitle + "|" + 
                          isActive + "|" + matchReason);
            }}
        }} catch (e) {{
            print("ERROR processing window: " + e);
        }}
    }}
    print("SCAN_END_" + MARKER);
}}

// Run the function
findMatchingWindows();
''')

            try:
                # Run the KWin script using dbus-send
                load_cmd = ["dbus-send", "--print-reply", "--dest=org.kde.KWin",
                            "/Scripting", "org.kde.kwin.Scripting.loadScript",
                            f"string:{tmp_path}", "string:kayland_scan"]
                load_result = subprocess.run(load_cmd, check=False, capture_output=True, text=True)

                # Extract script ID
                script_id = None
                if "int32" in load_result.stdout:
                    script_id_match = re.search(r'int32\s+(\d+)', load_result.stdout)
                    if script_id_match:
                        script_id = script_id_match.group(1)

                if not script_id:
                    self.logger.error("Failed to load KWin script")
                    return []

                # Try different paths for the script
                script_path = None
                for path in [f"/Scripting/Script{script_id}", f"/{script_id}"]:
                    run_cmd = ["dbus-send", "--print-reply", "--dest=org.kde.KWin",
                               path, "org.kde.kwin.Script.run"]
                    run_result = subprocess.run(run_cmd, check=False, capture_output=True, text=True)
                    if run_result.returncode == 0:
                        script_path = path
                        break

                if not script_path:
                    self.logger.error("Failed to run KWin script")
                    return []

                # Wait for the script to complete
                time.sleep(0.5)

                # Get journal output
                journal_cmd = ["journalctl", "--user", "-u", "plasma-kwin_wayland.service",
                               "-u", "plasma-kwin_x11.service", "--since=5 seconds ago", "-o", "cat"]
                journal_result = subprocess.run(journal_cmd, check=False, capture_output=True, text=True)

                if not journal_result.stdout:
                    self.logger.error("No output from KWin script")
                    return []

                # Parse the output to find matches
                lines = journal_result.stdout.splitlines()
                for line in lines:
                    if f"MATCH_{marker}|" in line:
                        # Split by the pipe character (|)
                        parts = line.split("|")
                        if len(parts) >= 7:
                            win_id = parts[1]         # Get just the window ID part
                            win_class = parts[2]
                            win_name = parts[3]
                            win_title = parts[4]
                            is_active = parts[5].lower() == "true"
                            match_reason = parts[6]

                            found_windows.append({
                                "id": win_id,         # Store the clean window ID
                                "class": win_class,
                                "classname": win_name,
                                "caption": win_title,
                                "is_active": is_active,
                                "match_reason": match_reason
                            })

                # Try to clean up the script
                if script_path:
                    stop_cmd = ["dbus-send", "--print-reply", "--dest=org.kde.KWin",
                                script_path, "org.kde.kwin.Script.stop"]
                    subprocess.run(stop_cmd, check=False, capture_output=True, text=True)

            except Exception as e:
                self.logger.error(f"Error in direct window search: {str(e)}")
            finally:
                # Clean up temporary file
                try:
                    os.unlink(tmp_path)
                except:
                    pass
        except Exception as e:
            self.logger.error(f"Failed to set up direct window search: {str(e)}")
        import traceback
        self.logger.error(traceback.format_exc())

        return found_windows

    def _find_chrome_windows(self) -> List[Dict[str, Any]]:
        """Find any Chrome windows for enhanced detection"""
        chrome_windows = []

        try:
            # Get all windows first
            windows = self.get_all_windows()
            active_window = self.get_active_window()

            for window_id in windows:
                window_class = self.get_window_class(window_id)

                if window_class and "chrome" in window_class.lower():
                    window_title = self.get_window_name(window_id)
                    is_active = (window_id == active_window)

                    chrome_windows.append({
                        "id": window_id,
                        "class": window_class,
                        "caption": window_title,
                        "is_active": is_active,
                        "match_reason": "chrome window"
                    })
        except Exception as e:
            self.logger.error(f"Error finding Chrome windows: {str(e)}")

        return chrome_windows

    def _find_matching_windows_fallback(self, class_pattern: str) -> List[Dict[str, Any]]:
        """Fallback method using kdotool search commands directly"""
        found_windows = []

        try:
            # First try searching by class
            output_class, success_class = self._run_kdotool(["search", "--class", class_pattern])
            window_ids_class = set(output_class.splitlines()) if success_class and output_class else set()

            # Then try searching by classname (resource name)
            output_name, success_name = self._run_kdotool(["search", "--classname", class_pattern])
            window_ids_name = set(output_name.splitlines()) if success_name and output_name else set()

            # Combine results (remove duplicates)
            window_ids = list(window_ids_class.union(window_ids_name))

            if not window_ids:
                return []

            # Get active window for comparison
            active_window, _ = self._run_kdotool(["getactivewindow"])
            active_window = active_window.strip() if active_window else None

            # Get details for each window
            for window_id in window_ids:
                if not window_id.strip():
                    continue

                class_output, _ = self._run_kdotool(["getwindowclassname", window_id])
                window_class = class_output.strip() if class_output else ""

                name_output, _ = self._run_kdotool(["getwindowname", window_id])
                window_name = name_output.strip() if name_output else ""

                is_active = (window_id == active_window)

                # Determine match reason
                match_reason = "unknown match"
                if class_pattern.lower() in window_class.lower():
                    match_reason = "class contains pattern"
                elif window_name and class_pattern.lower() in window_name.lower():
                    match_reason = "window name contains pattern"

                found_windows.append({
                    "id": window_id,
                    "class": window_class,
                    "caption": window_name,
                    "is_active": is_active,
                    "match_reason": match_reason
                })

            return found_windows

        except Exception as e:
            self.logger.error(f"Error in fallback window search: {str(e)}")
            return []

    def _find_chrome_windows(self) -> List[Dict[str, Any]]:
        """Find any Chrome windows for enhanced detection"""
        chrome_windows = []

        try:
            # Get all windows first
            windows = self.get_all_windows()
            active_window = self.get_active_window()

            for window_id in windows:
                window_class = self.get_window_class(window_id)

                if window_class and "chrome" in window_class.lower():
                    window_title = self.get_window_name(window_id)
                    is_active = (window_id == active_window)

                    chrome_windows.append({
                        "id": window_id,
                        "class": window_class,
                        "caption": window_title,
                        "is_active": is_active,
                        "match_reason": "chrome window"
                    })
        except Exception as e:
            self.logger.error(f"Error finding Chrome windows: {str(e)}")

        return chrome_windows

    def launch_application(self, command: str) -> bool:
        """Launch an application using the given command"""
        try:
            self.logger.info(f"Launching application: {command}")

            # Split the command into args and handle quoted arguments correctly
            args = shlex.split(command)
            self.logger.debug(f"Command split into args: {args}")

            # Ensure the command exists
            executable = args[0]
            if os.path.exists(executable):
                self.logger.debug(f"Executable exists at path: {executable}")
            elif self._command_exists(executable):
                self.logger.debug(f"Executable found in PATH: {executable}")
            else:
                self.logger.error(f"Command not found: {executable}")
                return False

            try:
                # Use Popen to avoid blocking and properly detach the process
                proc = subprocess.Popen(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True,
                    env=os.environ.copy(),  # Pass the current environment
                    close_fds=True  # Close file descriptors
                )

                # Check if process started correctly
                if proc.pid > 0:
                    self.logger.info(f"Started process with PID: {proc.pid}")
                    # Give the application a moment to start
                    time.sleep(0.5)
                    return True
                else:
                    self.logger.error("Failed to get valid PID for launched process")
                    return False

            except Exception as e:
                self.logger.error(f"Subprocess.Popen failed: {str(e)}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to launch application: {str(e)}")
            return False

    def _command_exists(self, command: str) -> bool:
        """Check if a command exists in PATH"""
        try:
            result = subprocess.run(
                ["which", command],
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode == 0
        except Exception:
            return False

    def toggle_window(self, class_pattern: str, launch_command: str) -> Tuple[str, bool]:
        """
        Toggle a window based on its state:
        - If window exists and is active: minimize it
        - If window exists and is not active: activate it
        - If window doesn't exist: launch the application

        This method uses two search strategies to find matching windows.
        """
        try:
            # Log start of operation
            log_message = f"Starting window toggle operation for pattern '{class_pattern}'"
            self.logger.info(log_message)
            return_messages = [log_message]

            # Check if pattern suggests a special application type
            is_firefox_pwa = "firefoxpwa" in launch_command and len(class_pattern) >= 20
            is_chrome_app = "chrome" in launch_command.lower() and len(class_pattern) >= 10

            if is_firefox_pwa or is_chrome_app:
                log_message = f"Detected special application type: {'FirefoxPWA' if is_firefox_pwa else 'Chrome App'}"
                self.logger.info(log_message)
                return_messages.append(log_message)

            # First try direct KWin script method
            found_windows = []
            try:
                found_windows = self._find_matching_windows_direct(class_pattern)
                if found_windows:
                    log_message = f"Direct search found {len(found_windows)} windows"
                    self.logger.info(log_message)
                    return_messages.append(log_message)
            except Exception as e:
                log_message = f"Direct search failed: {str(e)}"
                self.logger.warning(log_message)
                return_messages.append(log_message)

            # If direct search failed or found nothing, try fallback method
            if not found_windows:
                log_message = "Trying fallback search method with kdotool"
                self.logger.info(log_message)
                return_messages.append(log_message)

                try:
                    # Try searching by class
                    class_output, class_success = self._run_kdotool(["search", "--class", class_pattern])
                    class_windows = class_output.splitlines() if class_success and class_output else []

                    # Try searching by classname (resource name)
                    name_output, name_success = self._run_kdotool(["search", "--classname", class_pattern])
                    name_windows = name_output.splitlines() if name_success and name_output else []

                    # Combine results (removing duplicates)
                    window_ids = list(set(class_windows + name_windows))
                    log_message = f"Fallback search found {len(window_ids)} windows"
                    self.logger.info(log_message)
                    return_messages.append(log_message)

                    if window_ids:
                        # Get active window for comparison
                        active_output, _ = self._run_kdotool(["getactivewindow"])
                        active_window = active_output.strip() if active_output else None

                        # Process each window
                        for window_id in window_ids:
                            if not window_id or not window_id.strip():
                                continue

                            # Get window details
                            class_result, _ = self._run_kdotool(["getwindowclassname", window_id])
                            window_class = class_result.strip() if class_result else ""

                            name_result, _ = self._run_kdotool(["getwindowname", window_id])
                            window_name = name_result.strip() if name_result else ""

                            is_active = (window_id == active_window)
                            match_reason = "matched pattern"

                            found_windows.append({
                                "id": window_id,
                                "class": window_class,
                                "caption": window_name,
                                "is_active": is_active,
                                "match_reason": match_reason
                            })

                            log_message = f"Found window: {window_id} - {window_class} - '{window_name}' - Active: {is_active}"
                            self.logger.debug(log_message)
                except Exception as e:
                    log_message = f"Fallback search failed: {str(e)}"
                    self.logger.warning(log_message)
                    return_messages.append(log_message)

            # Log what we found
            if found_windows:
                log_message = f"Found {len(found_windows)} matching windows in total"
                self.logger.info(log_message)
                return_messages.append(log_message)

                # First check if any window is active - if so, minimize it
                active_matches = [win for win in found_windows if win.get("is_active", False)]
                if active_matches:
                    # We have an active matching window - minimize it
                    window_to_minimize = active_matches[0]
                    log_message = f"Action: Window {window_to_minimize['id']} is active, will minimize"
                    self.logger.info(log_message)
                    return_messages.append(log_message)

                    if self.minimize_window(window_to_minimize["id"]):
                        log_message = f"Success: Window {window_to_minimize['id']} minimized"
                        self.logger.info(log_message)
                        return_messages.append(log_message)
                        return ("\n".join(return_messages), True)
                    else:
                        log_message = f"ERROR: Failed to minimize window {window_to_minimize['id']}"
                        self.logger.error(log_message)
                        return_messages.append(log_message)
                        return ("\n".join(return_messages), False)
                else:
                    # No active matching window - activate the first match
                    window_to_activate = found_windows[0]
                    log_message = f"Action: Window {window_to_activate['id']} is not active, will activate"
                    self.logger.info(log_message)
                    return_messages.append(log_message)

                    if self.activate_window(window_to_activate["id"]):
                        log_message = f"Success: Window {window_to_activate['id']} activated"
                        self.logger.info(log_message)
                        return_messages.append(log_message)
                        return ("\n".join(return_messages), True)
                    else:
                        log_message = f"ERROR: Failed to activate window {window_to_activate['id']}"
                        self.logger.error(log_message)
                        return_messages.append(log_message)
                        return ("\n".join(return_messages), False)
            else:
                # No matching windows found, launch the application
                log_message = f"No windows matching pattern '{class_pattern}' found, launching: {launch_command}"
                self.logger.info(log_message)
                return_messages.append(log_message)

                success = self.launch_application(launch_command)

                if success:
                    log_message = f"Success: Launched application: {launch_command}"
                    self.logger.info(log_message)
                    return_messages.append(log_message)
                    return ("\n".join(return_messages), True)
                else:
                    log_message = f"ERROR: Failed to launch application: {launch_command}"
                    self.logger.error(log_message)
                    return_messages.append(log_message)
                    return ("\n".join(return_messages), False)

            # Fallback return if we somehow reach this point
            return ("\n".join(return_messages), False)

        except Exception as e:
            log_message = f"ERROR in toggle_window: {str(e)}"
            self.logger.error(log_message)
            # Include stack trace for better debugging
            import traceback
            self.logger.error(traceback.format_exc())
            return (log_message, False)