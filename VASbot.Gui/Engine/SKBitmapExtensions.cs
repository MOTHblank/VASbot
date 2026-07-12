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

            if (bitmap.BytesPerPixel == 4)
            {
                unsafe
                {
                    byte* ptr = (byte*)bitmap.GetPixels().ToPointer();
                    int rowBytes = bitmap.RowBytes;
                    byte* pixelPtr = ptr + y * rowBytes + x * 4;

                    if (bitmap.ColorType == SKColorType.Rgba8888 || bitmap.ColorType == SKColorType.Rgb888x)
                    {
                        return new SKColor(pixelPtr[0], pixelPtr[1], pixelPtr[2], pixelPtr[3]);
                    }
                    else // BGRA or assume BGRA
                    {
                        return new SKColor(pixelPtr[2], pixelPtr[1], pixelPtr[0], pixelPtr[3]);
                    }
                }
            }

            // Fallback to slow native method for non 4-byte formats
            return bitmap.GetPixel(x, y);
        }
    }
}
