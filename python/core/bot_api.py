import time
import numpy as np
import ctypes
import random
from ctypes import wintypes
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

class BotAPI:
    def __init__(self, gui_instance=None):
        self.gui = gui_instance
        self._is_running = True
        self._debug_mode = False
        self.bot = Bot()
        self.win = PywinautoBot() if is_pywinauto_available() else None
        self._last_frame = None
        self.regions = []
        self._target_hwnd = None
        self.on_log = None

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
            success = self.win.click_element(window, control_type, identifier, double_click)
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
                state_str = "Toggled" if state is None else ("Checked" if state else "Unchecked")
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
        window = self._get_active_app_window()
        if not window:
            self.log("Error: No target window set for send_hotkey.")
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
        if not self.win: return False
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
        if self._last_frame is not None:
            return self._last_frame
        from PIL import ImageGrab
        return np.array(ImageGrab.grab())

    @property
    def is_running(self):
        return self._is_running

    @is_running.setter
    def is_running(self, value):
        self._is_running = value

    def focus_window(self):
        if not win32gui or not self._target_hwnd: return
        try:
            win32gui.SetForegroundWindow(self._target_hwnd)
            time.sleep(0.1)
        except Exception as e:
            self.log(f"Error focusing window: {e}")

    def wait(self, seconds):
        time.sleep(seconds)

    def log(self, message):
        if self.on_log:
            self.on_log(message)
        else:
            timestamp = time.strftime('%H:%M:%S')
            print(f"[{timestamp}] {message}")

    def click_region(self, region_index, button='left', modifiers=[], human_like=False):
        if not self.is_running: return False
        if region_index >= len(self.regions):
            self.log(f"Error: Region {region_index} does not exist.")
            return False

        region = self.regions[region_index]
        self.focus_window()

        try:
            left, top, _, _ = _get_true_hwnd_rect(self._target_hwnd)
            x = left + region['x'] + region['width'] // 2
            y = top + region['y'] + region['height'] // 2

            if human_like:
                self.bot.human_move_to(x, y)
                self.bot.click(x, y, button, modifiers)
            else:
                self.bot.click(x, y, button, modifiers)
            self.log(f"Clicked region {region_index} at ({x}, {y})")
            return True
        except Exception as e:
            self.log(f"Error in click_region: {e}")
            return False

    def find_and_click_color(self, hex_color, region_index, button='left', modifiers=[], tolerance=10, human_like=False):
        if not self.is_running: return False
        if region_index >= len(self.regions):
            self.log(f"Error: Region {region_index} does not exist.")
            return False

        region = self.regions[region_index]
        target_rgb = tuple(int(hex_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        
        self.focus_window()

        try:
            full_frame = self._get_current_frame()
            x, y, w, h = region['x'], region['y'], region['width'], region['height']
            roi = full_frame[y:y+h, x:x+w]

            # ROI is BGRA from Shared Memory or RGB from ImageGrab
            # Let's standardize to RGB for the comparison
            if roi.shape[2] == 4: # BGRA
                roi_rgb = roi[:,:,[2,1,0]]
            else:
                roi_rgb = roi

            color_diff = np.abs(roi_rgb - target_rgb)
            matches = np.where(np.all(color_diff <= tolerance, axis=2))

            if len(matches[0]) > 0:
                rel_y, rel_x = matches[0][0], matches[1][0]
                
                left, top, _, _ = _get_true_hwnd_rect(self._target_hwnd)
                abs_x = left + region['x'] + rel_x
                abs_y = top + region['y'] + rel_y

                if human_like:
                    self.bot.human_move_to(abs_x, abs_y)
                    self.bot.click(abs_x, abs_y, button, modifiers)
                else:
                    self.bot.click(abs_x, abs_y, button, modifiers)
                self.log(f"Found color {hex_color} and clicked at ({abs_x}, {abs_y})")
                return True
            else:
                self.log(f"Color {hex_color} not found in region {region_index}.")
                return False
        except Exception as e:
            self.log(f"Error in find_and_click_color: {e}")
            return False

    def get_pixel_color_fast(self, x, y):
        if not self.is_running: return None
        try:
            # If we have a frame, use it
            if self._last_frame is not None:
                # Shared memory frame is likely at (0,0) relative to screen or window
                # For 'fast' pixel color, we usually want screen absolute
                pass 

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
        if not self.is_running: return None
        import pytesseract
        import cv2

        if region_index >= len(self.regions):
            self.log(f"Error: Region {region_index} does not exist.")
            return None

        region = self.regions[region_index]
        self.focus_window()

        try:
            full_frame = self._get_current_frame()
            x, y, w, h = region['x'], region['y'], region['width'], region['height']
            roi = full_frame[y:y+h, x:x+w]
            
            if roi.shape[2] == 4: # BGRA to Gray
                cv_img = cv2.cvtColor(roi, cv2.COLOR_BGRA2GRAY)
            else: # RGB to Gray
                cv_img = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)

            data = pytesseract.image_to_data(cv_img, output_type=pytesseract.Output.DICT)

            for i, word in enumerate(data['text']):
                if not word.strip(): continue
                match = (text == word) if case_sensitive else (text.lower() == word.lower())
                if match:
                    rel_x = data['left'][i] + data['width'][i] // 2
                    rel_y = data['top'][i] + data['height'][i] // 2
                    
                    left, top, _, _ = _get_true_hwnd_rect(self._target_hwnd)
                    abs_x = left + region['x'] + rel_x
                    abs_y = top + region['y'] + rel_y
                    
                    self.log(f"Found text '{text}' at ({abs_x}, {abs_y})")
                    return abs_x, abs_y
            return None
        except Exception as e:
            self.log(f"OCR Error: {e}")
            return None

    def find_image(self, template_path, region_index=None, confidence=0.8):
        if not self.is_running: return None
        import cv2
        import os

        if not os.path.exists(template_path):
            self.log(f"Error: Template image not found at {template_path}")
            return None

        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        if template is None:
            self.log(f"Error: Failed to load template image.")
            return None

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
                x, y, w, h = region['x'], region['y'], region['width'], region['height']
                search_area = img_bgr[y:y+h, x:x+w]
                offset_x, offset_y = region['x'], region['y']
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

                self.log(f"Found image '{os.path.basename(template_path)}' (Conf: {max_val:.2f}) at ({abs_x}, {abs_y})")
                return abs_x, abs_y
            
            self.log(f"Image not found. Max confidence: {max_val:.2f}")
            return None
        except Exception as e:
            self.log(f"Vision Error: {e}")
            return None

    def drag_and_drop(self, src_region_index, dst_region_index, duration=0.5):
        if not self.is_running: return False
        
        if src_region_index >= len(self.regions) or dst_region_index >= len(self.regions):
            self.log(f"Error: Invalid region index for drag and drop.")
            return False

        r1 = self.regions[src_region_index]
        r2 = self.regions[dst_region_index]
        self.focus_window()

        try:
            left, top, _, _ = _get_true_hwnd_rect(self._target_hwnd)
            
            start_x = left + r1['x'] + r1['width'] // 2
            start_y = top + r1['y'] + r1['height'] // 2
            
            end_x = left + r2['x'] + r2['width'] // 2
            end_y = top + r2['y'] + r2['height'] // 2

            self.bot.move_to(start_x, start_y)
            time.sleep(0.1)
            self.bot.press_button('left', down=True)
            time.sleep(0.1)
            self.bot.move_to(end_x, end_y)
            time.sleep(duration)
            self.bot.press_button('left', down=False)
            
            self.log(f"Dragged from region {src_region_index} to {dst_region_index}")
            return True
        except Exception as e:
            self.log(f"Drag and Drop Error: {e}")
            return False
