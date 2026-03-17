using System;
using System.Windows;
using VASbot.Gui.Engine;
using VASbot.Gui.UI.ViewModels;
using System.Windows;
using VASbot.Gui.Engine;
using VASbot.Gui.UI.ViewModels;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Windows.Input;
using System.Windows.Interop;

namespace VASbot.Gui.Engine
{
    public class HotkeyService : IDisposable
    {
        [DllImport("user32.dll")]
        private static extern bool RegisterHotKey(IntPtr hWnd, int id, uint fsModifiers, uint vk);

        [DllImport("user32.dll")]
        private static extern bool UnregisterHotKey(IntPtr hWnd, int id);

        private const int WM_HOTKEY = 0x0312;

        private readonly nint _hwnd;
        private readonly HwndSource _source;
        private readonly Dictionary<int, Action> _callbacks = new();
        private int _currentId = 0;

        public HotkeyService(nint hwnd)
        {
            _hwnd = hwnd;
            _source = HwndSource.FromHwnd(hwnd);
            _source.AddHook(HwndHook);
        }

        public int Register(ModifierKeys modifiers, Key key, Action callback)
        {
            int id = ++_currentId;
            uint vkey = (uint)KeyInterop.VirtualKeyFromKey(key);
            uint mod = (uint)modifiers;

            if (RegisterHotKey(_hwnd, id, mod, vkey))
            {
                _callbacks[id] = callback;
                return id;
            }
            return -1;
        }

        public void Unregister(int id)
        {
            if (_callbacks.ContainsKey(id))
            {
                UnregisterHotKey(_hwnd, id);
                _callbacks.Remove(id);
            }
        }

        private IntPtr HwndHook(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
        {
            if (msg == WM_HOTKEY)
            {
                int id = wParam.ToInt32();
                if (_callbacks.TryGetValue(id, out var callback))
                {
                    callback.Invoke();
                    handled = true;
                }
            }
            return IntPtr.Zero;
        }

        public void Dispose()
        {
            foreach (var id in new List<int>(_callbacks.Keys))
            {
                Unregister(id);
            }
            _source.RemoveHook(HwndHook);
        }
    }
}
