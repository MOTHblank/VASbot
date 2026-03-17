using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
using SkiaSharp;

namespace VASbot.Gui.Engine
{
    public class ScreenshotService : IDisposable
    {
        private readonly DXGICaptureService _dxgiService = new();

        [DllImport("user32.dll")]
        public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

        [DllImport("user32.dll")]
        public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, int nFlags);

        [DllImport("user32.dll")]
        [return: MarshalAs(UnmanagedType.Bool)]
        public static extern bool IsIconic(IntPtr hWnd);

        [DllImport("user32.dll")]
        public static extern int GetWindowLong(IntPtr hWnd, int nIndex);

        public const int GWL_STYLE = -16;
        public const int GWL_EXSTYLE = -20;

        public int LastWidth { get; private set; } = 1920;
        public int LastHeight { get; private set; } = 1080;

        [StructLayout(LayoutKind.Sequential)]
        public struct RECT
        {
            public int Left;
            public int Top;
            public int Right;
            public int Bottom;
        }

        public SKBitmap? CaptureWindow(IntPtr hwnd)
        {
            if (hwnd == IntPtr.Zero || IsIconic(hwnd)) return null;
            if (!GetWindowRect(hwnd, out RECT rect)) return null;

            int width = rect.Right - rect.Left;
            int height = rect.Bottom - rect.Top;
            if (width <= 0 || height <= 0) return null;

            LastWidth = width;
            LastHeight = height;

            try
            {
                var dxgiFrame = _dxgiService.Capture(new Rectangle(rect.Left, rect.Top, width, height));
                if (dxgiFrame != null) return dxgiFrame;
            }
            catch { }

            // Fallback to BitBlt if DXGI fails
            return CaptureWindowBitBlt(hwnd);
        }

        public SKBitmap? CaptureWindowBitBlt(IntPtr hwnd)
        {
            if (hwnd == IntPtr.Zero) return null;
            if (!GetWindowRect(hwnd, out RECT rect)) return null;

            int width = rect.Right - rect.Left;
            int height = rect.Bottom - rect.Top;
            if (width <= 0 || height <= 0) return null;

            using (Bitmap bmp = new Bitmap(width, height, PixelFormat.Format32bppArgb))
            {
                using (Graphics g = Graphics.FromImage(bmp))
                {
                    IntPtr hdc = g.GetHdc();
                    // PW_RENDERFULLCONTENT = 2
                    PrintWindow(hwnd, hdc, 2);
                    g.ReleaseHdc(hdc);
                }

                using (var stream = new System.IO.MemoryStream())
                {
                    bmp.Save(stream, ImageFormat.Bmp);
                    stream.Seek(0, System.IO.SeekOrigin.Begin);
                    return SKBitmap.Decode(stream);
                }
            }
        }

        public void Dispose()
        {
            _dxgiService.Dispose();
        }
    }
}
