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
    Enhanced function to get the true, physical bounding box of a window's client area.
    Handles maximized windows correctly by accounting for window state and client area.
    """
    rect = wintypes.RECT()
    
    try:
        # Check if window is maximized
        if win32gui:
            window_style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            if window_style & win32con.WS_MAXIMIZE:
                # For maximized windows, we need special handling
                # Get the monitor info where the window is located
                monitor_info = win32api.GetMonitorInfo(
                    win32api.MonitorFromWindow(hwnd, win32con.MONITOR_DEFAULTTONEAREST)
                )
                
                # Get the work area (excluding taskbar)
                work_area = monitor_info['Work']
                
                # For maximized windows, the client area is typically the entire work area
                # but we need to account for any borders or title bar that might still be visible
                try:
                    # Try to get the client area
                    client_rect = wintypes.RECT()
                    if win32gui.GetClientRect(hwnd, ctypes.byref(client_rect)):
                        # Convert client area to screen coordinates
                        point1 = wintypes.POINT(0, 0)
                        point2 = wintypes.POINT(client_rect.right, client_rect.bottom)
                        win32gui.ClientToScreen(hwnd, ctypes.byref(point1))
                        win32gui.ClientToScreen(hwnd, ctypes.byref(point2))
                        return point1.x, point1.y, point2.x, point2.y
                except:
                    pass
                
                # Fallback to work area for maximized windows
                return work_area[0], work_area[1], work_area[2], work_area[3]
        
        # For non-maximized windows, try DWM first (Windows Vista+)
        try:
            result = dwmapi.DwmGetWindowAttribute(
                hwnd, 
                DWMWA_EXTENDED_FRAME_BOUNDS, 
                ctypes.byref(rect), 
                ctypes.sizeof(rect)
            )
            if result == 0:  # S_OK
                # For non-maximized windows, we need to adjust for the client area
                try:
                    # Get window position
                    window_rect = wintypes.RECT()
                    win32gui.GetWindowRect(hwnd, ctypes.byref(window_rect))
                    
                    # Get client area
                    client_rect = wintypes.RECT()
                    if win32gui.GetClientRect(hwnd, ctypes.byref(client_rect)):
                        # Calculate the difference between window and client area
                        window_width = window_rect.right - window_rect.left
                        window_height = window_rect.bottom - window_rect.top
                        client_width = client_rect.right
                        client_height = client_rect.bottom
                        
                        # Calculate borders
                        border_width = (window_width - client_width) // 2
                        title_height = window_height - client_height - border_width
                        
                        # Adjust the DWM rect to get client area
                        left = rect.left + border_width
                        top = rect.top + title_height
                        right = rect.right - border_width
                        bottom = rect.bottom - border_width
                        
                        return left, top, right, bottom
                except:
                    pass
                
                # If client area adjustment fails, return the DWM rect
                return rect.left, rect.top, rect.right, rect.bottom
        except:
            pass
        
        # Fallback to standard GetWindowRect with client area adjustment
        try:
            if win32gui:
                # Get window position
                window_rect = wintypes.RECT()
                win32gui.GetWindowRect(hwnd, ctypes.byref(window_rect))
                
                # Get client area
                client_rect = wintypes.RECT()
                if win32gui.GetClientRect(hwnd, ctypes.byref(client_rect)):
                    # Convert client area to screen coordinates
                    point1 = wintypes.POINT(0, 0)
                    point2 = wintypes.POINT(client_rect.right, client_rect.bottom)
                    win32gui.ClientToScreen(hwnd, ctypes.byref(point1))
                    win32gui.ClientToScreen(hwnd, ctypes.byref(point2))
                    return point1.x, point1.y, point2.x, point2.y
                else:
                    # Fallback to window rect
                    return window_rect.left, window_rect.top, window_rect.right, window_rect.bottom
        except:
            pass
        
    except Exception as e:
        print(f"Error getting window rect: {e}")
    
    # Last resort fallback
        return 0, 0, 800, 600

# Public alias for easier import
get_true_hwnd_rect = _get_true_hwnd_rect
