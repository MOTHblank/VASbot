import time
import numpy as np
import ctypes
import random
from ctypes import wintypes

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
        self._target_hwnd = None
        self.on_log = None
        self._template_cache = {}
        self._tesseract_available = None
        self._tesseract_error = None

    def set_regions(self, regions):
        self.regions = regions

    def set_target_window(self, hwnd):
        self._target_hwnd = hwnd

    def set_frame_buffer(self, buffer):
        self._last_frame = buffer

    # --- High-Level Window Automation (Pywinauto) ---

    def _get_active_app_window(self):
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
        if not self.is_running:
            self.log("Script stopped - aborting type_text")
            return False
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
        if not self.is_running:
            self.log("Script stopped - aborting send_hotkey")
            return False
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
        while total_waited < seconds and self.is_running:
            remaining = seconds - total_waited
            wait_time = min(chunk_size, remaining)
            time.sleep(wait_time)
            total_waited += wait_time

    def log(self, message):
        if self.on_log:
            self.on_log(message)
        else:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] {message}")

    def click_region(self, region_index, button="left", modifiers=[], human_like=False):
        if not self.is_running:
            self.log("Script stopped - aborting click_region")
            return False
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

    def click(self, x, y, button="left", modifiers=[], human_like=False):
        """Clicks at the specified coordinates, supporting optional modifiers and human-like movement."""
        if not self.is_running:
            self.log("Script stopped - aborting click")
            return False

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
        if not self.is_running:
            self.log("Script stopped - aborting find_color")
            return None
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
        modifiers=[],
        tolerance=10,
        human_like=False,
    ):
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
        if not self.is_running:
            return
        if human_like:
            self.bot.human_move_to(x, y)
        else:
            self.bot.move_to(x, y)

    def get_mouse_position(self):
        return self.bot.get_cursor_pos()

    def wait_for_color(self, hex_color, region_index, timeout=10, tolerance=10):
        if not self.is_running:
            return False
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.is_running:
                return False
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
        if not self.is_running:
            return None
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

    def find_text(self, text, region_index, case_sensitive=False):
        if not self.is_running:
            return None
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
        # Auto-detect Tesseract path on Windows if not in PATH
        tesseract_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe")
        ]
        
        # Check if tesseract is already in PATH
        from subprocess import run, PIPE
        in_path = False
        try:
            run(['tesseract', '--version'], stdout=PIPE, stderr=PIPE)
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
        except pytesseract.TesseractNotFoundError:
            self.log("Vision Error: Tesseract OCR engine not found. Please ensure it is installed and in your PATH, or at C:\\Program Files\\Tesseract-OCR\\tesseract.exe")
            return None

        if region_index >= len(self.regions):

            # Check if tesseract is already in PATH
            from subprocess import run, PIPE

            in_path = False
            try:
                run(["tesseract", "--version"], stdout=PIPE, stderr=PIPE)
                in_path = True
            except:
                pass

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

        if not self._tesseract_available:
            self.log(self._tesseract_error)
            return None

        if region_index >= len(self.regions):
            self.log(f"Error: Region {region_index} does not exist.")
            return None

        region = self.regions[region_index]
        self.focus_window()

        try:
            full_frame = self._get_current_frame()
            if full_frame is None:
                self.log("Vision Error: Could not get screen frame.")
                return None

            x, y, w, h = region["x"], region["y"], region["width"], region["height"]
            roi = full_frame[y : y + h, x : x + w]

            self.log(f"Scanning region {region_index} ({w}x{h}) for text '{text}'...")

            if roi.shape[2] == 4:  # BGRA to Gray
                cv_img = cv2.cvtColor(roi, cv2.COLOR_BGRA2GRAY)
            else:  # RGB to Gray
                cv_img = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)

            data = pytesseract.image_to_data(
                cv_img, output_type=pytesseract.Output.DICT
            )

            found_words = [w for w in data["text"] if w.strip()]
            if self._debug_mode:
                self.log(f"OCR found words: {found_words}")

            for i, word in enumerate(data["text"]):
                if not word.strip():
                    continue
                match = (
                    (text == word) if case_sensitive else (text.lower() == word.lower())
                )
                if match:
                    rel_x = data["left"][i] + data["width"][i] // 2
                    rel_y = data["top"][i] + data["height"][i] // 2

                    left, top, _, _ = _get_true_hwnd_rect(self._target_hwnd)
                    abs_x = left + region["x"] + rel_x
                    abs_y = top + region["y"] + rel_y

                    self.log(f"Found text '{text}' at ({abs_x}, {abs_y})")
                    return abs_x, abs_y

            self.log(f"Text '{text}' not found in region.")
            return None
        except Exception as e:
            self.log(f"OCR Error: {e}")
            return None

    def find_image(self, template_path, region_index=None, confidence=0.8):
        if not self.is_running:
            return None
        try:
            import cv2
        except ImportError as e:
            self.log(f"Vision Error: Missing dependency. {e}")
            return None
        import os

        if template_path in self._template_cache:
            template = self._template_cache[template_path]
        else:
            if not os.path.exists(template_path):
                self.log(f"Error: Template image not found at {template_path}")
                return None

            template = cv2.imread(template_path, cv2.IMREAD_COLOR)
            if template is None:
                self.log(f"Error: Failed to load template image.")
                return None
            self._template_cache[template_path] = template

        self.focus_window()

        try:
            full_frame = self._get_current_frame()

            # Convert full frame to BGR for matching (assuming BGRA from shared memory)
            if full_frame.shape[2] == 4:
                img_bgr = cv2.cvtColor(full_frame, cv2.COLOR_BGRA2BGR)
            else:
                img_bgr = cv2.cvtColor(full_frame, cv2.COLOR_RGB2BGR)

            if region_index is not None:
                if region_index >= len(self.regions):
                    self.log(f"Error: Region {region_index} does not exist.")
                    return None
                region = self.regions[region_index]
                x, y, w, h = region["x"], region["y"], region["width"], region["height"]
                search_area = img_bgr[y : y + h, x : x + w]
                offset_x, offset_y = region["x"], region["y"]
            else:
                search_area = img_bgr
                offset_x, offset_y = 0, 0

            res = cv2.matchTemplate(search_area, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_pos = cv2.minMaxLoc(res)

            if max_val >= confidence:
                th, tw = template.shape[:2]
                rel_x = max_pos[0] + tw // 2
                rel_y = max_pos[1] + th // 2

                left, top, _, _ = _get_true_hwnd_rect(self._target_hwnd)
                abs_x = left + offset_x + rel_x
                abs_y = top + offset_y + rel_y

                self.log(
                    f"Found image '{os.path.basename(template_path)}' (Conf: {max_val:.2f}) at ({abs_x}, {abs_y})"
                )
                return abs_x, abs_y

            self.log(f"Image not found. Max confidence: {max_val:.2f}")
            return None
        except Exception as e:
            self.log(f"Vision Error: {e}")
            return None

    def drag_and_drop(self, src_region_index, dst_region_index, duration=0.5):
        if not self.is_running:
            return False

        if src_region_index >= len(self.regions) or dst_region_index >= len(
            self.regions
        ):
            self.log(f"Error: Invalid region index for drag and drop.")
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
