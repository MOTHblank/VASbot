"""
Pywinauto API - Windows Automation using pywinauto.

This module provides a PywinautoBot class for Windows GUI automation,
with graceful fallback when pywinauto is not installed.

Usage:
    from core.pywinauto_api import PywinautoBot, is_pywinauto_available

    if is_pywinauto_available():
        bot = PywinautoBot()
        # Use the bot for automation
"""

import time
from typing import Optional, List, Dict, Any

# Try to import pywinauto, provide fallback if not available
try:
    from pywinauto import Application, timings, findbestmatch, findwindows

    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False
    Application = None
    timings = None
    findbestmatch = None
    findwindows = None


def is_pywinauto_available() -> bool:
    """
    Check if pywinauto is available.

    Returns:
        bool: True if pywinauto is installed, False otherwise.
    """
    return PYWINAUTO_AVAILABLE


class PywinautoError(Exception):
    """Base exception for PywinautoBot errors."""

    pass


class PywinautoNotAvailableError(PywinautoError):
    """Raised when pywinauto is not installed."""

    pass


class WindowNotFoundError(PywinautoError):
    """Raised when a window cannot be found."""

    pass


class ElementNotFoundError(PywinautoError):
    """Raised when a control element cannot be found."""

    pass


class PywinautoBot:
    """
    A comprehensive Windows automation class using pywinauto.

    This class wraps pywinauto functionality for window management,
    element interaction, and control operations.

    Attributes:
        app (Application): The connected pywinauto Application instance.
        current_window: The currently active window wrapper.

    Example:
        >>> bot = PywinautoBot()
        >>> window = bot.wait_window("Notepad", timeout=5)
        >>> bot.click_element(window, "Button", "OK")
        >>> bot.type_into(window, "Edit", "Hello World")
    """

    def __init__(self, backend: str = "win32"):
        """
        Initialize the PywinautoBot.

        Args:
            backend: The backend to use ("win32" or "uia"). Default is "win32".

        Raises:
            PywinautoNotAvailableError: If pywinauto is not installed.
        """
        if not PYWINAUTO_AVAILABLE:
            raise PywinautoNotAvailableError(
                "pywinauto is not installed. Install it with: pip install pywinauto"
            )

        self._backend = backend
        self.app: Optional[Any] = None
        self.current_window: Optional[Any] = None

        # Set default timing values
        if timings:
            try:
                timings.Timings.exists_timeout = 5
                timings.Timings.after_click_wait = 0.1
            except AttributeError:
                pass

    def _ensure_app(self):
        """Ensure an Application instance exists."""
        if self.app is None:
            self.app = Application(backend=self._backend)
        return self.app

    def get_app(self, hwnd: int) -> Any:
        """Connect to a specific window by HWND and return it."""
        try:
            app = Application(backend=self._backend).connect(handle=hwnd)
            return app.window(handle=hwnd)
        except Exception as e:
            print(f"[PywinautoBot] Failed to connect to HWND {hwnd}: {e}")
            return None

    # ==================== Window Management ====================

    def get_window(
        self,
        title: Optional[str] = None,
        class_name: Optional[str] = None,
        process: Optional[int] = None,
    ) -> Any:
        """
        Find a window by title, class_name, or process ID.

        Args:
            title: Window title (partial or full match).
            class_name: Window class name.
            process: Process ID.

        Returns:
            Window wrapper object.

        Raises:
            WindowNotFoundError: If window is not found.

        Example:
            >>> window = bot.get_window(title="Notepad")
            >>> window = bot.get_window(class_name="Notepad")
        """
        try:
            app = self._ensure_app()

            if process:
                window = app.window(process=process)
            elif title and class_name:
                window = app.window(title=title, class_name=class_name)
            elif title:
                window = app.window(title=title)
            elif class_name:
                window = app.window(class_name=class_name)
            else:
                raise PywinautoError(
                    "At least one of title, class_name, or process must be provided"
                )

            # Verify window exists
            if not window.exists():
                raise WindowNotFoundError(
                    f"Window not found: title='{title}', class_name='{class_name}', process={process}"
                )

            self.current_window = window
            return window

        except WindowNotFoundError:
            raise
        except Exception as e:
            raise PywinautoError(f"Error finding window: {e}")

    def wait_window(self, title: str, timeout: float = 10) -> Any:
        """
        Wait for a window to appear and return it.

        Args:
            title: Window title to wait for.
            timeout: Maximum time to wait in seconds.

        Returns:
            Window wrapper object.

        Raises:
            WindowNotFoundError: If window doesn't appear within timeout.

        Example:
            >>> window = bot.wait_window("Download Complete", timeout=15)
        """
        start_time = time.time()
        last_error = None

        while time.time() - start_time < timeout:
            try:
                return self.get_window(title=title)
            except WindowNotFoundError as e:
                last_error = e
                time.sleep(0.2)
            except Exception as e:
                last_error = e
                time.sleep(0.2)

        raise WindowNotFoundError(
            f"Window '{title}' not found within {timeout} seconds. Last error: {last_error}"
        )

    def list_windows(
        self, title: Optional[str] = None, class_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all visible windows, optionally filtered by title or class_name.

        Args:
            title: Optional title filter (partial match).
            class_name: Optional class name filter.

        Returns:
            List of dictionaries containing window information.

        Example:
            >>> windows = bot.list_windows()
            >>> for w in windows:
            ...     print(f"{w['title']} - {w['class_name']}")
        """
        try:
            criteria = {}
            if title:
                criteria["title"] = title
            if class_name:
                criteria["class_name"] = class_name

            windows = findwindows.find_windows(**criteria, visible_only=True)

            result = []
            for hwnd in windows:
                try:
                    win = findwindows.find_window(hwnd=hwnd)
                    info = {
                        "hwnd": hwnd,
                        "title": win.window_text(),
                        "class_name": win.class_name(),
                    }

                    # Add to result if it has a title (visible window)
                    if info["title"]:
                        result.append(info)
                except:
                    continue

            return result

        except Exception as e:
            raise PywinautoError(f"Error listing windows: {e}")

    def close_window(self, window: Any) -> bool:
        """
        Close a window.

        Args:
            window: Window wrapper object.

        Returns:
            True if successful.

        Raises:
            PywinautoError: If closing fails.

        Example:
            >>> bot.close_window(window)
        """
        try:
            window.close()
            return True
        except Exception as e:
            raise PywinautoError(f"Error closing window: {e}")

    def minimize_window(self, window: Any) -> bool:
        """
        Minimize a window.

        Args:
            window: Window wrapper object.

        Returns:
            True if successful.

        Example:
            >>> bot.minimize_window(window)
        """
        try:
            window.minimize()
            return True
        except Exception as e:
            raise PywinautoError(f"Error minimizing window: {e}")

    def maximize_window(self, window: Any) -> bool:
        """
        Maximize a window.

        Args:
            window: Window wrapper object.

        Returns:
            True if successful.

        Example:
            >>> bot.maximize_window(window)
        """
        try:
            window.maximize()
            return True
        except Exception as e:
            raise PywinautoError(f"Error maximizing window: {e}")

    def restore_window(self, window: Any) -> bool:
        """
        Restore a minimized or maximized window to normal size.

        Args:
            window: Window wrapper object.

        Returns:
            True if successful.

        Example:
            >>> bot.restore_window(window)
        """
        try:
            window.restore()
            return True
        except Exception as e:
            raise PywinautoError(f"Error restoring window: {e}")

    def get_window_info(self, window: Any) -> Dict[str, Any]:
        """
        Get detailed information about a window.

        Args:
            window: Window wrapper object.

        Returns:
            Dictionary containing:
                - title: Window title
                - class_name: Window class name
                - process_id: Process ID
                - rectangle: Window position and size (left, top, right, bottom)
                - width: Window width
                - height: Window height
                - is_visible: Whether window is visible
                - is_enabled: Whether window is enabled

        Example:
            >>> info = bot.get_window_info(window)
            >>> print(f"Title: {info['title']}, Size: {info['width']}x{info['height']}")
        """
        try:
            rect = window.rectangle()

            return {
                "title": window.window_text(),
                "class_name": window.class_name(),
                "process_id": window.process_id(),
                "rectangle": (rect.left, rect.top, rect.right, rect.bottom),
                "width": rect.width(),
                "height": rect.height(),
                "is_visible": window.is_visible(),
                "is_enabled": window.is_enabled(),
            }
        except Exception as e:
            raise PywinautoError(f"Error getting window info: {e}")

    # ==================== Element Interaction ====================

    def _find_control(
        self, window: Any, control_type: Optional[str], identifier: str
    ) -> Any:
        """
        Find a control within a window.

        Args:
            window: Window wrapper object.
            control_type: Type of control (e.g., "Button", "Edit", "ComboBox"). Can be None.
            identifier: Control identifier (text, ID, or auto-id).

        Returns:
            Control wrapper object.

        Raises:
            ElementNotFoundError: If control is not found.
        """
        try:
            # Try different methods to find the control
            methods = [
                lambda: window[identifier],
                lambda: (
                    window.child_window(title=identifier, control_type=control_type)
                    if control_type
                    else window.child_window(title=identifier)
                ),
                lambda: (
                    window[control_type + identifier]
                    if control_type
                    else window[identifier]
                ),
            ]

            for method in methods:
                try:
                    ctrl = method()
                    if ctrl.exists(timeout=1):
                        return ctrl
                except:
                    continue

            # Try using best match
            try:
                ctrl = window[identifier]
                if ctrl.exists(timeout=1):
                    return ctrl
            except:
                pass

            raise ElementNotFoundError(
                f"Control not found: type='{control_type}', identifier='{identifier}'"
            )

        except ElementNotFoundError:
            raise
        except Exception as e:
            raise ElementNotFoundError(
                f"Error finding control: type='{control_type}', identifier='{identifier}'. {e}"
            )

    def click_element(
        self,
        window: Any,
        control_type: str,
        identifier: str,
        double_click: bool = False,
    ) -> bool:
        """
        Click a button or other control element.

        Args:
            window: Window wrapper object.
            control_type: Type of control (e.g., "Button", "RadioButton").
            identifier: Control identifier (text, ID, or auto-id).
            double_click: Whether to double-click instead of single click.

        Returns:
            True if successful.

        Example:
            >>> bot.click_element(window, "Button", "OK")
            >>> bot.click_element(window, "Button", "Submit", double_click=True)
        """
        try:
            ctrl = self._find_control(window, control_type, identifier)

            if double_click:
                ctrl.double_click_input()
            else:
                ctrl.click_input()

            return True

        except ElementNotFoundError:
            raise
        except Exception as e:
            raise PywinautoError(f"Error clicking element: {e}")

    def type_into(
        self, window: Any, control_identifier: str, text: str, clear_first: bool = True
    ) -> bool:
        """
        Type text into an edit field or other text input control.

        Args:
            window: Window wrapper object.
            control_identifier: Control identifier (text, ID, or auto-id).
            text: Text to type.
            clear_first: Whether to clear the field before typing.

        Returns:
            True if successful.

        Example:
            >>> bot.type_into(window, "Edit", "Hello World")
            >>> bot.type_into(window, "username", "myuser", clear_first=True)
        """
        try:
            ctrl = self._find_control(window, "Edit", control_identifier)

            if clear_first:
                ctrl.clear()

            ctrl.set_edit_text(text)
            return True

        except ElementNotFoundError:
            raise
        except Exception as e:
            raise PywinautoError(f"Error typing into element: {e}")

    def get_text(self, window: Any, control_identifier: str) -> str:
        """
        Get text from a control (edit field, static text, etc.).

        Args:
            window: Window wrapper object.
            control_identifier: Control identifier (text, ID, or auto-id).

        Returns:
            The text content of the control.

        Example:
            >>> text = bot.get_text(window, "Edit1")
            >>> print(text)
        """
        try:
            ctrl = self._find_control(window, None, control_identifier)
            return ctrl.window_text()

        except ElementNotFoundError:
            raise
        except Exception as e:
            raise PywinautoError(f"Error getting text: {e}")

    def select_dropdown(
        self, window: Any, control_identifier: str, value: str, by_index: bool = False
    ) -> bool:
        """
        Select a value from a dropdown (ComboBox) control.

        Args:
            window: Window wrapper object.
            control_identifier: ComboBox control identifier.
            value: Value to select (text or index).
            by_index: If True, treat value as index number instead of text.

        Returns:
            True if successful.

        Example:
            >>> bot.select_dropdown(window, "ComboBox", "Option 1")
            >>> bot.select_dropdown(window, "DropDown", 2, by_index=True)
        """
        try:
            ctrl = self._find_control(window, "ComboBox", control_identifier)

            if by_index:
                ctrl.select(int(value))
            else:
                ctrl.select(value)

            return True

        except ElementNotFoundError:
            raise
        except Exception as e:
            raise PywinautoError(f"Error selecting dropdown: {e}")

    def check_checkbox(
        self, window: Any, control_identifier: str, state: Optional[bool] = None
    ) -> bool:
        """
        Check or uncheck a checkbox control.

        Args:
            window: Window wrapper object.
            control_identifier: Checkbox control identifier.
            state: True to check, False to uncheck. If None, toggles current state.

        Returns:
            True if successful.

        Example:
            >>> bot.check_checkbox(window, "Remember Me", True)  # Check
            >>> bot.check_checkbox(window, "Remember Me", False) # Uncheck
            >>> bot.check_checkbox(window, "Remember Me")       # Toggle
        """
        try:
            ctrl = self._find_control(window, "CheckBox", control_identifier)

            if state is None:
                # Toggle
                ctrl.toggle()
            elif state:
                ctrl.check()
            else:
                ctrl.uncheck()

            return True

        except ElementNotFoundError:
            raise
        except Exception as e:
            raise PywinautoError(f"Error checking checkbox: {e}")

    # ==================== Window Information ====================

    def get_all_controls(
        self, window: Any, include_disabled: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get a tree of all controls within a window.

        This is useful for exploring the UI structure and finding control identifiers.

        Args:
            window: Window wrapper object.
            include_disabled: Whether to include disabled controls.

        Returns:
            List of dictionaries containing control information:
                - control_type: Type of control
                - text: Control text/label
                - control_id: Control identifier
                - enabled: Whether control is enabled
                - visible: Whether control is visible

        Example:
            >>> controls = bot.get_all_controls(window)
            >>> for ctrl in controls[:10]:  # Print first 10
            ...     print(f"{ctrl['control_type']}: {ctrl['text']}")
        """
        try:
            controls = []

            # Get all children recursively
            def get_children(parent, depth=0):
                try:
                    children = parent.children()
                    for child in children:
                        try:
                            # Skip if disabled and not requested
                            if not include_disabled and not child.is_enabled():
                                continue

                            ctrl_info = {
                                "control_type": child.friendly_class_name(),
                                "text": child.window_text(),
                                "control_id": (
                                    child.control_id()
                                    if hasattr(child, "control_id")
                                    else None
                                ),
                                "enabled": child.is_enabled(),
                                "visible": child.is_visible(),
                                "depth": depth,
                            }
                            controls.append(ctrl_info)

                            # Recurse
                            if depth < 5:  # Limit depth to avoid too deep recursion
                                get_children(child, depth + 1)
                        except:
                            continue
                except:
                    pass

            get_children(window)
            return controls

        except Exception as e:
            raise PywinautoError(f"Error getting controls: {e}")

    def print_control_tree(self, window: Any, max_depth: int = 3) -> None:
        """
        Print a formatted tree of controls for debugging/ exploration.

        Args:
            window: Window wrapper object.
            max_depth: Maximum depth to traverse.

        Example:
            >>> bot.print_control_tree(window)
        """
        try:

            def print_children(parent, depth=0):
                if depth > max_depth:
                    return

                try:
                    children = parent.children()
                    for child in children:
                        try:
                            indent = "  " * depth
                            ctrl_type = child.friendly_class_name()
                            text = child.window_text()
                            text_str = f" - '{text}'" if text else ""
                            print(f"{indent}{ctrl_type}{text_str}")
                            print_children(child, depth + 1)
                        except:
                            continue
                except:
                    pass

            print(f"\n=== Control Tree for: {window.window_text()} ===\n")
            print_children(window)
            print("\n" + "=" * 50)

        except Exception as e:
            raise PywinautoError(f"Error printing control tree: {e}")

    # ==================== Utility Methods ====================

    def connect_to_app(self, process_id: int) -> Any:
        """
        Connect to an existing application by process ID.

        Args:
            process_id: The process ID of the application.

        Returns:
            Window wrapper for the application's main window.

        Example:
            >>> # First get process ID from task manager or list_windows
            >>> window = bot.connect_to_app(1234)
        """
        try:
            app = Application(backend=self._backend).connect(process=process_id)
            self.app = app
            window = app.top_window()
            self.current_window = window
            return window

        except Exception as e:
            raise PywinautoError(f"Error connecting to app (PID {process_id}): {e}")

    def start_app(self, path: str, arguments: str = "") -> Any:
        """
        Start an application and return its main window.

        Args:
            path: Path to the executable.
            arguments: Command line arguments (optional).

        Returns:
            Window wrapper for the application's main window.

        Example:
            >>> window = bot.start_app("C:\\Windows\\notepad.exe")
        """
        try:
            if arguments:
                app = Application(backend=self._backend).start(f'"{path}" {arguments}')
            else:
                app = Application(backend=self._backend).start(f'"{path}"')

            self.app = app
            window = app.top_window()
            self.current_window = window
            return window

        except Exception as e:
            raise PywinautoError(f"Error starting app '{path}': {e}")

    def wait_for_element(
        self, window: Any, control_identifier: str, timeout: float = 10
    ) -> Any:
        """
        Wait for a control to become visible and return it.

        Args:
            window: Window wrapper object.
            control_identifier: Control identifier.
            timeout: Maximum time to wait in seconds.

        Returns:
            Control wrapper object.

        Raises:
            ElementNotFoundError: If element doesn't appear within timeout.

        Example:
            >>> ctrl = bot.wait_for_element(window, "LoadingSpinner", timeout=15)
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                ctrl = self._find_control(window, None, control_identifier)
                if ctrl.exists() and ctrl.is_visible():
                    return ctrl
            except:
                pass
            time.sleep(0.2)

        raise ElementNotFoundError(
            f"Element '{control_identifier}' not found within {timeout} seconds"
        )

    def send_hotkey(self, window: Any, *keys: str) -> bool:
        """
        Send a hotkey combination to a window.

        Args:
            window: Window wrapper object.
            *keys: Keys to press (e.g., "ctrl", "c", "alt", "f4").

        Returns:
            True if successful.

        Example:
            >>> bot.send_hotkey(window, "ctrl", "c")   # Copy
            >>> bot.send_hotkey(window, "alt", "f4")   # Close
            >>> bot.send_hotkey(window, "ctrl", "v")   # Paste
        """
        try:
            window.set_focus()
            window.type_keys("+".join(keys), with_spaces=True)
            return True
        except Exception as e:
            raise PywinautoError(f"Error sending hotkey: {e}")

    def get_focused_element_info(self, window: Any) -> Dict[str, Any]:
        """
        Get information about the currently focused control.

        Args:
            window: Window wrapper object.

        Returns:
            Dictionary with focused element information.

        Example:
            >>> info = bot.get_focused_element_info(window)
            >>> print(f"Focused: {info['control_type']} - {info['text']}")
        """
        try:
            focused = window.get_focus()
            return {
                "control_type": focused.friendly_class_name(),
                "text": focused.window_text(),
                "control_id": (
                    focused.control_id() if hasattr(focused, "control_id") else None
                ),
            }
        except Exception as e:
            raise PywinautoError(f"Error getting focused element: {e}")

    def screenshot(self, window: Any, filepath: str) -> bool:
        """
        Take a screenshot of a window.

        Args:
            window: Window wrapper object.
            filepath: Path to save the screenshot.

        Returns:
            True if successful.

        Example:
            >>> bot.screenshot(window, "C:\\screenshot.png")
        """
        try:
            window.capture_as_image().save(filepath)
            return True
        except Exception as e:
            raise PywinautoError(f"Error taking screenshot: {e}")


# Standalone function for quick access when pywinauto might not be available
def create_bot(backend: str = "win32") -> Optional[PywinautoBot]:
    """
    Create a PywinautoBot instance if pywinauto is available.

    Args:
        backend: The backend to use ("win32" or "uia").

    Returns:
        PywinautoBot instance or None if pywinauto is not available.

    Example:
        >>> bot = create_bot()
        >>> if bot:
        ...     window = bot.wait_window("Notepad")
        ... else:
        ...     print("pywinauto not available")
    """
    if not PYWINAUTO_AVAILABLE:
        return None

    return PywinautoBot(backend=backend)
