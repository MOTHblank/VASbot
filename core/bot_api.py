import time
import numpy as np
import ctypes
import random
from ctypes import wintypes

try:
    import pyautogui
    pyautogui.FAILSAFE = False
except ImportError: 
    pyautogui = None

try:
    import win32gui
    import win32api
    import win32con
except ImportError: 
    win32gui = win32api = win32con = None

from utils.windows_utils import _get_true_hwnd_rect

# --- Enhanced Ctypes structures for SendInput and DWM ---
user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi
kernel32 = ctypes.windll.kernel32

class BotAPI:
    def __init__(self, gui_instance):
        self.gui = gui_instance
        self._is_running = True
        self._debug_mode = False
        
    @property
    def is_running(self):
        """Check if the script is in a running state, not paused or stopped."""
        if hasattr(self, '_stop_event') and self._stop_event.is_set():
            return False
        return self._is_running
        
    def enable_debug(self):
        """Enable debug logging for troubleshooting"""
        self._debug_mode = True
        self.log("Debug mode enabled")
        
    def wait(self, seconds): 
        """Standard wait with pause support"""
        if hasattr(self.gui, 'script_runner') and hasattr(self.gui.script_runner, '_pause_event'):
            self.gui.script_runner._pause_event.wait()  # Block if paused
        time.sleep(seconds)
        
    def random_wait(self, base_seconds, variance_seconds):
        """Wait with random variance"""
        actual_wait = base_seconds + random.uniform(-variance_seconds, variance_seconds)
        actual_wait = max(0.1, actual_wait)  # Minimum 0.1 seconds
        self.log(f"Random wait: {actual_wait:.2f}s")
        self.wait(actual_wait)
        
    def log(self, message):
        """Enhanced logging with timestamps"""
        timestamp = time.strftime('%H:%M:%S')
        if hasattr(self.gui, 'log_message'):
            self.gui.log_message(f"[{timestamp}] {message}")
        if self._debug_mode:
            print(f"[DEBUG {timestamp}] {message}")

    def _send_key_input(self, vk_code, key_up=False):
        """Send keyboard input using SendInput"""
        ki = KEYBDINPUT(vk_code, 0, KEYEVENTF_KEYUP if key_up else 0, 0, None)
        input_struct = INPUT(INPUT_KEYBOARD, INPUT._INPUT(ki=ki))
        user32.SendInput(1, ctypes.byref(input_struct), ctypes.sizeof(INPUT))

    def _perform_foreground_click(self, x, y, button='left', modifiers=[]):
        """Improved foreground clicking with better modifier support"""
        try:
            # Clamp coordinates to window bounds
            hwnd = self.gui.selected_window
            left, top, right, bottom = _get_true_hwnd_rect(hwnd)
            clamped_x = max(left, min(right - 1, x))
            clamped_y = max(top, min(bottom - 1, y))
            if (clamped_x, clamped_y) != (x, y):
                self.log(f"Clamped click from ({x},{y}) to ({clamped_x},{clamped_y})")
                x, y = clamped_x, clamped_y
            
            # Press modifiers
            for mod in modifiers:
                if mod == 'shift':
                    pyautogui.keyDown('shift')
                elif mod == 'ctrl':
                    pyautogui.keyDown('ctrl')
                elif mod == 'alt':
                    pyautogui.keyDown('alt')
            
            # Small delay for stability
            time.sleep(0.01)
            
            # Perform click
            if button == 'middle':
                pyautogui.click(x, y, button='middle')
            else:
                pyautogui.click(x, y, button=button)
                
        except Exception as e:
            self.log(f"Foreground click error: {e}")
        finally:
            # Release modifiers (in reverse order)
            for mod in reversed(modifiers):
                if mod == 'shift':
                    pyautogui.keyUp('shift')
                elif mod == 'ctrl':
                    pyautogui.keyUp('ctrl')
                elif mod == 'alt':
                    pyautogui.keyUp('alt')

    def click_within_region(self, region_index, x_offset=None, y_offset=None, button='left', modifiers=[]):
        """
        Click at a specific position within a region, ensuring the click stays within region bounds.
        If no offset is provided, clicks at the center of the region.
        """
        if not self.is_running: return False
        self.log(f"Executing click_within_region: region={region_index}, button='{button}', modifiers={modifiers}")

        if region_index >= len(self.gui.regions): 
            self.log(f"Error: Region {region_index} does not exist.")
            return False
            
        region = self.gui.regions[region_index]
        hwnd = self.gui.selected_window
        
        try:
            # Get accurate window position
            left, top, right, bottom = _get_true_hwnd_rect(hwnd)
            
            # Calculate position within region
            if x_offset is None: x_offset = region['width'] // 2
            if y_offset is None: y_offset = region['height'] // 2
                
            # Ensure offset is within region bounds
            x_offset = max(0, min(region['width'] - 1, x_offset))
            y_offset = max(0, min(region['height'] - 1, y_offset))
            
            # Convert to screen coordinates
            screen_x = left + region['x'] + x_offset
            screen_y = top + region['y'] + y_offset
            
            self.log(f"Calculated click position: screen_x={screen_x}, screen_y={screen_y}")
            
            # Always use foreground clicking for reliability
            self.log("Activating window for foreground click...")
            win32gui.SetForegroundWindow(hwnd)
            self.wait(0.1)

            self.log("Performing foreground click...")
            self._perform_foreground_click(screen_x, screen_y, button, modifiers)
            self.log(f"✅ SUCCESS: Clicked within Region {region_index} at ({screen_x}, {screen_y})")
            return True
            
        except Exception as e:
            self.log(f"❌ ERROR in click_within_region: {e}")
            return False

    def click_region(self, region_index, button='left', modifiers=[]):
        """Enhanced region clicking with strict confinement to region bounds"""
        if not self.is_running: return False
        if region_index >= len(self.gui.regions): 
            self.log(f"Error: Region {region_index} does not exist.")
            return False
            
        # Use our new method that ensures clicks stay within region bounds
        return self.click_within_region(region_index, None, None, button, modifiers)

    def find_and_click_color(self, hex_color, region_index, button='left', modifiers=[], tolerance=10):
        """Enhanced color finding with improved accuracy and strict region confinement"""
        if not self.is_running: return False
        self.log(f"Executing find_and_click_color: region={region_index}, color='{hex_color}', tolerance={tolerance}")

        if region_index >= len(self.gui.regions): 
            self.log(f"Error: Region {region_index} does not exist.")
            return False
            
        region = self.gui.regions[region_index]
        hwnd = self.gui.selected_window
        target_rgb = tuple(int(hex_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        
        try:
            # Get accurate window position
            left, top, right, bottom = _get_true_hwnd_rect(hwnd)
            if (right - left) <= 0 or (bottom - top) <= 0:
                self.log(f"Error: Target window has zero or negative size: ({left},{top},{right},{bottom})")
                return False
            
            # Calculate screenshot region - ensure we stay within window bounds
            region_left = max(0, region['x'])
            region_top = max(0, region['y'])
            region_right = min(right - left, region['x'] + region['width'])
            region_bottom = min(bottom - top, region['y'] + region['height'])
            
            # Convert to screen coordinates
            screenshot_x = left + region_left
            screenshot_y = top + region_top
            screenshot_w = region_right - region_left
            screenshot_h = region_bottom - region_top
            
            if screenshot_w <= 0 or screenshot_h <= 0:
                self.log(f"Error: Screenshot region has zero or negative size: w={screenshot_w}, h={screenshot_h}")
                return False

            self.log(f"Taking screenshot of region: ({screenshot_x}, {screenshot_y}, {screenshot_w}, {screenshot_h})")
            screenshot = pyautogui.screenshot(region=(screenshot_x, screenshot_y, screenshot_w, screenshot_h))
            if screenshot is None:
                self.log("Screenshot failed (returned None).")
                return False

            screenshot_array = np.array(screenshot)
            
            # Find pixels matching the color within tolerance
            self.log(f"Searching for color {target_rgb}...")
            color_diff = np.abs(screenshot_array - target_rgb)
            matches = np.where(np.all(color_diff <= tolerance, axis=2))
            
            if len(matches[0]) > 0:
                rel_y, rel_x = matches[0][0], matches[1][0]
                self.log(f"Color found at relative coords ({rel_x}, {rel_y})")
                
                # Convert to screen coordinates
                screen_x = screenshot_x + rel_x
                screen_y = screenshot_y + rel_y
                
                # Perform the click (always foreground)
                self.log(f"Activating window for foreground click at ({screen_x}, {screen_y})...")
                win32gui.SetForegroundWindow(hwnd)
                self.wait(0.1)
                self._perform_foreground_click(screen_x, screen_y, button, modifiers)
                self.log(f"✅ SUCCESS: Found color {hex_color} and clicked at ({screen_x}, {screen_y})")
                return True
            else:
                self.log(f"Color {hex_color} not found in region {region_index}.")
                return False
                
        except Exception as e:
            self.log(f"❌ ERROR in find_and_click_color: {e}")
            return False

    def get_pixel_color(self, region_index, x_offset=None, y_offset=None):
        """Get the color of a pixel in a region (useful for debugging)"""
        if not self.is_running: return None
        if region_index >= len(self.gui.regions): 
            self.log(f"Error: Region {region_index} does not exist.")
            return None
            
        region = self.gui.regions[region_index]
        hwnd = self.gui.selected_window
        
        try:
            left, top, right, bottom = _get_true_hwnd_rect(hwnd)
            
            # Use center of region if no offset specified
            if x_offset is None:
                x_offset = region['width'] // 2
            if y_offset is None:
                y_offset = region['height'] // 2
            
            screen_x = left + region['x'] + x_offset
            screen_y = top + region['y'] + y_offset
            
            # Take 1x1 screenshot
            pixel_screenshot = pyautogui.screenshot(region=(screen_x, screen_y, 1, 1))
            rgb = pixel_screenshot.getpixel((0, 0))
            hex_color = '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])
            
            self.log(f"Pixel at ({screen_x}, {screen_y}): RGB{rgb} = {hex_color}")
            return hex_color
            
        except Exception as e:
            self.log(f"Error getting pixel color: {e}")
            return None

    def is_point_in_any_region(self, x, y):
        """Check if a screen coordinate is within any defined region"""
        if not self.is_running: return False
        if not self.gui.regions:
            return False
            
        hwnd = self.gui.selected_window
        try:
            left, top, right, bottom = _get_true_hwnd_rect(hwnd)
            
            # Convert screen coordinates to window-relative coordinates
            win_x = x - left
            win_y = y - top
            
            # Check if the point is within any region
            for i, region in enumerate(self.gui.regions):
                if (region['x'] <= win_x < region['x'] + region['width'] and
                    region['y'] <= win_y < region['y'] + region['height']):
                    if self._debug_mode:
                        self.log(f"Point ({x}, {y}) is within Region {i}")
                    return True
                
            if self._debug_mode:
                self.log(f"Point ({x}, {y}) is not within any defined region")
            return False
            
        except Exception as e:
            self.log(f"Error checking if point is in region: {e}")
            return False

    def is_color_present(self, hex_color, region_index, tolerance=10):
        """Check if a color is present in a region without clicking"""
        if not self.is_running: return False
        if region_index >= len(self.gui.regions): 
            self.log(f"Error: Region {region_index} does not exist.")
            return False
            
        region = self.gui.regions[region_index]
        hwnd = self.gui.selected_window
        target_rgb = tuple(int(hex_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        
        try:
            left, top, right, bottom = _get_true_hwnd_rect(hwnd)
            
            screenshot_x = left + region['x']
            screenshot_y = top + region['y']
            screenshot_w = region['width']
            screenshot_h = region['height']
            
            screenshot = pyautogui.screenshot(region=(screenshot_x, screenshot_y, screenshot_w, screenshot_h))
            screenshot_array = np.array(screenshot)
            
            color_diff = np.abs(screenshot_array - target_rgb)
            matches = np.where(np.all(color_diff <= tolerance, axis=2))
            
            found = len(matches[0]) > 0
            if found:
                self.log(f"✅ Color {hex_color} found in Region {region_index}")
            else:
                self.log(f"❌ Color {hex_color} not found in Region {region_index}")
                
            return found
            
        except Exception as e:
            self.log(f"Error checking color presence: {e}")
            return False

    def wait_for_color(self, hex_color, region_index, timeout=30, tolerance=10, check_interval=0.5):
        """Wait for a color to appear in a region"""
        if not self.is_running: return False
        self.log(f"Waiting for color {hex_color} in Region {region_index} (timeout: {timeout}s)")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.is_running:
                self.log("Wait for color cancelled - bot stopped")
                return False
                
            if self.is_color_present(hex_color, region_index, tolerance):
                elapsed = time.time() - start_time
                self.log(f"✅ Color appeared after {elapsed:.1f}s")
                return True
                
            self.wait(check_interval)
        
        self.log(f"❌ Color {hex_color} did not appear within {timeout}s timeout")
        return False

    def type_text(self, text, delay=0.05):
        """Type text with optional delay between characters"""
        if not self.is_running: return False
        try:
            if delay > 0:
                for char in text:
                    if not self.is_running: break
                    pyautogui.write(char)
                    self.wait(delay)
            else:
                pyautogui.write(text)

            self.log(f"✅ Typed text: '{text}'")
            return True

        except Exception as e:
            self.log(f"Error typing text: {e}")
            return False

    def press_key(self, key, modifiers=[]):
        """Press a key with optional modifiers"""
        if not self.is_running: return False
        try:
            for mod in modifiers:
                pyautogui.keyDown(mod)

            pyautogui.press(key)

            for mod in reversed(modifiers):
                pyautogui.keyUp(mod)

            mod_str = "+".join(modifiers + [key])
            self.log(f"✅ Pressed key: {mod_str}")
            return True

        except Exception as e:
            self.log(f"Error pressing key: {e}")
            return False

    def scroll(self, region_index, clicks=3, direction='up', background=True):
        """Scroll in a region"""
        if not self.is_running: return False
        if region_index >= len(self.gui.regions):
            self.log(f"Error: Region {region_index} does not exist.")
            return False
            
        region = self.gui.regions[region_index]
        hwnd = self.gui.selected_window
        
        try:
            left, top, right, bottom = _get_true_hwnd_rect(hwnd)
            
            center_x = left + region['x'] + region['width'] // 2
            center_y = top + region['y'] + region['height'] // 2

            scroll_amount = clicks if direction == 'up' else -clicks
            
            if background:
                # Move mouse to position first
                self.move_mouse(region_index, background=True)
                self.wait(0.1)
            else:
                win32gui.SetForegroundWindow(hwnd)
                self.wait(0.1)
                pyautogui.moveTo(center_x, center_y)
            
            pyautogui.scroll(scroll_amount, x=center_x, y=center_y)

            self.log(f"✅ Scrolled {direction} {clicks} clicks in Region {region_index}")
            return True
            
        except Exception as e:
            self.log(f"Error scrolling: {e}")
            return False

    def type_text(self, text, delay=0.05):
        """Type text with optional delay between characters"""
        if not self.is_running: return False
        try:
            if delay > 0:
                for char in text:
                    if not self.is_running: break
                    pyautogui.write(char)
                    self.wait(delay)
            else:
                pyautogui.write(text)
            
            self.log(f"✅ Typed text: '{text}'")
            return True
            
        except Exception as e:
            self.log(f"Error typing text: {e}")
            return False

    def press_key(self, key, modifiers=[]):
        """Press a key with optional modifiers"""
        if not self.is_running: return False
        try:
            for mod in modifiers:
                pyautogui.keyDown(mod)
            
            pyautogui.press(key)
            
            for mod in reversed(modifiers):
                pyautogui.keyUp(mod)
            
            mod_str = "+".join(modifiers + [key])
            self.log(f"✅ Pressed key: {mod_str}")
            return True
            
        except Exception as e:
            self.log(f"Error pressing key: {e}")
            return False

    def scroll(self, region_index, clicks=3, direction='up', background=True):
        """Scroll in a region"""
        if not self.is_running: return False
        if region_index >= len(self.gui.regions):
            self.log(f"Error: Region {region_index} does not exist.")
            return False
            
        region = self.gui.regions[region_index]
        hwnd = self.gui.selected_window
        
        try:
            left, top, right, bottom = _get_true_hwnd_rect(hwnd)
            
            center_x = left + region['x'] + region['width'] // 2
            center_y = top + region['y'] + region['height'] // 2
            
            scroll_amount = clicks if direction == 'up' else -clicks
            
            if background:
                # Move mouse to position first
                self.move_mouse(region_index, background=True)
                self.wait(0.1)
            else:
                win32gui.SetForegroundWindow(hwnd)
                self.wait(0.1)
                pyautogui.moveTo(center_x, center_y)
            
            pyautogui.scroll(scroll_amount, x=center_x, y=center_y)
            
            self.log(f"✅ Scrolled {direction} {clicks} clicks in Region {region_index}")
            return True
            
        except Exception as e:
            self.log(f"Error scrolling: {e}")
            return False