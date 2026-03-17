using SkiaSharp;
using System.Drawing;

namespace VASbot.Gui.Engine
{
    /// <summary>
    /// Centralized coordinate transformer (Phase 2 requirement).
    /// Maps between Screen (Hwnd relative), Image (0,0 of bitmap), and Canvas (WPF control).
    /// </summary>
    public class CoordinateTransformer
    {
        private SKPoint _offset;
        private double _zoom;

        public void UpdateTransform(SKPoint offset, double zoom)
        {
            _offset = offset;
            _zoom = zoom;
        }

        public SKPoint CanvasToImage(SKPoint p)
        {
            return new SKPoint(
                (float)((p.X - _offset.X) / _zoom),
                (float)((p.Y - _offset.Y) / _zoom)
            );
        }

        public SKPoint ImageToCanvas(SKPoint p)
        {
            return new SKPoint(
                (float)(p.X * _zoom + _offset.X),
                (float)(p.Y * _zoom + _offset.Y)
            );
        }

        public SKRect ScreenToImage(System.Windows.Rect screenRect, System.Windows.Rect windowRect)
        {
            return new SKRect(
                (float)(screenRect.Left - windowRect.Left),
                (float)(screenRect.Top - windowRect.Top),
                (float)(screenRect.Right - windowRect.Left),
                (float)(screenRect.Bottom - windowRect.Top)
            );
        }

        public Rectangle ImageToScreen(SKRect r, Rectangle windowRect)
        {
            return new Rectangle(
                (int)(windowRect.X + r.Left),
                (int)(windowRect.Y + r.Top),
                (int)r.Width,
                (int)r.Height
            );
        }
    }
}
