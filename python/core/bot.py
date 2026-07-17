import ctypes
import time
import random
from ctypes import wintypes

# C struct redefinitions
PUL = ctypes.POINTER(ctypes.c_ulong)


class KeyBdInput(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", PUL),
    ]


class HardwareInput(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", PUL),
    ]


class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput), ("mi", MouseInput), ("hi", HardwareInput)]


class Input(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("ii", Input_I)]


# Constants
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

KEYEVENTF_KEYDOWN = 0x0000
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000
MOUSEEVENTF_WHEEL = 0x0800

# Virtual Key Codes
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt key

KEY_MAP = {
    "a": 0x41,
    "b": 0x42,
    "c": 0x43,
    "d": 0x44,
    "e": 0x45,
    "f": 0x46,
    "g": 0x47,
    "h": 0x48,
    "i": 0x49,
    "j": 0x4A,
    "k": 0x4B,
    "l": 0x4C,
    "m": 0x4D,
    "n": 0x4E,
    "o": 0x4F,
    "p": 0x50,
    "q": 0x51,
    "r": 0x52,
    "s": 0x53,
    "t": 0x54,
    "u": 0x55,
    "v": 0x56,
    "w": 0x57,
    "x": 0x58,
    "y": 0x59,
    "z": 0x5A,
    "f1": 0x70,
    "f2": 0x71,
    "f3": 0x72,
    "f4": 0x73,
    "f5": 0x74,
    "f6": 0x75,
    "f7": 0x76,
    "f8": 0x77,
    "f9": 0x78,
    "f10": 0x79,
    "f11": 0x7A,
    "f12": 0x7B,
    "enter": 0x0D,
    "esc": 0x1B,
    "tab": 0x09,
    "backspace": 0x08,
    "delete": 0x2E,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "shift": VK_SHIFT,
    "ctrl": VK_CONTROL,
    "alt": VK_MENU,
}


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class Bot:
    """Provides low-level control over mouse and keyboard input using ctypes and SendInput."""

    def __init__(self):
        self._debug_mode = True  # Enable debug logging for troubleshooting
        # Initialize user32 with explicit signatures
        self.user32 = ctypes.windll.user32

        # SetCursorPos
        self.user32.SetCursorPos.argtypes = [ctypes.c_long, ctypes.c_long]
        self.user32.SetCursorPos.restype = (
            ctypes.c_int
        )  # Returns BOOL (non-zero success)

        # GetCursorPos
        self.user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
        self.user32.GetCursorPos.restype = ctypes.c_int

        # SendInput
        self.user32.SendInput.argtypes = [
            ctypes.c_uint,
            ctypes.POINTER(Input),
            ctypes.c_int,
        ]
        self.user32.SendInput.restype = ctypes.c_uint

        # mouse_event (deprecated but robust fallback)
        self.user32.mouse_event.argtypes = [
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.c_ulong,
        ]
        self.user32.mouse_event.restype = None

    def get_cursor_pos(self):
        pt = POINT()
        self.user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    def human_move_to(self, target_x, target_y, duration=0.06, steps=8):
        """Moves the mouse to the target coordinates using a Bezier curve to simulate human movement.
        Fast but not instant — still uses a curved path so it doesn't look robotic.
        """
        start_x, start_y = self.get_cursor_pos()

        # Calculate distance to scale the curve's 'waviness'
        dist = ((target_x - start_x) ** 2 + (target_y - start_y) ** 2) ** 0.5
        if dist < 5:
            self.move_to(target_x, target_y)
            time.sleep(random.uniform(0.02, 0.05))
            return

        # Define control points for the Bezier curve
        # Make it much closer to a straight line (max 10% of distance or 20px)
        max_offset = min(20, dist * 0.1)
        offset_x = random.uniform(-max_offset, max_offset)
        offset_y = random.uniform(-max_offset, max_offset)

        # Control points at 1/3 and 2/3 of the path
        cp1_x = start_x + (target_x - start_x) * 0.33 + offset_x
        cp1_y = start_y + (target_y - start_y) * 0.33 + offset_y
        cp2_x = start_x + (target_x - start_x) * 0.66 - offset_x
        cp2_y = start_y + (target_y - start_y) * 0.66 - offset_y

        sleep_time = duration / steps

        for i in range(1, steps + 1):
            t = i / steps

            # Cubic Bezier formula
            x = (
                (1 - t) ** 3 * start_x
                + 3 * (1 - t) ** 2 * t * cp1_x
                + 3 * (1 - t) * t**2 * cp2_x
                + t**3 * target_x
            )
            y = (
                (1 - t) ** 3 * start_y
                + 3 * (1 - t) ** 2 * t * cp1_y
                + 3 * (1 - t) * t**2 * cp2_y
                + t**3 * target_y
            )

            self.move_to(int(x), int(y))
            time.sleep(sleep_time)

        # Brief rest on the final position before clicking
        time.sleep(random.uniform(0.02, 0.06))

    def _send_input(self, inputs):
        """Internal method to send a list of INPUT structures to the OS."""
        n_inputs = len(inputs)
        inputs_arr = (Input * n_inputs)(*inputs)
        try:
            result = self.user32.SendInput(n_inputs, inputs_arr, ctypes.sizeof(Input))
            if result != n_inputs:
                err = ctypes.get_last_error()
                print(
                    f"Bot: SendInput failed! Sent {result}/{n_inputs}. Error code: {err}"
                )
                if err == 5:  # ERROR_ACCESS_DENIED
                    print("Bot: ACCESS DENIED. Please run as Administrator!")
            return result
        except Exception as e:
            print(f"Bot: Exception in SendInput: {e}")
            return 0

    def move_to(self, x, y):
        """Moves the mouse to the specified absolute screen coordinates.
        Attempts SetCursorPos first, then falls back to SendInput with VIRTUALDESK support.
        """
        x = int(x)
        y = int(y)

        # Method 1: SetCursorPos (Direct & Simple)
        # This is usually the most reliable for "teleporting" the mouse.
        ret = self.user32.SetCursorPos(x, y)

        if ret == 0:
            # If SetCursorPos failed, try SendInput with Virtual Desktop support
            err = ctypes.get_last_error()
            if self._debug_mode:
                print(
                    f"Bot: SetCursorPos({x}, {y}) failed. Error: {err}. Trying SendInput..."
                )

            # Method 2: SendInput (Robust Multi-Monitor)
            v_left = self.user32.GetSystemMetrics(76)
            v_top = self.user32.GetSystemMetrics(77)
            v_width = self.user32.GetSystemMetrics(78)
            v_height = self.user32.GetSystemMetrics(79)

            # Normalize to 0-65535 range across the virtual desktop
            abs_x = x - v_left
            abs_y = y - v_top
            nx = int((abs_x / v_width) * 65535)
            ny = int((abs_y / v_height) * 65535)

            # Clamp
            nx = max(0, min(65535, nx))
            ny = max(0, min(65535, ny))

            # 0x8000=ABSOLUTE, 0x0001=MOVE, 0x4000=VIRTUALDESK
            mouse_input = MouseInput(dx=nx, dy=ny, dwFlags=0x8000 | 0x0001 | 0x4000)
            input_entry = Input(type=INPUT_MOUSE, ii=Input_I(mi=mouse_input))
            self._send_input([input_entry])

        # Always verify/finalize with a tiny relative move to trigger hooks
        mouse_input = MouseInput(dx=0, dy=0, dwFlags=0x0001)  # MOUSEEVENTF_MOVE
        input_entry = Input(type=INPUT_MOUSE, ii=Input_I(mi=mouse_input))
        self._send_input([input_entry])

    def press_button(self, button="left", down=True):
        """Presses or releases a mouse button."""
        if button == "left":
            dwFlags = MOUSEEVENTF_LEFTDOWN if down else MOUSEEVENTF_LEFTUP
        elif button == "right":
            dwFlags = MOUSEEVENTF_RIGHTDOWN if down else MOUSEEVENTF_RIGHTUP
        else:  # middle
            dwFlags = MOUSEEVENTF_MIDDLEDOWN if down else MOUSEEVENTF_MIDDLEUP

        self._send_input(
            [Input(type=INPUT_MOUSE, ii=Input_I(mi=MouseInput(dwFlags=dwFlags)))]
        )

    def scroll(self, clicks, x=None, y=None):
        """Scrolls the mouse wheel by the given amount."""
        if x is not None and y is not None:
            self.move_to(x, y)
            time.sleep(0.05)

        # mouseData represents wheel movement where one click is usually 120
        # Positive values scroll forward/up, negative values scroll backward/down
        mouseData = int(clicks * 120)
        self._send_input(
            [
                Input(
                    type=INPUT_MOUSE,
                    ii=Input_I(
                        mi=MouseInput(dwFlags=MOUSEEVENTF_WHEEL, mouseData=mouseData)
                    ),
                )
            ]
        )

    def key_down(self, key):
        """Presses and holds a keyboard key."""
        if key in KEY_MAP:
            self._send_input(
                [
                    Input(
                        type=INPUT_KEYBOARD,
                        ii=Input_I(
                            ki=KeyBdInput(wVk=KEY_MAP[key], dwFlags=KEYEVENTF_KEYDOWN)
                        ),
                    )
                ]
            )

    def key_up(self, key):
        """Releases a keyboard key."""
        if key in KEY_MAP:
            self._send_input(
                [
                    Input(
                        type=INPUT_KEYBOARD,
                        ii=Input_I(
                            ki=KeyBdInput(wVk=KEY_MAP[key], dwFlags=KEYEVENTF_KEYUP)
                        ),
                    )
                ]
            )

    def double_click(self, x, y, button="left", modifiers=None):
        """Performs a double mouse click at the specified coordinates."""
        if modifiers is None:
            modifiers = []
        self.click(x, y, button, modifiers)
        time.sleep(0.05)
        self.click(x, y, button, modifiers)

    def click(self, x, y, button="left", modifiers=None):
        """Performs a mouse click at the specified coordinates with optional modifiers."""
        if modifiers is None:
            modifiers = []
        self.move_to(x, y)
        # Settle delay: ensures movement is complete before click action begins
        time.sleep(0.05)

        mod_inputs_down = [
            Input(
                type=INPUT_KEYBOARD,
                ii=Input_I(ki=KeyBdInput(wVk=KEY_MAP[mod], dwFlags=KEYEVENTF_KEYDOWN)),
            )
            for mod in modifiers
            if mod in KEY_MAP
        ]
        if mod_inputs_down:
            self._send_input(mod_inputs_down)

        if button == "left":
            down, up = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP
        elif button == "right":
            down, up = MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
        else:  # middle
            down, up = MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP

        self._send_input(
            [Input(type=INPUT_MOUSE, ii=Input_I(mi=MouseInput(dwFlags=down)))]
        )
        time.sleep(random.uniform(0.05, 0.1))
        self._send_input(
            [Input(type=INPUT_MOUSE, ii=Input_I(mi=MouseInput(dwFlags=up)))]
        )

        mod_inputs_up = [
            Input(
                type=INPUT_KEYBOARD,
                ii=Input_I(ki=KeyBdInput(wVk=KEY_MAP[mod], dwFlags=KEYEVENTF_KEYUP)),
            )
            for mod in reversed(modifiers)
            if mod in KEY_MAP
        ]
        if mod_inputs_up:
            self._send_input(mod_inputs_up)

    def type_text(self, text, delay=0.05):
        """Types the given text using unicode characters."""
        if delay <= 0:
            # ⚡ Bolt: Fast list comprehension to batch input events instead of repeated appends
            inputs = [
                Input(
                    type=INPUT_KEYBOARD,
                    ii=Input_I(ki=KeyBdInput(wVk=0, wScan=ord(char), dwFlags=flag)),
                )
                for char in text
                for flag in (KEYEVENTF_UNICODE, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)
            ]
            if inputs:
                self._send_input(inputs)
        else:
            for char in text:
                key_input_down = KeyBdInput(
                    wVk=0, wScan=ord(char), dwFlags=KEYEVENTF_UNICODE
                )
                key_input_up = KeyBdInput(
                    wVk=0, wScan=ord(char), dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
                )
                self._send_input(
                    [
                        Input(type=INPUT_KEYBOARD, ii=Input_I(ki=key_input_down)),
                        Input(type=INPUT_KEYBOARD, ii=Input_I(ki=key_input_up)),
                    ]
                )
                time.sleep(delay)

    def press_key(self, key, modifiers=None):
        """Presses a key with optional modifiers."""
        if modifiers is None:
            modifiers = []
        mod_inputs_down = [
            Input(
                type=INPUT_KEYBOARD,
                ii=Input_I(ki=KeyBdInput(wVk=KEY_MAP[mod], dwFlags=KEYEVENTF_KEYDOWN)),
            )
            for mod in modifiers
            if mod in KEY_MAP
        ]
        if mod_inputs_down:
            self._send_input(mod_inputs_down)

        if key in KEY_MAP:
            vk_code = KEY_MAP[key]
            self._send_input(
                [
                    Input(
                        type=INPUT_KEYBOARD,
                        ii=Input_I(
                            ki=KeyBdInput(wVk=vk_code, dwFlags=KEYEVENTF_KEYDOWN)
                        ),
                    )
                ]
            )
            time.sleep(random.uniform(0.05, 0.1))
            self._send_input(
                [
                    Input(
                        type=INPUT_KEYBOARD,
                        ii=Input_I(ki=KeyBdInput(wVk=vk_code, dwFlags=KEYEVENTF_KEYUP)),
                    )
                ]
            )

        mod_inputs_up = [
            Input(
                type=INPUT_KEYBOARD,
                ii=Input_I(ki=KeyBdInput(wVk=KEY_MAP[mod], dwFlags=KEYEVENTF_KEYUP)),
            )
            for mod in reversed(modifiers)
            if mod in KEY_MAP
        ]
        if mod_inputs_up:
            self._send_input(mod_inputs_up)
