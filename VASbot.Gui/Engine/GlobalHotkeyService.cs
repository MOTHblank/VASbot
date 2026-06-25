using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Input;
using System.Windows.Interop;

namespace VASbot.Gui.Engine
{
    /// <summary>
    /// Global hotkey service using low-level keyboard hook.
    /// Works even when this application doesn't have focus.
    /// </summary>
    public class GlobalHotkeyService : IDisposable
    {
        private const int WH_KEYBOARD_LL = 13;
        private const int WM_KEYDOWN = 0x0100;
        private const int WM_SYSKEYDOWN = 0x0104;

        private delegate IntPtr LowLevelKeyboardProc(int nCode, IntPtr wParam, IntPtr lParam);

        [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        private static extern IntPtr SetWindowsHookEx(int idHook, LowLevelKeyboardProc lpfn, IntPtr hMod, uint dwThreadId);

        [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool UnhookWindowsHookEx(IntPtr hhk);

        [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        private static extern IntPtr CallNextHookEx(IntPtr hhk, int nCode, IntPtr wParam, IntPtr lParam);

        [DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        private static extern IntPtr GetModuleHandle(string lpModuleName);

        [DllImport("user32.dll")]
        private static extern int ToAscii(uint uVirtKey, uint uScanCode, byte[] lpKeyState, out uint lpChar, uint uFlags);

        [StructLayout(LayoutKind.Sequential)]
        private struct KBDLLHOOKSTRUCT
        {
            public uint vkCode;
            public uint scanCode;
            public uint flags;
            public uint time;
            public IntPtr dwExtraInfo;
        }

        private IntPtr _hookId = IntPtr.Zero;
        private LowLevelKeyboardProc _proc;
        
        private readonly Action _runCallback;
        private readonly Action _stopCallback;
        private readonly Action _killCallback;

        // Track pressed keys for combinations
        private bool _ctrlPressed = false;
        private bool _altPressed = false;
        private bool _shiftPressed = false;

        public GlobalHotkeyService(Action runCallback, Action stopCallback, Action killCallback)
        {
            _runCallback = runCallback;
            _stopCallback = stopCallback;
            _killCallback = killCallback;
            _proc = HookCallback;
        }

        public void Start()
        {
            _hookId = SetHook(_proc);
            if (_hookId == IntPtr.Zero)
            {
                int error = Marshal.GetLastWin32Error();
                Debug.WriteLine($"Failed to install global keyboard hook. Error: {error}");
            }
            else
            {
                Debug.WriteLine("Global keyboard hook installed successfully.");
            }
        }

        private IntPtr SetHook(LowLevelKeyboardProc proc)
        {
            using (Process curProcess = Process.GetCurrentProcess())
            using (ProcessModule? curModule = curProcess.MainModule)
            {
                return SetWindowsHookEx(WH_KEYBOARD_LL, proc, GetModuleHandle(curModule?.ModuleName ?? string.Empty), 0);
            }
        }

        private IntPtr HookCallback(int nCode, IntPtr wParam, IntPtr lParam)
        {
            if (nCode >= 0 && (wParam == (IntPtr)WM_KEYDOWN || wParam == (IntPtr)WM_SYSKEYDOWN))
            {
                var hookStructObj = Marshal.PtrToStructure(lParam, typeof(KBDLLHOOKSTRUCT));
                if (hookStructObj == null) return CallNextHookEx(_hookId, nCode, wParam, lParam);
                KBDLLHOOKSTRUCT hookStruct = (KBDLLHOOKSTRUCT)hookStructObj!;
                Key key = KeyInterop.KeyFromVirtualKey((int)hookStruct.vkCode);

                // Track modifier states
                if (hookStruct.vkCode == 0x11) _ctrlPressed = true;  // VK_CONTROL
                if (hookStruct.vkCode == 0x10) _shiftPressed = true; // VK_SHIFT
                if (hookStruct.vkCode == 0x12) _altPressed = true;   // VK_MENU (Alt)

                // F5 - RUN script
                if (key == Key.F5)
                {
                    Debug.WriteLine("F5 RUN TRIGGERED!");
                    _runCallback?.Invoke();
                    return (IntPtr)1; // Consume the key
                }

                // F12 - KILLSWITCH (highest priority) - works alone or with any modifiers
                if (key == Key.F12)
                {
                    Debug.WriteLine("F12 KILLSWITCH TRIGGERED!");
                    _killCallback?.Invoke();
                    return (IntPtr)1; // Consume the key
                }

                // F6 - STOP - works alone or with modifiers
                if (key == Key.F6)
                {
                    Debug.WriteLine("F6 STOP TRIGGERED!");
                    _stopCallback?.Invoke();
                    return (IntPtr)1; // Consume the key
                }

                // Also support F6 with Ctrl for reliability
                if (key == Key.F6 && (_ctrlPressed || _altPressed || _shiftPressed))
                {
                    Debug.WriteLine("F6+Modifier STOP TRIGGERED!");
                    _stopCallback?.Invoke();
                    return (IntPtr)1;
                }

                // F12 with any modifier also kills
                if (key == Key.F12 && (_ctrlPressed || _altPressed || _shiftPressed))
                {
                    Debug.WriteLine("F12+Modifier KILLSWITCH TRIGGERED!");
                    _killCallback?.Invoke();
                    return (IntPtr)1;
                }
            }
            else if (nCode >= 0)
            {
                // Key up - reset modifiers
                var hookStructObj = Marshal.PtrToStructure(lParam, typeof(KBDLLHOOKSTRUCT));
                if (hookStructObj == null) return CallNextHookEx(_hookId, nCode, wParam, lParam);
                KBDLLHOOKSTRUCT hookStruct = (KBDLLHOOKSTRUCT)hookStructObj!;
                if (hookStruct.vkCode == 0x11) _ctrlPressed = false;
                if (hookStruct.vkCode == 0x10) _shiftPressed = false;
                if (hookStruct.vkCode == 0x12) _altPressed = false;
            }

            return CallNextHookEx(_hookId, nCode, wParam, lParam);
        }

        public void Dispose()
        {
            if (_hookId != IntPtr.Zero)
            {
                UnhookWindowsHookEx(_hookId);
                _hookId = IntPtr.Zero;
            }
        }
    }
}
