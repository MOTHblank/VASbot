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
        public static extern bool GetClientRect(IntPtr hWnd, out RECT lpRect);

        [DllImport("user32.dll")]
        public static extern bool ClientToScreen(IntPtr hWnd, ref POINT lpPoint);

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

        [StructLayout(LayoutKind.Sequential)]
        public struct POINT
        {
            public int X;
            public int Y;
        }

        public bool GetTrueClientScreenRect(IntPtr hwnd, out RECT screenRect)
        {
            screenRect = new RECT();
            if (!GetClientRect(hwnd, out RECT clientRect)) return false;

            POINT ptLT = new POINT { X = clientRect.Left, Y = clientRect.Top };
            POINT ptRB = new POINT { X = clientRect.Right, Y = clientRect.Bottom };

            if (!ClientToScreen(hwnd, ref ptLT)) return false;
            if (!ClientToScreen(hwnd, ref ptRB)) return false;

            screenRect.Left = ptLT.X;
            screenRect.Top = ptLT.Y;
            screenRect.Right = ptRB.X;
            screenRect.Bottom = ptRB.Y;
            return true;
        }

        public SKBitmap? CaptureWindow(IntPtr hwnd)
        {
            if (hwnd == IntPtr.Zero || IsIconic(hwnd)) return null;
            if (!GetTrueClientScreenRect(hwnd, out RECT rect)) return null;

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
            if (!GetTrueClientScreenRect(hwnd, out RECT rect)) return null;

            int width = rect.Right - rect.Left;
            int height = rect.Bottom - rect.Top;
            if (width <= 0 || height <= 0) return null;

            using (Bitmap bmp = new Bitmap(width, height, PixelFormat.Format32bppArgb))
            {
                using (Graphics g = Graphics.FromImage(bmp))
                {
                    IntPtr hdc = g.GetHdc();
                    // PW_CLIENTONLY = 1
                    PrintWindow(hwnd, hdc, 1);
                    g.ReleaseHdc(hdc);
                }

                // Direct memory copy instead of slow MemoryStream encoding/decoding
                var bmpData = bmp.LockBits(new Rectangle(0, 0, width, height), ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
                try
                {
                    var info = new SKImageInfo(width, height, SKColorType.Bgra8888, SKAlphaType.Premul);
                    var skBitmap = new SKBitmap(info);

                    long bytesToCopy = (long)bmpData.Stride * height;
                    unsafe
                    {
                        Buffer.MemoryCopy((void*)bmpData.Scan0, (void*)skBitmap.GetPixels(), bytesToCopy, bytesToCopy);
                    }
                    return skBitmap;
                }
                finally
                {
                    bmp.UnlockBits(bmpData);
                }
            }
        }

        public void Dispose()
        {
            _dxgiService.Dispose();
        }
    }
}
