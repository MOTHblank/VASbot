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

    def _send_input_click(self, x, y, button='left', modifiers=[]):
        """Enhanced background clicking using SendInput with improved accuracy"""
        try:
            # Clamp coordinates to window bounds
            hwnd = self.gui.selected_window
            left, top, right, bottom = _get_true_hwnd_rect(hwnd)
            clamped_x = max(left, min(right - 1, x))
            clamped_y = max(top, min(bottom - 1, y))
            if (clamped_x, clamped_y) != (x, y):
                self.log(f"Clamped click from ({x},{y}) to ({clamped_x},{clamped_y})")
                x, y = clamped_x, clamped_y
            
            # Convert screen coordinates to normalized coordinates (0-65535)
            nx = int(x * 65535.0 / screen_width)
            ny = int(y * 65535.0 / screen_height)
            
            # Clamp values to valid range
            nx = max(0, min(65535, nx))
            ny = max(0, min(65535, ny))
            
            if self._debug_mode:
                self.log(f"Sending input click to screen ({x}, {y}) -> normalized ({nx}, {ny})")
            
            inputs = []
            
            # Press modifier keys first
            for mod in modifiers:
                if mod == 'shift':
                    ki = KEYBDINPUT(VK_SHIFT, 0, 0, 0, None)
                    inputs.append(INPUT(INPUT_KEYBOARD, INPUT._INPUT(ki=ki)))
                elif mod == 'ctrl':
                    ki = KEYBDINPUT(VK_CONTROL, 0, 0, 0, None)
                    inputs.append(INPUT(INPUT_KEYBOARD, INPUT._INPUT(ki=ki)))
                elif mod == 'alt':
                    ki = KEYBDINPUT(VK_MENU, 0, 0, 0, None)
                    inputs.append(INPUT(INPUT_KEYBOARD, INPUT._INPUT(ki=ki)))
            
            # Move mouse to position
            move_input = MOUSEINPUT(nx, ny, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, 0, None)
            inputs.append(INPUT(INPUT_MOUSE, INPUT._INPUT(mi=move_input)))
            
            # Mouse down
            if button == 'left':
                down_flags = MOUSEEVENTF_LEFTDOWN
                up_flags = MOUSEEVENTF_LEFTUP
            elif button == 'right':
                down_flags = MOUSEEVENTF_RIGHTDOWN
                up_flags = MOUSEEVENTF_RIGHTUP
            elif button == 'middle':
                down_flags = MOUSEEVENTF_MIDDLEDOWN
                up_flags = MOUSEEVENTF_MIDDLEUP
            else:
                down_flags = MOUSEEVENTF_LEFTDOWN
                up_flags = MOUSEEVENTF_LEFTUP
            
            down_input = MOUSEINPUT(nx, ny, 0, down_flags | MOUSEEVENTF_ABSOLUTE, 0, None)
            inputs.append(INPUT(INPUT_MOUSE, INPUT._INPUT(mi=down_input)))
            
            # Mouse up
            up_input = MOUSEINPUT(nx, ny, 0, up_flags | MOUSEEVENTF_ABSOLUTE, 0, None)
            inputs.append(INPUT(INPUT_MOUSE, INPUT._INPUT(mi=up_input)))
            
            # Release modifier keys (in reverse order)
            for mod in reversed(modifiers):
                if mod == 'shift':
                    ki = KEYBDINPUT(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0, None)
                    inputs.append(INPUT(INPUT_KEYBOARD, INPUT._INPUT(ki=ki)))
                elif mod == 'ctrl':
                    ki = KEYBDINPUT(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0, None)
                    inputs.append(INPUT(INPUT_KEYBOARD, INPUT._INPUT(ki=ki)))
                elif mod == 'alt':
                    ki = KEYBDINPUT(VK_MENU, 0, KEYEVENTF_KEYUP, 0, None)
                    inputs.append(INPUT(INPUT_KEYBOARD, INPUT._INPUT(ki=ki)))
            
            # Send all inputs at once
            if inputs:
                input_array = (INPUT * len(inputs))(*inputs)
                result = user32.SendInput(len(inputs), input_array, ctypes.sizeof(INPUT))
                
                if self._debug_mode:
                    self.log(f"SendInput result: {result}/{len(inputs)} inputs sent")
                    
                if result == 0:
                    error_code = kernel32.GetLastError()
                    self.log(f"SendInput failed with error code: {error_code}")
                    return False
                    
            return True
            
        except Exception as e:
            self.log(f"Background click error: {e}")
            return False

    def click_within_region(self, region_index, x_offset=None, y_offset=None, button='left', modifiers=[], background=True):
        """
        Click at a specific position within a region, ensuring the click stays within region bounds.
        If no offset is provided, clicks at the center of the region.
        """
        if not self.is_running: return False
        if region_index >= len(self.gui.regions): 
            self.log(f"Error: Region {region_index} does not exist.")
            return False
            
        region = self.gui.regions[region_index]
        hwnd = self.gui.selected_window
        
        try:
            # Get accurate window position
            left, top, right, bottom = _get_true_hwnd_rect(hwnd)
            
            # Calculate position within region
            if x_offset is None:
                x_offset = region['width'] // 2
            if y_offset is None:
                y_offset = region['height'] // 2
                
            # Ensure offset is within region bounds
            x_offset = max(0, min(region['width'] - 1, x_offset))
            y_offset = max(0, min(region['height'] - 1, y_offset))
            
            # Convert to screen coordinates
            screen_x = left + region['x'] + x_offset
            screen_y = top + region['y'] + y_offset
            
            if self._debug_mode:
                self.log(f"Clicking within region {region_index} at offset ({x_offset}, {y_offset}) -> screen ({screen_x}, {screen_y})")
            
            # Perform the click
            success = True
            if background:
                success = self._send_input_click(screen_x, screen_y, button, modifiers)
            else:
                try:
                    win32gui.SetForegroundWindow(hwnd)
                    self.wait(0.1)
                    self._perform_foreground_click(screen_x, screen_y, button, modifiers)
                except Exception as e:
                    self.log(f"Foreground activation error: {e}")
                    success = False
            
            if success:
                self.log(f"✅ Clicked within Region {region_index} at ({screen_x}, {screen_y})")
            else:
                self.log(f"❌ Failed to click within Region {region_index}")
                
            return success
            
        except Exception as e:
            self.log(f"Error in click_within_region: {e}")
            return False

    def click_region(self, region_index, button='left', modifiers=[], background=True):
        """Enhanced region clicking with strict confinement to region bounds"""
        if not self.is_running: return False
        if region_index >= len(self.gui.regions): 
            self.log(f"Error: Region {region_index} does not exist.")
            return False
            
        # Use our new method that ensures clicks stay within region bounds
        return self.click_within_region(region_index, None, None, button, modifiers, background)

    def find_and_click_color(self, hex_color, region_index, button='left', modifiers=[], background=True, tolerance=10):
        """Enhanced color finding with improved accuracy and strict region confinement"""
        if not self.is_running: return False
        if region_index >= len(self.gui.regions): 
            self.log(f"Error: Region {region_index} does not exist.")
            return False
            
        region = self.gui.regions[region_index]
        hwnd = self.gui.selected_window
        target_rgb = tuple(int(hex_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        mode = "background" if background else "foreground"
        
        try:
            # Get accurate window position
            left, top, right, bottom = _get_true_hwnd_rect(hwnd)
            
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
            
            if self._debug_mode:
                self.log(f"Screenshot region: ({screenshot_x}, {screenshot_y}, {screenshot_w}, {screenshot_h})")
                self.log(f"Looking for color {hex_color} (RGB: {target_rgb}) with tolerance {tolerance}")
            
            # Take screenshot of the region only
            screenshot = pyautogui.screenshot(region=(screenshot_x, screenshot_y, screenshot_w, screenshot_h))
            screenshot_array = np.array(screenshot)
            
            # Find pixels matching the color within tolerance
            color_diff = np.abs(screenshot_array - target_rgb)
            matches = np.where(np.all(color_diff <= tolerance, axis=2))
            
            if len(matches[0]) > 0:
                # Use the first match
                rel_y, rel_x = matches[0][0], matches[1][0]
                
                # Convert to screen coordinates, ensuring we stay within the region
                screen_x = screenshot_x + rel_x
                screen_y = screenshot_y + rel_y
                
                # Double-check that the click is within the region
                if (screen_x < screenshot_x or screen_x >= screenshot_x + screenshot_w or
                    screen_y < screenshot_y or screen_y >= screenshot_y + screenshot_h):
                    self.log(f"Error: Calculated click position ({screen_x}, {screen_y}) is outside region bounds")
                    return False
                
                if self._debug_mode:
                    self.log(f"Color found at relative ({rel_x}, {rel_y}) -> screen ({screen_x}, {screen_y})")
                
                # Perform the click
                success = True
                if background:
                    success = self._send_input_click(screen_x, screen_y, button, modifiers)
                else:
                    try:
                        win32gui.SetForegroundWindow(hwnd)
                        self.wait(0.1)
                        self._perform_foreground_click(screen_x, screen_y, button, modifiers)
                    except Exception as e:
                        self.log(f"Foreground activation error: {e}")
                        success = False
                
                if success:
                    self.log(f"✅ Found color {hex_color} and clicked ({mode}) at ({screen_x}, {screen_y})")
                else:
                    self.log(f"❌ Found color but failed to click ({mode})")
                    
                return success
            else:
                if self._debug_mode:
                    unique_colors = np.unique(screenshot_array.reshape(-1, 3), axis=0)
                    self.log(f"Color not found. Region contains {len(unique_colors)} unique colors")
                return False
                
        except Exception as e:
            self.log(f"Error in find_and_click_color: {e}")
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

    def move_mouse(self, region_index, x_offset=None, y_offset=None, background=True):
        """Move mouse to a specific position within a region, ensuring it stays within bounds"""
        if not self.is_running: return False
        if region_index >= len(self.gui.regions): 
            self.log(f"Error: Region {region_index} does not exist.")
            return False
            
        region = self.gui.regions[region_index]
        hwnd = self.gui.selected_window
        
        try:
            left, top, right, bottom = _get_true_hwnd_rect(hwnd)
            
            # Calculate position within region
            if x_offset is None:
                x_offset = region['width'] // 2
            if y_offset is None:
                y_offset = region['height'] // 2
                
            # Ensure offset is within region bounds
            x_offset = max(0, min(region['width'] - 1, x_offset))
            y_offset = max(0, min(region['height'] - 1, y_offset))
            
            # Convert to screen coordinates
            screen_x = left + region['x'] + x_offset
            screen_y = top + region['y'] + y_offset
            
            if background:
                # Use SendInput to move mouse
                nx = int(screen_x * 65535.0 / screen_width)
                ny = int(screen_y * 65535.0 / screen_height)
                
                move_input = MOUSEINPUT(nx, ny, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, 0, None)
                input_struct = INPUT(INPUT_MOUSE, INPUT._INPUT(mi=move_input))
                user32.SendInput(1, ctypes.byref(input_struct), ctypes.sizeof(INPUT))
            else:
                pyautogui.moveTo(screen_x, screen_y)
            
            self.log(f"Mouse moved to ({screen_x}, {screen_y}) within Region {region_index}")
            return True
            
        except Exception as e:
            self.log(f"Error moving mouse: {e}")
            return False

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

    def drag(self, from_region_index, to_region_index, button='left', background=True, duration=0.5):
        """Drag from one region to another"""
        if not self.is_running: return False
        if from_region_index >= len(self.gui.regions) or to_region_index >= len(self.gui.regions):
            self.log(f"Error: Invalid region index for drag operation")
            return False
            
        from_region = self.gui.regions[from_region_index]
        to_region = self.gui.regions[to_region_index]
        hwnd = self.gui.selected_window
        
        try:
            left, top, right, bottom = _get_true_hwnd_rect(hwnd)
            
            # Calculate positions
            from_x = left + from_region['x'] + from_region['width'] // 2
            from_y = top + from_region['y'] + from_region['height'] // 2
            to_x = left + to_region['x'] + to_region['width'] // 2
            to_y = top + to_region['y'] + to_region['height'] // 2
            
            if background:
                # Implement background drag using SendInput
                steps = 10  # Number of move steps for smooth drag
                sleep_per_step = duration / steps
                
                # Move to starting position
                nx = int(from_x * 65535.0 / screen_width)
                ny = int(from_y * 65535.0 / screen_height)
                move_input = MOUSEINPUT(nx, ny, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, 0, None)
                input_struct = INPUT(INPUT_MOUSE, INPUT._INPUT(mi=move_input))
                user32.SendInput(1, ctypes.byref(input_struct), ctypes.sizeof(INPUT))
                
                # Mouse down
                down_flags = MOUSEEVENTF_LEFTDOWN if button == 'left' else MOUSEEVENTF_RIGHTDOWN if button == 'right' else MOUSEEVENTF_MIDDLEDOWN
                down_input = MOUSEINPUT(nx, ny, 0, down_flags | MOUSEEVENTF_ABSOLUTE, 0, None)
                input_struct = INPUT(INPUT_MOUSE, INPUT._INPUT(mi=down_input))
                user32.SendInput(1, ctypes.byref(input_struct), ctypes.sizeof(INPUT))
                
                # Move in steps
                for i in range(1, steps + 1):
                    curr_x = from_x + (to_x - from_x) * (i / steps)
                    curr_y = from_y + (to_y - from_y) * (i / steps)
                    nx = int(curr_x * 65535.0 / screen_width)
                    ny = int(curr_y * 65535.0 / screen_height)
                    move_input = MOUSEINPUT(nx, ny, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, 0, None)
                    input_struct = INPUT(INPUT_MOUSE, INPUT._INPUT(mi=move_input))
                    user32.SendInput(1, ctypes.byref(input_struct), ctypes.sizeof(INPUT))
                    time.sleep(sleep_per_step)
                
                # Mouse up
                up_flags = MOUSEEVENTF_LEFTUP if button == 'left' else MOUSEEVENTF_RIGHTUP if button == 'right' else MOUSEEVENTF_MIDDLEUP
                up_input = MOUSEINPUT(nx, ny, 0, up_flags | MOUSEEVENTF_ABSOLUTE, 0, None)
                input_struct = INPUT(INPUT_MOUSE, INPUT._INPUT(mi=up_input))
                user32.SendInput(1, ctypes.byref(input_struct), ctypes.sizeof(INPUT))
            else:
                win32gui.SetForegroundWindow(hwnd)
                self.wait(0.1)
                pyautogui.moveTo(from_x, from_y)
                pyautogui.drag(to_x - from_x, to_y - from_y, duration=duration, button=button)
            
            self.log(f"✅ Dragged from Region {from_region_index} to Region {to_region_index}")
            return True
            
        except Exception as e:
            self.log(f"Error during drag operation: {e}")
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