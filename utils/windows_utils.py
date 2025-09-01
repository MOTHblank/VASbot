import ctypes
from ctypes import wintypes
try:
    import win32gui, win32api, win32con
except ImportError:
    win32gui = win32api = win32con = None

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi
DWMWA_EXTENDED_FRAME_BOUNDS = 9


def _get_true_hwnd_rect(hwnd):
    """
    Gets the true screen coordinates of a window's client area.
    This is a more reliable method that avoids issues with DWM and scaling.
    """
    try:
        if not win32gui or not win32gui.IsWindow(hwnd):
            return 0, 0, 0, 0

        # Get the client rectangle, which is relative to the window's top-left corner
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        
        # Convert the client area's top-left and bottom-right points to screen coordinates
        screen_left, screen_top = win32gui.ClientToScreen(hwnd, (left, top))
        screen_right, screen_bottom = win32gui.ClientToScreen(hwnd, (right, bottom))
        
        return screen_left, screen_top, screen_right, screen_bottom

    except Exception as e:
        print(f"Error in _get_true_hwnd_rect: {e}")
        # Fallback to GetWindowRect if everything else fails
        try:
            rect = win32gui.GetWindowRect(hwnd)
            return rect[0], rect[1], rect[2], rect[3]
        except Exception:
            return 0, 0, 0, 0

# Public alias for easier import
get_true_hwnd_rect = _get_true_hwnd_rect
