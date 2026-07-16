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
    if not hwnd:
        return 0, 0, 0, 0

    # Try win32gui first if available (handles 64-bit HWND handles robustly)
    if win32gui is not None:
        try:
            if win32gui.IsWindow(hwnd):
                # win32gui.GetClientRect returns (left, top, right, bottom) -> (0, 0, width, height)
                _, _, w, h = win32gui.GetClientRect(hwnd)
                # win32gui.ClientToScreen returns (x, y) in screen coordinates
                left, top = win32gui.ClientToScreen(hwnd, (0, 0))
                return left, top, left + w, top + h
        except Exception as e:
            print(f"Error in _get_true_hwnd_rect (win32gui): {e}")

    # Fallback to ctypes with explicit 64-bit argtypes configuration
    try:
        user32.IsWindow.argtypes = [wintypes.HWND]
        user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]

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
        print(f"Error in _get_true_hwnd_rect (ctypes): {e}")
        # Fallback to GetWindowRect if everything else fails
        try:
            user32.GetWindowRect.argtypes = [
                wintypes.HWND,
                ctypes.POINTER(wintypes.RECT),
            ]
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            return rect.left, rect.top, rect.right, rect.bottom
        except Exception:
            return 0, 0, 0, 0


# Public alias for easier import
get_true_hwnd_rect = _get_true_hwnd_rect


def get_display_info():
    """Gets information about all connected displays."""
    if not win32api:
        return []

    displays = []
    for hmonitor, _, _ in win32api.EnumDisplayMonitors():
        try:
            monitor_info = win32api.GetMonitorInfo(hmonitor)
            displays.append(
                {
                    "handle": hmonitor,
                    "rect": monitor_info["Monitor"],
                    "work_rect": monitor_info["Work"],
                    "is_primary": monitor_info["Flags"]
                    == win32con.MONITORINFOF_PRIMARY,
                }
            )
        except Exception as e:
            print(f"Error getting monitor info: {e}")
    return displays
