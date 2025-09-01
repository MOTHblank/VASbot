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
        if not user32.IsWindow(hwnd):
            return 0, 0, 0, 0

        client_rect = wintypes.RECT()
        user32.GetClientRect(hwnd, ctypes.byref(client_rect))
        
        point_tl = wintypes.POINT(client_rect.left, client_rect.top)
        point_br = wintypes.POINT(client_rect.right, client_rect.bottom)
        
        user32.ClientToScreen(hwnd, ctypes.byref(point_tl))
        user32.ClientToScreen(hwnd, ctypes.byref(point_br))

        return point_tl.x, point_tl.y, point_br.x, point_br.y

    except Exception as e:
        print(f"Error in _get_true_hwnd_rect: {e}")
        # Fallback to GetWindowRect if everything else fails
        try:
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            return rect.left, rect.top, rect.right, rect.bottom
        except Exception:
            return 0, 0, 0, 0

# Public alias for easier import
get_true_hwnd_rect = _get_true_hwnd_rect
