import time
import numpy as np
import ctypes
import random
from ctypes import wintypes

try:
    import cv2
except ImportError:
    cv2 = None

# --- CRITICAL: Set DPI Awareness BEFORE any other UI/GDI calls ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
except:
    pass

try:
    import win32gui
except ImportError:
    win32gui = None

try:
    from windows_utils import _get_true_hwnd_rect
except ImportError:
    from core.windows_utils import _get_true_hwnd_rect

try:
    from bot import Bot
except ImportError:
    from core.bot import Bot

try:
    from pywinauto_api import PywinautoBot, is_pywinauto_available
except ImportError:
    from core.pywinauto_api import PywinautoBot, is_pywinauto_available


class ScriptStoppedError(BaseException):
    """Custom exception raised when the script execution is stopped."""
    pass


class GUIProxy:
    """Proxy class that mimics the old bot.gui interface for embedded regions support."""

    def __init__(self, bot_api):
        self._bot = bot_api
        self._regions = []

    @property
    def regions(self):
        return self._regions

    @regions.setter
    def regions(self, value):
        """Set regions - converts to proper format and updates bot."""
        if isinstance(value, list):
            self._regions = []
            for r in value:
                # Ensure required fields exist
                if all(k in r for k in ["x", "y", "width", "height"]):
                    self._regions.append(
                        {
                            "x": r.get("x", 0),
                            "y": r.get("y", 0),
                            "width": r.get("width", 0),
                            "height": r.get("height", 0),
                            "color": r.get(
                                "color", "#FFFF00"
                            ),  # Default yellow if not specified
                            "name": r.get("name", f"Region {len(self._regions)}"),
                        }
                    )
            # Sync to the bot's region list
            self._bot.set_regions(self._regions)

    def update_region_selector(self):
        """Log that region selector was updated."""
        self._bot.log(
            f"Updated region selector with {len(self._regions)} embedded regions"
        )


def hex_to_bgr(hex_str):
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 3:
        hex_str = ''.join(c * 2 for c in hex_str)
    r = int(hex_str[0:2], 16)
    g = int(hex_str[2:4], 16)
    b = int(hex_str[4:6], 16)
    return (b, g, r)


class DynamicRegion:
    def __init__(self, bot, label_id, stats, centroid, mask, offset_x, offset_y):
        self.bot = bot
        self.label_id = label_id
        self._stats = stats          # [left, top, width, height, area]
        self._centroid = centroid    # (cx, cy)
        self._mask = mask            # binary mask of this component (cropped to bounding box)
        self._offset_x = offset_x
        self._offset_y = offset_y
        
    def center(self):
        """Returns absolute screen coordinates of the component centroid."""
        left, top, _, _ = _get_true_hwnd_rect(self.bot._target_hwnd)
        cx = left + self._offset_x + self._centroid[0]
        cy = top + self._offset_y + self._centroid[1]
        return int(cx), int(cy)
        
    def click(self, button="left", human_like=True):
        """Clicks the centroid of the component."""
        cx, cy = self.center()
        self.bot.click(cx, cy, button=button, human_like=human_like)
        
    def bounds(self):
        """Returns (x, y, w, h) client-relative bounding box."""
        return (
            int(self._offset_x + self._stats[0]), 
            int(self._offset_y + self._stats[1]), 
            int(self._stats[2]), 
            int(self._stats[3])
        )
        
    def area(self):
        """Returns total area of matching pixels in this component."""
        return int(self._stats[4])
        
    def mask(self):
        """Returns the binary mask of this component."""
        return self._mask

    def contains(self, hex_color, tolerance=25):
        """Checks if this component contains a specific color."""
        left, top, w, h, _ = self._stats
        b, g, r = hex_to_bgr(hex_color)
        
        full_frame = self.bot._get_current_frame()
        if full_frame is None:
            return False
            
        if full_frame.shape[2] == 4:
            img_bgr = cv2.cvtColor(full_frame, cv2.COLOR_BGRA2BGR)
        else:
            img_bgr = cv2.cvtColor(full_frame, cv2.COLOR_RGB2BGR)
            
        gx = self._offset_x + left
        gy = self._offset_y + top
        
        bgr_crop = img_bgr[gy : gy + h, gx : gx + w]
        
        lower = np.array([max(0, b - tolerance), max(0, g - tolerance), max(0, r - tolerance)], dtype=np.uint8)
        upper = np.array([min(255, b + tolerance), min(255, g + tolerance), min(255, r + tolerance)], dtype=np.uint8)
        color_mask = cv2.inRange(bgr_crop, lower, upper)
        
        intersection = cv2.bitwise_and(color_mask, color_mask, mask=self._mask)
        return cv2.countNonZero(intersection) > 0

    def save(self, filepath):
        """Saves a crop of this component to a file."""
        left, top, w, h, _ = self._stats
        full_frame = self.bot._get_current_frame()
        if full_frame is None:
            return False
            
        gx = self._offset_x + left
        gy = self._offset_y + top
        crop = full_frame[gy : gy + h, gx : gx + w].copy()
        
        cv2.imwrite(filepath, crop)
        return True

    def highlight(self, duration_sec=1.5):
        """Logs high-level information about the highlighted region."""
        self.bot.log(f"[Highlight] DynamicRegion at center {self.center()} with bounds {self.bounds()}")


class BotAPI:
    def __init__(self, gui_instance=None):
        # Use GUIProxy if no gui_instance provided, otherwise use the provided instance
        if gui_instance is None:
            self.gui = GUIProxy(self)
        else:
            self.gui = gui_instance
        self._is_running = True
        self._debug_mode = False
        self.bot = Bot()
        self.win = PywinautoBot() if is_pywinauto_available() else None
        self._last_frame = None
        self.regions = []
        self._color_clusters = []
        self._target_hwnd = None
        self.on_log = None
        self._template_cache = {}
        self._tesseract_available = None
        self._tesseract_error = None
        self._frame_counter = 0
        self._ccl_cache = {}
        self._ocr_cache = {}

    def set_regions(self, regions):
        self.regions = regions

    def set_color_clusters(self, clusters):
        self._color_clusters = clusters

    def set_target_window(self, hwnd):
        self._target_hwnd = hwnd

    def set_frame_buffer(self, buffer):
        self._last_frame = buffer
        self._frame_counter += 1
        self._ccl_cache = {}

    def check_running(self):
        """Raises ScriptStoppedError if the script is no longer running."""
        if not self._is_running:
            raise ScriptStoppedError("Script stopped by user")

    # --- High-Level Window Automation (Pywinauto) ---

    def _get_active_app_window(self):
        self.check_running()
        if not self.win or not self._target_hwnd:
            return None
        return self.win.get_app(self._target_hwnd)

    def click_element(self, identifier, control_type="Button", double_click=False):
        window = self._get_active_app_window()
        if not window:
            self.log("Error: No target window set for element interaction.")
            return False
        try:
            success = self.win.click_element(
                window, control_type, identifier, double_click
            )
            if success:
                self.log(f"Clicked {control_type} '{identifier}'")
            return success
        except Exception as e:
            self.log(f"Element Error: {e}")
            return False

    def type_into(self, identifier, text, clear_first=True):
        window = self._get_active_app_window()
        if not window:
            self.log("Error: No target window set for typing.")
            return False
        try:
            success = self.win.type_into(window, identifier, text, clear_first)
            if success:
                self.log(f"Typed into '{identifier}'")
            return success
        except Exception as e:
            self.log(f"Type Error: {e}")
            return False

    def type_text(self, text, delay=0.05, press_enter=False):
        self.check_running()
        try:
            self.bot.type_text(text, delay=delay)
            if press_enter:
                self.bot.press_key("enter")
            self.log(f"Typed raw text: '{text}'")
            return True
        except Exception as e:
            self.log(f"Type Text Error: {e}")
            return False

    def get_text(self, identifier):
        window = self._get_active_app_window()
        if not window:
            self.log("Error: No target window set for get_text.")
            return None
        try:
            text = self.win.get_text(window, identifier)
            self.log(f"Got text from '{identifier}': {text}")
            return text
        except Exception as e:
            self.log(f"Get Text Error: {e}")
            return None

    def select_dropdown(self, identifier, value, by_index=False):
        window = self._get_active_app_window()
        if not window:
            self.log("Error: No target window set for select_dropdown.")
            return False
        try:
            success = self.win.select_dropdown(window, identifier, value, by_index)
            if success:
                self.log(f"Selected '{value}' in dropdown '{identifier}'")
            return success
        except Exception as e:
            self.log(f"Dropdown Error: {e}")
            return False

    def check_checkbox(self, identifier, state=None):
        window = self._get_active_app_window()
        if not window:
            self.log("Error: No target window set for check_checkbox.")
            return False
        try:
            success = self.win.check_checkbox(window, identifier, state)
            if success:
                state_str = (
                    "Toggled"
                    if state is None
                    else ("Checked" if state else "Unchecked")
                )
                self.log(f"{state_str} checkbox '{identifier}'")
            return success
        except Exception as e:
            self.log(f"Checkbox Error: {e}")
            return False

    def wait_for_element(self, identifier, timeout=10):
        window = self._get_active_app_window()
        if not window:
            self.log("Error: No target window set for wait_for_element.")
            return False
        try:
            ctrl = self.win.wait_for_element(window, identifier, timeout)
            if ctrl:
                self.log(f"Element '{identifier}' is now visible.")
                return True
            return False
        except Exception as e:
            self.log(f"Wait Element Error: {e}")
            return False

    def send_hotkey(self, *keys):
        self.check_running()
        if not self._target_hwnd:
            self.log("Error: No target window set.")
            return False
        # Check if window still exists
        if win32gui and not win32gui.IsWindow(self._target_hwnd):
            self.log("Error: Target window no longer exists.")
            self._target_hwnd = None
            return False

        window = self._get_active_app_window()
        if not window:
            self.log("Error: Could not get window for send_hotkey.")
            return False
        try:
            success = self.win.send_hotkey(window, *keys)
            if success:
                self.log(f"Sent hotkey: {'+'.join(keys)}")
            return success
        except Exception as e:
            self.log(f"Hotkey Error: {e}")
            return False

    def wait_window(self, title, timeout=10):
        self.check_running()
        if not self.win:
            return False
        try:
            window = self.win.wait_window(title, timeout)
            if window:
                self._target_hwnd = window.handle
                self.log(f"Found and focused window: {title}")
                return True
        except Exception as e:
            self.log(f"Wait Error: {e}")
            return False

    # --- Low-Level / Vision Logic ---

    def _get_current_frame(self):
        """Returns the shared memory frame if available, else grabs a new one."""
        # Check if window is still valid
        if self._target_hwnd and win32gui and not win32gui.IsWindow(self._target_hwnd):
            self.log("Warning: Target window no longer exists in _get_current_frame")
            self._target_hwnd = None
            return None

        if self._last_frame is not None:
            if self._debug_mode:
                self.log(f"Using shared memory frame: {self._last_frame.shape}")
            return self._last_frame

        from PIL import ImageGrab

        if self._target_hwnd:
            try:
                left, top, right, bottom = _get_true_hwnd_rect(self._target_hwnd)
                if self._debug_mode:
                    self.log(
                        f"Grabbing window frame: ({left}, {top}, {right}, {bottom})"
                    )
                img = ImageGrab.grab(bbox=(left, top, right, bottom))
                return np.array(img)
            except Exception as e:
                self.log(f"Error grabbing window frame: {e}")
                return None

        if self._debug_mode:
            self.log("Grabbing full screen frame (no target window)")
        return np.array(ImageGrab.grab())

    def get_window_rect(self):
        if not self._target_hwnd:
            return None
        try:
            from core.windows_utils import _get_true_hwnd_rect
            return _get_true_hwnd_rect(self._target_hwnd)
        except Exception:
            try:
                from windows_utils import _get_true_hwnd_rect
                return _get_true_hwnd_rect(self._target_hwnd)
            except Exception:
                return None

    def screen_to_client(self, x, y):
        """Converts absolute screen coordinates to client-relative coordinates."""
        rect = self.get_window_rect()
        if rect:
            left, top, _, _ = rect
            return x - left, y - top
        return x, y

    def client_to_screen(self, x, y):
        """Converts client-relative coordinates to absolute screen coordinates."""
        rect = self.get_window_rect()
        if rect:
            left, top, _, _ = rect
            return left + x, top + y
        return x, y

    @property
    def is_running(self):
        return self._is_running

    @is_running.setter
    def is_running(self, value):
        self._is_running = value

    def focus_window(self):
        if not win32gui or not self._target_hwnd:
            return
        try:
            # Check if window still exists
            if not win32gui.IsWindow(self._target_hwnd):
                self.log("Error: Target window no longer exists")
                self._target_hwnd = None
                return

            # Check if already focused
            if win32gui.GetForegroundWindow() == self._target_hwnd:
                return

            # ShowWindow constants
            SW_RESTORE = 9
            win32gui.ShowWindow(self._target_hwnd, SW_RESTORE)

            # Use the Alt key trick to bypass focus restrictions
            import ctypes

            self.bot.press_key("alt")

            win32gui.SetForegroundWindow(self._target_hwnd)
            time.sleep(0.2)
        except Exception as e:
            self.log(f"Focus Error: {e}")

    def wait(self, seconds):
        """Wait for the specified number of seconds, checking if the bot is still running."""
        chunk_size = 0.1
        total_waited = 0
        while total_waited < seconds:
            self.check_running()
            remaining = seconds - total_waited
            wait_time = min(chunk_size, remaining)
            time.sleep(wait_time)
            total_waited += wait_time
        self.check_running()

    def log(self, message):
        if self.on_log:
            self.on_log(message)
        else:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] {message}")

    def click_region(self, region_index, button="left", modifiers=None, human_like=False):
        if modifiers is None:
            modifiers = []
        self.check_running()
        if region_index >= len(self.regions):
            self.log(
                f"Error: Region {region_index} does not exist. Total regions: {len(self.regions)}"
            )
            return False
        if not self._target_hwnd:
            self.log("Error: No target window set or window was closed.")
            return False

        # Check if window still exists before trying to interact
        if win32gui and not win32gui.IsWindow(self._target_hwnd):
            self.log("Error: Target window no longer exists.")
            self._target_hwnd = None
            return False

        region = self.regions[region_index]

        try:
            left, top, _, _ = _get_true_hwnd_rect(self._target_hwnd)
            x = left + region["x"] + region["width"] // 2
            y = top + region["y"] + region["height"] // 2

            self.log(f"Clicking region[{region_index}] center -> screen({x},{y})")

            if human_like:
                self.bot.human_move_to(x, y)
                self.bot.click(x, y, button, modifiers)
            else:
                self.bot.click(x, y, button, modifiers)
            self.log(f"Clicked region {region_index} at ({x}, {y})")
            return True
        except Exception as e:
            self.log(f"Error in click_region: {e}")
            import traceback

            self.log(f"Stack: {traceback.format_exc()}")
            return False

    def scroll(self, clicks, x=None, y=None):
        """Scrolls the mouse wheel by the given amount."""
        self.check_running()
        try:
            self.bot.scroll(clicks, x, y)
            self.log(f"Scrolled {clicks} clicks at {x}, {y}")
            return True
        except Exception as e:
            self.log(f"Scroll Error: {e}")
            return False

    def key_down(self, key):
        """Presses and holds a keyboard key."""
        self.check_running()
        try:
            self.bot.key_down(key)
            self.log(f"Key down: {key}")
            return True
        except Exception as e:
            self.log(f"Key Down Error: {e}")
            return False

    def key_up(self, key):
        """Releases a keyboard key."""
        self.check_running()
        try:
            self.bot.key_up(key)
            self.log(f"Key up: {key}")
            return True
        except Exception as e:
            self.log(f"Key Up Error: {e}")
            return False

    def double_click(self, x, y, button="left", modifiers=None, human_like=False):
        """Performs a double mouse click at the specified coordinates."""
        if modifiers is None:
            modifiers = []
        self.check_running()
        try:
            if human_like:
                self.bot.human_move_to(x, y)
                self.bot.double_click(x, y, button, modifiers)
            else:
                self.bot.double_click(x, y, button, modifiers)
            self.log(f"Double clicked coordinates ({x}, {y})")
            return True
        except Exception as e:
            self.log(f"Error in double_click: {e}")
            import traceback

            self.log(f"Stack: {traceback.format_exc()}")
            return False

    def press_button(self, button="left", down=True):
        """Presses or releases a mouse button."""
        self.check_running()
        try:
            self.bot.press_button(button, down)
            action = "pressed" if down else "released"
            self.log(f"Mouse button {button} {action}")
            return True
        except Exception as e:
            self.log(f"Press Button Error: {e}")
            return False

    def click(self, x, y, button="left", modifiers=None, human_like=False):
        """Clicks at the specified coordinates, supporting optional modifiers and human-like movement."""
        if modifiers is None:
            modifiers = []
        self.check_running()

        try:
            if human_like:
                self.bot.human_move_to(x, y)
                self.bot.click(x, y, button, modifiers)
            else:
                self.bot.click(x, y, button, modifiers)
            self.log(f"Clicked coordinates ({x}, {y})")
            return True
        except Exception as e:
            self.log(f"Error in click: {e}")
            import traceback

            self.log(f"Stack: {traceback.format_exc()}")
            return False

    def find_color(self, hex_color, region_index, tolerance=10):
        self.check_running()
        if region_index >= len(self.regions):
            self.log(
                f"Error: Region {region_index} does not exist. Total regions: {len(self.regions)}"
            )
            return None
        if not self._target_hwnd:
            self.log("Error: No target window set or window was closed.")
            return None

        region = self.regions[region_index]

        # Parse target color
        try:
            target_rgb = tuple(
                int(hex_color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)
            )
        except Exception as e:
            self.log(f"Error: Invalid hex color '{hex_color}': {e}")
            return None

        # Check if window still exists before trying to interact
        import win32gui

        if win32gui and not win32gui.IsWindow(self._target_hwnd):
            self.log("Error: Target window no longer exists.")
            self._target_hwnd = None
            return None

        self.focus_window()

        try:
            full_frame = self._get_current_frame()
            if full_frame is None:
                self.log("Vision Error: Could not get screen frame.")
                return None

            # Get region bounds
            x, y, w, h = region["x"], region["y"], region["width"], region["height"]

            # Validate ROI is within frame bounds
            frame_h, frame_w = full_frame.shape[:2]
            if x < 0 or y < 0 or x + w > frame_w or y + h > frame_h:
                self.log(
                    f"Error: Region {region_index} bounds ({x},{y},{w},{h}) outside frame ({frame_w}x{frame_h})"
                )
                return None

            roi = full_frame[y : y + h, x : x + w]

            if roi.size == 0:
                self.log(f"Error: Empty ROI for region {region_index}")
                return None

            # ROI is BGRA from Shared Memory or RGB from ImageGrab
            if roi.shape[2] == 4:  # BGRA
                roi_rgb = roi[:, :, [2, 1, 0]]
            else:
                roi_rgb = roi

            # Calculate color differences
            color_diff = np.abs(roi_rgb - target_rgb)
            matches = np.where(np.all(color_diff <= tolerance, axis=2))

            if len(matches[0]) > 0:
                # Get FIRST match (top-left most)
                rel_y, rel_x = matches[0][0], matches[1][0]

                # Calculate absolute screen coordinates
                left, top, _, _ = _get_true_hwnd_rect(self._target_hwnd)
                abs_x = left + region["x"] + rel_x
                abs_y = top + region["y"] + rel_y

                # Get actual pixel color at click location for debugging
                actual_color = roi_rgb[rel_y, rel_x]

                self.log(
                    f"[{hex_color}] Found at region[{region_index}] offset({rel_x},{rel_y}) -> screen({abs_x},{abs_y}) | actual RGB: {actual_color}"
                )

                return abs_x, abs_y
            else:
                # Log what colors ARE in the region for debugging
                if roi_rgb.size > 0:
                    avg_color = np.mean(roi_rgb.reshape(-1, 3), axis=0)
                    min_color = np.min(roi_rgb.reshape(-1, 3), axis=0)
                    max_color = np.max(roi_rgb.reshape(-1, 3), axis=0)
                    self.log(
                        f"[{hex_color}] NOT found in region[{region_index}]. RGB range: {min_color}-{max_color}, avg: {avg_color}"
                    )
                else:
                    self.log(
                        f"[{hex_color}] NOT found in region[{region_index}] (empty region)"
                    )
                return None
        except Exception as e:
            self.log(f"Error in find_color: {e}")
            import traceback

            self.log(f"Stack: {traceback.format_exc()}")
            return None

    def find_and_click_color(
        self,
        hex_color,
        region_index,
        button="left",
        modifiers=None,
        tolerance=10,
        human_like=False,
    ):
        if modifiers is None:
            modifiers = []
        self.check_running()
        result = self.find_color(hex_color, region_index, tolerance)
        if result:
            abs_x, abs_y = result
            if human_like:
                self.bot.human_move_to(abs_x, abs_y)
                self.bot.click(abs_x, abs_y, button, modifiers)
            else:
                self.bot.click(abs_x, abs_y, button, modifiers)
            return True
        return False

    def get_pixel_color(self, x, y):
        return self.get_pixel_color_fast(x, y)

    def move_mouse(self, x, y, human_like=True):
        self.check_running()
        if human_like:
            self.bot.human_move_to(x, y)
        else:
            self.bot.move_to(x, y)

    def get_mouse_position(self):
        return self.bot.get_cursor_pos()

    def wait_for_color(self, hex_color, region_index, timeout=10, tolerance=10):
        self.check_running()
        start_time = time.time()
        while time.time() - start_time < timeout:
            self.check_running()
            if self.find_color(hex_color, region_index, tolerance):
                return True
            self.wait(0.1)
        self.log(
            f"Timeout: Color {hex_color} not found in region {region_index} after {timeout} seconds."
        )
        return False

    def hover_color(self, hex_color, region_index, tolerance=10, human_like=True):
        result = self.find_color(hex_color, region_index, tolerance)
        if result:
            abs_x, abs_y = result
            self.move_mouse(abs_x, abs_y, human_like)
            return True
        return False

    def hover_image(
        self, template_path, region_index=None, confidence=0.8, human_like=True
    ):
        result = self.find_image(template_path, region_index, confidence)
        if result:
            abs_x, abs_y = result
            self.move_mouse(abs_x, abs_y, human_like)
            return True
        return False

    def hover_text(self, text, region_index, case_sensitive=False, human_like=True):
        result = self.find_text(text, region_index, case_sensitive)
        if result:
            abs_x, abs_y = result
            self.move_mouse(abs_x, abs_y, human_like)
            return True
        return False

    def get_pixel_color_fast(self, x, y):
        self.check_running()
        try:
            hdc = ctypes.windll.user32.GetDC(0)
            pixel = ctypes.windll.gdi32.GetPixel(hdc, x, y)
            ctypes.windll.user32.ReleaseDC(0, hdc)
            r = pixel & 0xFF
            g = (pixel >> 8) & 0xFF
            b = (pixel >> 16) & 0xFF
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception as e:
            self.log(f"Error in get_pixel_color_fast: {e}")
            return None

    def _resolve_region(self, region_index):
        if region_index is None:
            return None
        if isinstance(region_index, int):
            if region_index >= len(self.regions):
                self.log(f"Error: Region index {region_index} does not exist.")
                return None
            return self.regions[region_index]
        if isinstance(region_index, dict):
            if all(k in region_index for k in ("x", "y", "width", "height")):
                return region_index
            x = region_index.get("x", 0)
            y = region_index.get("y", 0)
            w = region_index.get("width", region_index.get("w", 0))
            h = region_index.get("height", region_index.get("h", 0))
            return {"x": x, "y": y, "width": w, "height": h}
        if isinstance(region_index, (list, tuple)) and len(region_index) == 4:
            return {"x": region_index[0], "y": region_index[1], "width": region_index[2], "height": region_index[3]}
        self.log(f"Error: Invalid region representation {region_index}")
        return None

    def find_text(self, text, region_index, case_sensitive=False):
        self.check_running()
        try:
            import pytesseract
            import cv2
            import os
        except ImportError as e:
            self.log(f"Vision Error: Missing dependency. {e}")
            return None

        if getattr(self, "_tesseract_available", None) is None:
            # Auto-detect Tesseract path on Windows if not in PATH
            tesseract_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe"),
            ]

            # Check if tesseract is already in PATH
            from subprocess import run, PIPE

            in_path = False
            try:
                run(["tesseract", "--version"], stdout=PIPE, stderr=PIPE)
                in_path = True
            except FileNotFoundError:
                pass
            except Exception as e:
                self.log(f"Vision Warning: Tesseract PATH check failed: {e}")

            if not in_path:
                for path in tesseract_paths:
                    if os.path.exists(path):
                        pytesseract.pytesseract.tesseract_cmd = path
                        break

            # Check if tesseract is installed/accessible
            try:
                pytesseract.get_tesseract_version()
                self._tesseract_available = True
            except pytesseract.TesseractNotFoundError:
                self._tesseract_available = False
                self._tesseract_error = "Vision Error: Tesseract OCR engine not found. Please ensure it is installed and in your PATH, or at C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
            except Exception as e:
                self._tesseract_available = False
                self._tesseract_error = f"Vision Error: Tesseract check failed. {e}"

        if not getattr(self, "_tesseract_available", False):
            self.log(getattr(self, "_tesseract_error", "Unknown Tesseract error"))

        # Keep original fallback checks for maximum robust redundancy
        tesseract_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe"),
        ]

        from subprocess import run, PIPE

        in_path = False
        try:
            run(["tesseract", "--version"], stdout=PIPE, stderr=PIPE)
            in_path = True
        except FileNotFoundError:
            pass
        except Exception as e:
            self.log(f"Vision Warning: Tesseract PATH check failed: {e}")

        if not in_path:
            for path in tesseract_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    break

        try:
            pytesseract.get_tesseract_version()
        except pytesseract.TesseractNotFoundError:
            self.log(
                "Vision Error: Tesseract OCR engine not found. Please ensure it is installed and in your PATH, or at C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
            )
            return None

        region = self._resolve_region(region_index)
        if region is None:
            self.log(f"Error: Could not resolve region from {region_index}")
            return None

        self.focus_window()

        try:
            full_frame = self._get_current_frame()
            if full_frame is None:
                self.log("Vision Error: Could not get screen frame.")
                return None

            x, y, w, h = region["x"], region["y"], region["width"], region["height"]
            roi = full_frame[y : y + h, x : x + w]

            # Compute fast hash of the region to avoid redundant Tesseract OCR processes
            import hashlib
            roi_hash = hashlib.md5(roi.tobytes()).hexdigest()

            self.log(f"Scanning region {region_index} ({w}x{h}) for text '{text}'...")

            if roi.shape[2] == 4:  # BGRA to Gray
                cv_img = cv2.cvtColor(roi, cv2.COLOR_BGRA2GRAY)
            else:  # RGB to Gray
                cv_img = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)

            # We will use up to 3 passes to recognize the text:
            # Pass 1: 2x Interpolated Gray (retains detail, best for small fonts)
            # Pass 2: 2x Interpolated + Otsu Thresholding (best for high contrast backgrounds)
            # Pass 3: 2x Interpolated + Inverted Otsu (best for light text on dark background)
            
            scale_factor = 2.0
            scaled_img = cv2.resize(cv_img, (0, 0), fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
            
            _, binarized = cv2.threshold(scaled_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            _, binarized_inv = cv2.threshold(scaled_img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            passes = [
                (scaled_img, "--psm 3", "2x Scale Interpolated (PSM 3)"),
                (scaled_img, "--psm 6", "2x Scale Interpolated (PSM 6)"),
                (scaled_img, "--psm 11", "2x Scale Interpolated (PSM 11)"),
                (binarized, "--psm 3", "2x Scale + Otsu Binarization (PSM 3)"),
                (binarized, "--psm 6", "2x Scale + Otsu Binarization (PSM 6)"),
                (binarized_inv, "--psm 3", "2x Scale + Inverted Otsu (PSM 3)"),
                (binarized_inv, "--psm 6", "2x Scale + Inverted Otsu (PSM 6)")
            ]
            
            query_words = [q for q in text.split() if q.strip()]
            if not query_words:
                return None
            n_query = len(query_words)

            import re
            def clean_str(s):
                return re.sub(r'[^a-z0-9]', '', s.lower())

            clean_query = clean_str(text)

            # Initialize OCR cache if not present (defensive)
            if not hasattr(self, "_ocr_cache"):
                self._ocr_cache = {}

            for pass_idx, (processed_img, config_str, pass_name) in enumerate(passes):
                cache_key = (roi_hash, pass_idx)
                if cache_key in self._ocr_cache:
                    if self._debug_mode:
                        self.log(f"Retrieving OCR result from frame-hash cache (Pass: {pass_name})")
                    data = self._ocr_cache[cache_key]
                else:
                    if self._debug_mode:
                        self.log(f"Running OCR Pass: {pass_name}")
                    data = pytesseract.image_to_data(processed_img, config=config_str, output_type=pytesseract.Output.DICT)
                    
                    # FIFO eviction if cache size exceeds 1000 items (approx 140 images with all 7 passes)
                    if len(self._ocr_cache) >= 1000:
                        try:
                            self._ocr_cache.pop(next(iter(self._ocr_cache)))
                        except Exception:
                            pass
                    self._ocr_cache[cache_key] = data

                found_words = [w for w in data["text"] if w.strip()]
                
                if self._debug_mode:
                    self.log(f"[{pass_name}] found words: {found_words}")

                words_in_data = data["text"]
                num_words = len(words_in_data)

                found_match = False
                matched_start = -1
                matched_len = 0

                # 1. Try exact sequence match
                for i in range(num_words - n_query + 1):
                    sub_words = words_in_data[i : i + n_query]
                    if any(not w.strip() for w in sub_words):
                        continue

                    match = True
                    for qw, sw in zip(query_words, sub_words):
                        m = (qw == sw) if case_sensitive else (qw.lower() == sw.lower())
                        if not m:
                            match = False
                            break

                    if match:
                        found_match = True
                        matched_start = i
                        matched_len = n_query
                        break

                # 2. Try substring sliding-window fallback if exact match failed
                if not found_match and len(clean_query) >= 3:
                    for window_size in range(1, n_query + 3):
                        for i in range(num_words - window_size + 1):
                            sub_words = words_in_data[i : i + window_size]
                            joined_sub = "".join(sub_words)
                            clean_joined = clean_str(joined_sub)
                            
                            if clean_joined and (clean_query in clean_joined or clean_joined in clean_query):
                                found_match = True
                                matched_start = i
                                matched_len = window_size
                                break
                        if found_match:
                            break

                if found_match:
                    # Reconstruct bounding box in the scaled image coords
                    left_coords = [data["left"][idx] for idx in range(matched_start, matched_start + matched_len)]
                    top_coords = [data["top"][idx] for idx in range(matched_start, matched_start + matched_len)]
                    right_coords = [data["left"][idx] + data["width"][idx] for idx in range(matched_start, matched_start + matched_len)]
                    bottom_coords = [data["top"][idx] + data["height"][idx] for idx in range(matched_start, matched_start + matched_len)]

                    min_l = min(left_coords)
                    min_t = min(top_coords)
                    max_r = max(right_coords)
                    max_b = max(bottom_coords)

                    # Center coordinate in processed image
                    scaled_rel_x = min_l + (max_r - min_l) // 2
                    scaled_rel_y = min_t + (max_b - min_t) // 2

                    # Map back to original image coordinate scale
                    rel_x = int(scaled_rel_x / scale_factor)
                    rel_y = int(scaled_rel_y / scale_factor)

                    left, top, _, _ = _get_true_hwnd_rect(self._target_hwnd)
                    abs_x = left + region["x"] + rel_x
                    abs_y = top + region["y"] + rel_y

                    self.log(f"Found text '{text}' via {pass_name} at ({abs_x}, {abs_y})")
                    return abs_x, abs_y

            self.log(f"Text '{text}' not found in region.")
            return None
        except Exception as e:
            self.log(f"OCR Error: {e}")
            return None

    def find_image(self, template_path, region_index=None, confidence=0.8):
        self.check_running()
        try:
            import cv2
        except ImportError as e:
            self.log(f"Vision Error: Missing dependency. {e}")
            return None
        import os

        # Check template cache (cache tuples of (template, mask, has_alpha))
        if template_path in self._template_cache:
            cache_val = self._template_cache[template_path]
            # Handle legacy cache format where only template was cached
            if isinstance(cache_val, tuple) and len(cache_val) == 3:
                template, mask, has_alpha = cache_val
            else:
                template = cache_val
                mask = None
                has_alpha = False
        else:
            if not os.path.exists(template_path):
                self.log(f"Error: Template image not found at {template_path}")
                return None

            # Read unchanged to preserve alpha channel
            template_img = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
            if template_img is None:
                self.log("Error: Failed to load template image.")
                return None

            has_alpha = False
            mask = None
            if len(template_img.shape) == 3 and template_img.shape[2] == 4:
                # Extract alpha channel
                alpha = template_img[:, :, 3]
                # Only treat as transparent if there are actual non-opaque pixels
                if np.any(alpha < 255):
                    template = template_img[:, :, :3] # BGR channels
                    mask = alpha
                    has_alpha = True
                else:
                    template = template_img[:, :, :3]
            else:
                template = template_img

            self._template_cache[template_path] = (template, mask, has_alpha)

        self.focus_window()

        try:
            full_frame = self._get_current_frame()
            if full_frame is None:
                self.log("Vision Error: Could not get screen frame.")
                return None

            # Convert full frame to BGR for matching (assuming BGRA from shared memory)
            if full_frame.shape[2] == 4:
                img_bgr = cv2.cvtColor(full_frame, cv2.COLOR_BGRA2BGR)
            else:
                img_bgr = cv2.cvtColor(full_frame, cv2.COLOR_RGB2BGR)

            if region_index is not None:
                region = self._resolve_region(region_index)
                if region is None:
                    return None
                x, y, w, h = region["x"], region["y"], region["width"], region["height"]
                search_area = img_bgr[y : y + h, x : x + w]
                offset_x, offset_y = region["x"], region["y"]
            else:
                search_area = img_bgr
                offset_x, offset_y = 0, 0

            if has_alpha:
                # SQDIFF_NORMED with mask: best match is at min_val (perfect match is 0.0)
                res = cv2.matchTemplate(search_area, template, cv2.TM_SQDIFF_NORMED, mask=mask)
                min_val, max_val, min_loc, max_pos = cv2.minMaxLoc(res)
                match_val = 1.0 - min_val
                best_pos = min_loc
            else:
                res = cv2.matchTemplate(search_area, template, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_pos = cv2.minMaxLoc(res)
                match_val = max_val
                best_pos = max_pos

            if match_val >= confidence:
                th, tw = template.shape[:2]
                rel_x = best_pos[0] + tw // 2
                rel_y = best_pos[1] + th // 2

                left, top, _, _ = _get_true_hwnd_rect(self._target_hwnd)
                abs_x = left + offset_x + rel_x
                abs_y = top + offset_y + rel_y

                self.log(
                    f"Found image '{os.path.basename(template_path)}' (Conf: {match_val:.2f}) at ({abs_x}, {abs_y})"
                )
                return abs_x, abs_y

            self.log(f"Image not found. Max confidence: {match_val:.2f}")
            return None
        except Exception as e:
            self.log(f"Vision Error: {e}")
            return None

    def find_all_images(self, template_path, region_index=None, confidence=0.8, max_results=100):
        self.check_running()
        try:
            import cv2
        except ImportError as e:
            self.log(f"Vision Error: Missing dependency. {e}")
            return []
        import os

        # Cache template loading with transparency support
        if template_path in self._template_cache:
            cache_val = self._template_cache[template_path]
            if isinstance(cache_val, tuple) and len(cache_val) == 3:
                template, mask, has_alpha = cache_val
            else:
                template = cache_val
                mask = None
                has_alpha = False
        else:
            if not os.path.exists(template_path):
                self.log(f"Error: Template image not found at {template_path}")
                return []

            template_img = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
            if template_img is None:
                self.log("Error: Failed to load template image.")
                return []

            has_alpha = False
            mask = None
            if len(template_img.shape) == 3 and template_img.shape[2] == 4:
                alpha = template_img[:, :, 3]
                if np.any(alpha < 255):
                    template = template_img[:, :, :3]
                    mask = alpha
                    has_alpha = True
                else:
                    template = template_img[:, :, :3]
            else:
                template = template_img

            self._template_cache[template_path] = (template, mask, has_alpha)

        self.focus_window()

        try:
            full_frame = self._get_current_frame()
            if full_frame is None:
                self.log("Vision Error: Could not get screen frame.")
                return []

            if full_frame.shape[2] == 4:
                img_bgr = cv2.cvtColor(full_frame, cv2.COLOR_BGRA2BGR)
            else:
                img_bgr = cv2.cvtColor(full_frame, cv2.COLOR_RGB2BGR)

            if region_index is not None:
                region = self._resolve_region(region_index)
                if region is None:
                    return []
                x, y, w, h = region["x"], region["y"], region["width"], region["height"]
                search_area = img_bgr[y : y + h, x : x + w]
                offset_x, offset_y = region["x"], region["y"]
            else:
                search_area = img_bgr
                offset_x, offset_y = 0, 0

            # Match template
            if has_alpha:
                res = cv2.matchTemplate(search_area, template, cv2.TM_SQDIFF_NORMED, mask=mask)
                locs = np.where(res <= (1.0 - confidence))
                scores = 1.0 - res[locs]
            else:
                res = cv2.matchTemplate(search_area, template, cv2.TM_CCOEFF_NORMED)
                locs = np.where(res >= confidence)
                scores = res[locs]

            h, w = template.shape[:2]
            candidates = []
            for y_val, x_val, score in zip(locs[0], locs[1], scores):
                candidates.append([int(x_val), int(y_val), int(x_val + w), int(y_val + h), float(score)])

            # Sort by score descending
            candidates = sorted(candidates, key=lambda c: c[4], reverse=True)

            # Apply Non-Maximum Suppression (NMS) to remove overlapping results
            keep = []
            while candidates and len(keep) < max_results:
                best = candidates.pop(0)
                keep.append(best)
                new_candidates = []
                for cand in candidates:
                    # Calculate intersection coordinates
                    ix1 = max(best[0], cand[0])
                    iy1 = max(best[1], cand[1])
                    ix2 = min(best[2], cand[2])
                    iy2 = min(best[3], cand[3])
                    
                    iw = max(0, ix2 - ix1)
                    ih = max(0, iy2 - iy1)
                    inter_area = iw * ih
                    
                    if inter_area > 0:
                        best_area = (best[2] - best[0]) * (best[3] - best[1])
                        cand_area = (cand[2] - cand[0]) * (cand[3] - cand[1])
                        union_area = best_area + cand_area - inter_area
                        iou = inter_area / union_area
                        if iou > 0.3:  # Overlap threshold
                            continue
                    new_candidates.append(cand)
                candidates = new_candidates

            left, top, _, _ = _get_true_hwnd_rect(self._target_hwnd)
            results = []
            for box in keep:
                center_x = left + offset_x + box[0] + w // 2
                center_y = top + offset_y + box[1] + h // 2
                results.append((center_x, center_y))

            if results:
                self.log(f"Found {len(results)} matches for '{os.path.basename(template_path)}'")
            return results
        except Exception as e:
            self.log(f"Vision Error in find_all_images: {e}")
            return []
        except Exception as e:
            self.log(f"Vision Error: {e}")
            return None

    def drag_and_drop(self, src_region_index, dst_region_index, duration=0.5):
        self.check_running()

        if src_region_index >= len(self.regions) or dst_region_index >= len(
            self.regions
        ):
            self.log("Error: Invalid region index for drag and drop.")
            return False

        r1 = self.regions[src_region_index]
        r2 = self.regions[dst_region_index]
        self.focus_window()

        try:
            left, top, _, _ = _get_true_hwnd_rect(self._target_hwnd)

            start_x = left + r1["x"] + r1["width"] // 2
            start_y = top + r1["y"] + r1["height"] // 2

            end_x = left + r2["x"] + r2["width"] // 2
            end_y = top + r2["y"] + r2["height"] // 2

            self.bot.move_to(start_x, start_y)
            time.sleep(0.1)
            self.bot.press_button("left", down=True)
            time.sleep(0.1)
            self.bot.move_to(end_x, end_y)
            time.sleep(duration)
            self.bot.press_button("left", down=False)

            self.log(f"Dragged from region {src_region_index} to {dst_region_index}")
            return True
        except Exception as e:
            self.log(f"Drag and Drop Error: {e}")
            return False

    def find_color_clusters(
        self, name_or_colors, proximity=None, tolerance=None, region_index=None
    ):
        """
        Connected-Component Labeling (CCL) based Color Cluster Segmentation.
        Segments the frame, clusters pixels, bridges gaps within 'proximity' pixels,
        and filters components to only keep those containing all specified colors.
        
        Returns a list of DynamicRegion objects.
        """
        self.check_running()
        
        # 1. Resolve colors, proximity and tolerance
        colors = []
        p_val = proximity
        t_val = tolerance

        if isinstance(name_or_colors, str):
            # Predefined cluster lookup
            matched = None
            for c in self._color_clusters:
                if c["name"] == name_or_colors:
                    matched = c
                    break
            if matched:
                colors = matched["colors"]
                if p_val is None:
                    p_val = matched["proximity"]
                if t_val is None:
                    t_val = matched["tolerance"]
            else:
                self.log(f"Warning: Predefined cluster '{name_or_colors}' not found. Treating as single color.")
                colors = [name_or_colors]
        elif isinstance(name_or_colors, list):
            colors = name_or_colors

        if not colors:
            self.log("Vision Error: No colors specified for color clusters segmentation.")
            return []

        if p_val is None:
            p_val = 10
        if t_val is None:
            t_val = 25

        # 1b. Check frame-based cache
        cache_key = (self._frame_counter, tuple(colors), p_val, t_val, region_index)
        if cache_key in self._ccl_cache:
            if self._debug_mode:
                self.log(f"Retrieving color cluster results from frame cache (Key: {cache_key})")
            return self._ccl_cache[cache_key]

        # 2. Get frame
        full_frame = self._get_current_frame()
        if full_frame is None:
            self.log("Vision Error: Could not retrieve screen frame.")
            return []

        # Convert full frame to BGR
        if full_frame.shape[2] == 4:
            img_bgr = cv2.cvtColor(full_frame, cv2.COLOR_BGRA2BGR)
        else:
            img_bgr = cv2.cvtColor(full_frame, cv2.COLOR_RGB2BGR)

        # 3. Handle ROI (region_index)
        if region_index is not None:
            region = self._resolve_region(region_index)
            if region is None:
                return []
            rx, ry, rw, rh = region["x"], region["y"], region["width"], region["height"]
            search_area = img_bgr[ry : ry + rh, rx : rx + rw]
            offset_x, offset_y = rx, ry
        else:
            search_area = img_bgr
            offset_x, offset_y = 0, 0

        # 4. Generate binary masks for each color
        masks = []
        for hex_col in colors:
            b, g, r = hex_to_bgr(hex_col)
            lower = np.array([max(0, b - t_val), max(0, g - t_val), max(0, r - t_val)], dtype=np.uint8)
            upper = np.array([min(255, b + t_val), min(255, g + t_val), min(255, r + t_val)], dtype=np.uint8)
            mask = cv2.inRange(search_area, lower, upper)
            masks.append(mask)

        # 5. Combine and dilate mask (proximity gap bridging) with zero-copy/in-place optimization
        if len(masks) == 1:
            combined_mask = masks[0]
        else:
            combined_mask = np.zeros(search_area.shape[:2], dtype=np.uint8)
            for m in masks:
                cv2.bitwise_or(combined_mask, m, dst=combined_mask)

        if p_val > 1:
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (p_val, p_val))
            dilated_mask = cv2.dilate(combined_mask, kernel)
        else:
            dilated_mask = combined_mask

        # 6. Run native Connected Component Labeling
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(dilated_mask)

        # 7. Check color co-existence on each component with native C++ optimizations
        valid_regions = []
        for k in range(1, num_labels): # Skip background label (0)
            left, top, w, h, area = stats[k]
            
            # Fast check: skip very small components immediately
            if area < 4:
                continue

            # Crop labels view and run fast native C++ scalar compare
            labels_crop = labels[top : top + h, left : left + w]
            comp_mask_crop = cv2.compare(labels_crop, k, cv2.CMP_EQ)

            # Check coexistence of ALL original colors in this component
            coexistence_valid = True
            for m in masks:
                m_crop = m[top : top + h, left : left + w]
                intersection = cv2.bitwise_and(m_crop, comp_mask_crop)
                if cv2.countNonZero(intersection) == 0:
                    coexistence_valid = False
                    break

            if coexistence_valid:
                # Instantiate DynamicRegion
                centroid = centroids[k]
                valid_regions.append(
                    DynamicRegion(
                        self,
                        label_id=k,
                        stats=stats[k],
                        centroid=centroid,
                        mask=comp_mask_crop,
                        offset_x=offset_x,
                        offset_y=offset_y
                    )
                )

        if self._debug_mode:
            self.log(f"find_color_clusters found {len(valid_regions)} matches out of {num_labels - 1} connected components.")

        # Cache results before returning
        self._ccl_cache[cache_key] = valid_regions
        return valid_regions

    def find_color_cluster(
        self, name_or_colors, proximity=None, tolerance=None, region_index=None
    ):
        """Returns the first matching DynamicRegion, or None if none found."""
        regions = self.find_color_clusters(
            name_or_colors, proximity, tolerance, region_index
        )
        return regions[0] if regions else None

    def click_color_cluster(
        self, name_or_colors, proximity=None, tolerance=None, region_index=None, button="left", human_like=True
    ):
        """Finds the first matching cluster and clicks its centroid."""
        region = self.find_color_cluster(
            name_or_colors, proximity, tolerance, region_index
        )
        if region:
            region.click(button=button, human_like=human_like)
            return True
        else:
            self.log(f"Vision Error: click_color_cluster could not find cluster '{name_or_colors}'")
            return False

    def detect_shapes(self, shape_type="all", min_size=15, max_size=None, region_index=None):
        """
        Detects circles, rectangles, or grid cells using OpenCV contour analysis.
        Returns a list of dicts: {"type": ..., "x": ..., "y": ..., "width": ..., "height": ..., "confidence": ...}
        """
        self.check_running()
        full_frame = self._get_current_frame()
        if full_frame is None:
            self.log("Vision Error: Could not retrieve screen frame for shape detection.")
            return []

        # Convert full frame to BGR
        if full_frame.shape[2] == 4:
            img_bgr = cv2.cvtColor(full_frame, cv2.COLOR_BGRA2BGR)
        else:
            img_bgr = cv2.cvtColor(full_frame, cv2.COLOR_RGB2BGR)

        # Handle ROI
        if region_index is not None:
            region = self._resolve_region(region_index)
            if region is None:
                return []
            rx, ry, rw, rh = region["x"], region["y"], region["width"], region["height"]
            search_area = img_bgr[ry : ry + rh, rx : rx + rw]
            offset_x, offset_y = rx, ry
        else:
            search_area = img_bgr
            offset_x, offset_y = 0, 0

        # Grayscale, Gaussian Blur & Canny Edge Detection
        gray = cv2.cvtColor(search_area, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        
        # Find Contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detected = []
        rectangles = []  # candidate rectangles for Grid solver
        
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w < min_size or h < min_size:
                continue
            if max_size is not None and (w > max_size or h > max_size):
                continue
                
            perimeter = cv2.arcLength(cnt, True)
            area = cv2.contourArea(cnt)
            if perimeter == 0:
                continue
                
            # 1. Circularity check
            circularity = 4 * np.pi * area / (perimeter ** 2)
            if (shape_type == "all" or shape_type == "circle") and circularity > 0.82:
                (cx, cy), r = cv2.minEnclosingCircle(cnt)
                cw = int(r * 2)
                ch = int(r * 2)
                cx_box = int(cx - r)
                cy_box = int(cy - r)
                
                detected.append({
                    "type": "circle",
                    "x": offset_x + cx_box,
                    "y": offset_y + cy_box,
                    "width": cw,
                    "height": ch,
                    "confidence": float(circularity)
                })
                continue
            
            # 2. Polygon approximation
            approx = cv2.approxPolyDP(cnt, 0.03 * perimeter, True)
            if len(approx) == 4 and cv2.isContourConvex(approx):
                rectangles.append((x, y, w, h))

        # Grid Clustering Solver
        if shape_type in ("all", "grid"):
            rects_by_size = []
            for r in rectangles:
                rx, ry, rw, rh = r
                added = False
                for group in rects_by_size:
                    rep_w = sum(item[2] for item in group) / len(group)
                    rep_h = sum(item[3] for item in group) / len(group)
                    if abs(rw - rep_w) < rep_w * 0.15 and abs(rh - rep_h) < rep_h * 0.15:
                        group.append(r)
                        added = True
                        break
                if not added:
                    rects_by_size.append([r])
            
            for group in rects_by_size:
                if len(group) < 4:
                    continue
                sorted_group = sort_grid_cells(group)
                
                rows = []
                for cell in sorted_group:
                    cx, cy, cw, ch = cell
                    added = False
                    for r_list in rows:
                        avg_y = sum(item[1] for item in r_list) / len(r_list)
                        if abs(cy - avg_y) < ch / 2:
                            r_list.append(cell)
                            added = True
                            break
                    if not added:
                        rows.append([cell])
                
                if len(rows) >= 2:
                    cols_counts = [len(r_list) for r_list in rows]
                    max_cols = max(cols_counts)
                    if max_cols >= 2 and all(abs(count - max_cols) <= 1 for count in cols_counts):
                        for r_list in rows:
                            for cell in r_list:
                                cx, cy, cw, ch = cell
                                detected.append({
                                    "type": "grid_cell",
                                    "x": offset_x + cx,
                                    "y": offset_y + cy,
                                    "width": cw,
                                    "height": ch,
                                    "confidence": 1.0
                                })
                        continue

        if shape_type in ("all", "rectangle"):
            for r in rectangles:
                rx, ry, rw, rh = r
                detected.append({
                    "type": "rectangle",
                    "x": offset_x + rx,
                    "y": offset_y + ry,
                    "width": rw,
                    "height": rh,
                    "confidence": 1.0
                })

        return detected

    def find_shapes(self, shape_type="circle", min_size=15, max_size=None, region_index=None):
        """
        Returns a list of DynamicRegion objects representing detected shapes.
        """
        self.check_running()
        shapes = self.detect_shapes(
            shape_type=shape_type,
            min_size=min_size,
            max_size=max_size,
            region_index=region_index
        )
        
        valid_regions = []
        for i, s in enumerate(shapes):
            cx, cy, cw, ch = s["x"], s["y"], s["width"], s["height"]
            stats = [cx, cy, cw, ch, cw * ch]
            centroid = (cx + cw / 2.0, cy + ch / 2.0)
            mask = np.ones((ch, cw), dtype=np.uint8) * 255
            
            valid_regions.append(
                DynamicRegion(
                    bot=self,
                    label_id=i + 1,
                    stats=stats,
                    centroid=centroid,
                    mask=mask,
                    offset_x=0,
                    offset_y=0
                )
            )
        return valid_regions

    def find_grid(self, min_cells=4, size_tolerance=0.15, region_index=None):
        """
        Returns a DynamicGrid object representing the largest detected grid, or None.
        """
        self.check_running()
        shapes = self.detect_shapes(shape_type="grid", min_size=15, region_index=region_index)
        
        grid_cells = [s for s in shapes if s["type"] == "grid_cell"]
        if not grid_cells:
            # Fallback: check raw rectangles and try solver
            rect_shapes = self.detect_shapes(shape_type="rectangle", min_size=15, region_index=region_index)
            rects = [(s["x"], s["y"], s["width"], s["height"]) for s in rect_shapes]
            if len(rects) >= min_cells:
                rects_by_size = []
                for r in rects:
                    rw, rh = r[2], r[3]
                    added = False
                    for group in rects_by_size:
                        rep_w = sum(item[2] for item in group) / len(group)
                        rep_h = sum(item[3] for item in group) / len(group)
                        if abs(rw - rep_w) < rep_w * size_tolerance and abs(rh - rep_h) < rep_h * size_tolerance:
                            group.append(r)
                            added = True
                            break
                    if not added:
                        rects_by_size.append([r])
                
                for group in rects_by_size:
                    if len(group) >= min_cells:
                        grid_cells = [{"x": r[0], "y": r[1], "width": r[2], "height": r[3]} for r in group]
                        break
                        
        if len(grid_cells) < min_cells:
            return None
            
        cell_coords = [(c["x"], c["y"], c["width"], c["height"]) for c in grid_cells]
        sorted_coords = sort_grid_cells(cell_coords)
        
        xs = [c[0] for c in sorted_coords]
        ys = [c[1] for c in sorted_coords]
        right_coords = [c[0] + c[2] for c in sorted_coords]
        bottom_coords = [c[1] + c[3] for c in sorted_coords]
        
        min_x = min(xs)
        min_y = min(ys)
        max_x = max(right_coords)
        max_y = max(bottom_coords)
        
        rows = []
        for cell in sorted_coords:
            cx, cy, cw, ch = cell
            added = False
            for r_list in rows:
                avg_y = sum(item[1] for item in r_list) / len(r_list)
                if abs(cy - avg_y) < ch / 2:
                    r_list.append(cell)
                    added = True
                    break
            if not added:
                rows.append([cell])
                
        num_rows = len(rows)
        num_cols = max(len(r_list) for r_list in rows) if rows else 0
        
        return DynamicGrid(
            bot=self,
            x=min_x,
            y=min_y,
            w=max_x - min_x,
            h=max_y - min_y,
            rows=num_rows,
            cols=num_cols,
            cells=sorted_coords
        )

    def wait_for_change(self, region_index, threshold=0.02, timeout=10):
        """
        Blocks execution until the specified region detects a visual change.
        """
        self.check_running()
        region = self._resolve_region(region_index)
        if region is None:
            self.log(f"Motion Trigger Error: Region index {region_index} could not be resolved.")
            return False

        rx, ry, rw, rh = region["x"], region["y"], region["width"], region["height"]
        
        full_frame = self._get_current_frame()
        if full_frame is None:
            self.log("Motion Trigger Error: Reference frame could not be retrieved.")
            return False
            
        ref_crop = full_frame[ry : ry + rh, rx : rx + rw]
        if ref_crop.shape[2] == 4:
            ref_gray = cv2.cvtColor(ref_crop, cv2.COLOR_BGRA2GRAY)
        else:
            ref_gray = cv2.cvtColor(ref_crop, cv2.COLOR_RGB2GRAY)
            
        start_time = time.time()
        self.log(f"Waiting for visual change inside region {region_index}...")
        
        while time.time() - start_time < timeout:
            if not self.is_running:
                raise ScriptStoppedError()
                
            time.sleep(0.05)
            
            current_frame = self._get_current_frame()
            if current_frame is None:
                continue
                
            curr_crop = current_frame[ry : ry + rh, rx : rx + rw]
            if curr_crop.shape[2] == 4:
                curr_gray = cv2.cvtColor(curr_crop, cv2.COLOR_BGRA2GRAY)
            else:
                curr_gray = cv2.cvtColor(curr_crop, cv2.COLOR_RGB2GRAY)
                
            diff = cv2.absdiff(curr_gray, ref_gray)
            _, thresh = cv2.threshold(diff, 20, 255, cv2.THRESH_BINARY)
            
            change_pixels = cv2.countNonZero(thresh)
            total_pixels = rw * rh
            ratio = float(change_pixels) / total_pixels
            
            if ratio >= threshold:
                self.log(f"Motion Detected! Visual change of {ratio:.1%} exceeded threshold {threshold:.1%}.")
                return True
                
        self.log(f"Timeout: No change detected inside region {region_index} after {timeout} seconds.")
        return False

    def wait_for_no_change(self, region_index, threshold=0.01, timeout=10, duration=1.0):
        """
        Blocks execution until the specified region becomes stable/static.
        """
        self.check_running()
        region = self._resolve_region(region_index)
        if region is None:
            self.log(f"Motion Trigger Error: Region index {region_index} could not be resolved.")
            return False

        rx, ry, rw, rh = region["x"], region["y"], region["width"], region["height"]
        
        start_time = time.time()
        stable_start = None
        
        full_frame = self._get_current_frame()
        if full_frame is None:
            self.log("Motion Trigger Error: Initial frame could not be retrieved.")
            return False
            
        last_crop = full_frame[ry : ry + rh, rx : rx + rw]
        if last_crop.shape[2] == 4:
            last_gray = cv2.cvtColor(last_crop, cv2.COLOR_BGRA2GRAY)
        else:
            last_gray = cv2.cvtColor(last_crop, cv2.COLOR_RGB2GRAY)
            
        self.log(f"Waiting for region {region_index} to stabilize (no change for {duration}s)...")
        
        while time.time() - start_time < timeout:
            if not self.is_running:
                raise ScriptStoppedError()
                
            time.sleep(0.05)
            
            current_frame = self._get_current_frame()
            if current_frame is None:
                continue
                
            curr_crop = current_frame[ry : ry + rh, rx : rx + rw]
            if curr_crop.shape[2] == 4:
                curr_gray = cv2.cvtColor(curr_crop, cv2.COLOR_BGRA2GRAY)
            else:
                curr_gray = cv2.cvtColor(curr_crop, cv2.COLOR_RGB2GRAY)
                
            diff = cv2.absdiff(curr_gray, last_gray)
            _, thresh = cv2.threshold(diff, 20, 255, cv2.THRESH_BINARY)
            
            change_pixels = cv2.countNonZero(thresh)
            total_pixels = rw * rh
            ratio = float(change_pixels) / total_pixels
            
            last_gray = curr_gray
            
            if ratio < threshold:
                if stable_start is None:
                    stable_start = time.time()
                elif time.time() - stable_start >= duration:
                    self.log(f"Region {region_index} is stable! Change ratio {ratio:.2%} remained below {threshold:.1%} for {duration}s.")
                    return True
            else:
                stable_start = None
                
        self.log(f"Timeout: Region {region_index} did not stabilize after {timeout} seconds.")
        return False


def sort_grid_cells(cells):
    # Sort by y first
    cells = sorted(cells, key=lambda c: c[1])
    rows = []
    for c in cells:
        x, y, w, h = c
        added = False
        for r in rows:
            avg_y = sum(item[1] for item in r) / len(r)
            if abs(y - avg_y) < h / 2:
                r.append(c)
                added = True
                break
        if not added:
            rows.append([c])
            
    sorted_cells = []
    rows = sorted(rows, key=lambda r: sum(item[1] for item in r) / len(r))
    for r in rows:
        sorted_row = sorted(r, key=lambda c: c[0])
        sorted_cells.extend(sorted_row)
    return sorted_cells


class DynamicGrid:
    def __init__(self, bot, x, y, w, h, rows, cols, cells):
        self.bot = bot
        self.x = x
        self.y = y
        self.width = w
        self.height = h
        self.rows = rows
        self.cols = cols
        self.cells = cells

    def count(self):
        """Returns the total number of cells detected."""
        return len(self.cells)

    def cell(self, cell_index):
        """
        Returns a DynamicRegion for the cell at 1-based index (e.g. 1 to 28).
        """
        if cell_index < 1 or cell_index > len(self.cells):
            self.bot.log(f"Grid Error: Cell index {cell_index} out of bounds (1 to {len(self.cells)}).")
            return None
            
        cx, cy, cw, ch = self.cells[cell_index - 1]
        
        stats = [cx, cy, cw, ch, cw * ch]
        centroid = (cx + cw / 2.0, cy + ch / 2.0)
        mask = np.ones((ch, cw), dtype=np.uint8) * 255
        
        return DynamicRegion(
            bot=self.bot,
            label_id=cell_index,
            stats=stats,
            centroid=centroid,
            mask=mask,
            offset_x=0,
            offset_y=0
        )

