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
        client_rect = win32gui.GetClientRect(hwnd)
        
        # Convert the client area's top-left and bottom-right points to screen coordinates
        point_tl = wintypes.POINT(client_rect[0], client_rect[1])
        point_br = wintypes.POINT(client_rect[2], client_rect[3])
        
        win32gui.ClientToScreen(hwnd, ctypes.byref(point_tl))
        win32gui.ClientToScreen(hwnd, ctypes.byref(point_br))
        
        return point_tl.x, point_tl.y, point_br.x, point_br.y

    except Exception as e:
        print(f"Error in _get_true_hwnd_rect: {e}")
        # Fallback to GetWindowRect if ClientToScreen fails for some reason
        try:
            rect = win32gui.GetWindowRect(hwnd)
            return rect[0], rect[1], rect[2], rect[3]
        except Exception:
            return 0, 0, 0, 0

# Public alias for easier import
get_true_hwnd_rect = _get_true_hwnd_rect
