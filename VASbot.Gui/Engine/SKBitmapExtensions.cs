using SkiaSharp;
using System;

namespace VASbot.Gui.Engine
{
    public static class SKBitmapExtensions
    {
        public static SKColor GetPixelFast(this SKBitmap bitmap, int x, int y)
        {
            if (bitmap == null) return SKColors.Empty;

            if (x < 0 || x >= bitmap.Width || y < 0 || y >= bitmap.Height)
            {
                return SKColors.Empty;
            }

            if (bitmap.BytesPerPixel == 4 && bitmap.ColorType == SKColorType.Bgra8888)
            {
                unsafe
                {
                    byte* ptr = (byte*)bitmap.GetPixels().ToPointer();
                    int rowBytes = bitmap.RowBytes;
                    byte* pixelPtr = ptr + y * rowBytes + x * 4;

                    byte b = pixelPtr[0];
                    byte g = pixelPtr[1];
                    byte r = pixelPtr[2];
                    byte a = pixelPtr[3];

                    return new SKColor(r, g, b, a);
                }
            }

            // Fallback to slow native method for other formats
            return bitmap.GetPixel(x, y);
        }
    }
}
