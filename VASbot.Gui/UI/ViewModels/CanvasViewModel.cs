using System;
using System.Collections.ObjectModel;
using System.Windows;
using CommunityToolkit.Mvvm.ComponentModel;
using SkiaSharp;
using VASbot.Gui.Engine;

namespace VASbot.Gui.UI.ViewModels
{
    public partial class CanvasViewModel : ObservableObject
    {
        [ObservableProperty]
        private SKBitmap? _capturedBitmap;

        [ObservableProperty]
        private double _zoomLevel = 1.0;

        [ObservableProperty]
        private SKPoint _offset = new(0, 0);

        [ObservableProperty]
        private bool _isPanning;

        [ObservableProperty]
        private bool _isCreatingRegion;

        [ObservableProperty]
        private RegionModel? _currentCreationRegion;

        private Point _lastMousePos;
        private SKPoint _startCreationPos;

        public ObservableCollection<RegionModel> Regions { get; } = new();

        public void Render(SKCanvas canvas, float width, float height)
        {
            canvas.Clear(SKColors.Black);
            if (CapturedBitmap == null) return;

            canvas.Save();
            canvas.Translate(Offset.X, Offset.Y);
            canvas.Scale((float)ZoomLevel);

            // 1. Draw Captured Window
            canvas.DrawBitmap(CapturedBitmap, 0, 0);

            // 2. Draw Regions
            using var paint = new SKPaint
            {
                Style = SKPaintStyle.Stroke,
                StrokeWidth = 2 / (float)ZoomLevel, 
                IsAntialias = true
            };

            foreach (var region in Regions)
            {
                DrawRegion(canvas, region, paint);
            }

            // 3. Draw temporary region being created
            if (IsCreatingRegion && CurrentCreationRegion != null)
            {
                paint.Color = SKColors.Yellow;
                DrawRegion(canvas, CurrentCreationRegion, paint);
            }

            canvas.Restore();
        }

        private void DrawRegion(SKCanvas canvas, RegionModel region, SKPaint paint)
        {
            if (SKColor.TryParse(region.Color, out var color))
                paint.Color = color;
            
            var rect = new SKRect(region.X, region.Y, region.X + region.Width, region.Y + region.Height);
            
            paint.Style = SKPaintStyle.Fill;
            var fillColor = paint.Color.WithAlpha(30);
            using (var fillPaint = new SKPaint { Color = fillColor, Style = SKPaintStyle.Fill })
            {
                canvas.DrawRect(rect, fillPaint);
            }

            paint.Style = SKPaintStyle.Stroke;
            canvas.DrawRect(rect, paint);
        }

        public void StartCreation(Point pos)
        {
            IsCreatingRegion = true;
            _startCreationPos = ScreenToImage(pos);
            CurrentCreationRegion = new RegionModel 
            { 
                X = (int)_startCreationPos.X, 
                Y = (int)_startCreationPos.Y,
                Width = 0,
                Height = 0,
                Color = "#FFFF00"
            };
        }

        public void UpdateCreation(Point pos)
        {
            if (!IsCreatingRegion || CurrentCreationRegion == null) return;

            var currentPos = ScreenToImage(pos);
            
            int x = (int)Math.Min(_startCreationPos.X, currentPos.X);
            int y = (int)Math.Min(_startCreationPos.Y, currentPos.Y);
            int w = (int)Math.Abs(_startCreationPos.X - currentPos.X);
            int h = (int)Math.Abs(_startCreationPos.Y - currentPos.Y);

            CurrentCreationRegion.X = x;
            CurrentCreationRegion.Y = y;
            CurrentCreationRegion.Width = w;
            CurrentCreationRegion.Height = h;
            
            OnPropertyChanged(nameof(CurrentCreationRegion));
        }

        public void EndCreation()
        {
            if (IsCreatingRegion && CurrentCreationRegion != null && CurrentCreationRegion.Width > 2 && CurrentCreationRegion.Height > 2)
            {
                CurrentCreationRegion.Color = "#FF0000";
                CurrentCreationRegion.Name = $"Region {Regions.Count}";
                Regions.Add(CurrentCreationRegion);
            }
            IsCreatingRegion = false;
            CurrentCreationRegion = null;
        }

        public void StartPan(Point pos)
        {
            IsPanning = true;
            _lastMousePos = pos;
        }

        public void UpdatePan(Point pos)
        {
            if (!IsPanning) return;

            var deltaX = (float)(pos.X - _lastMousePos.X);
            var deltaY = (float)(pos.Y - _lastMousePos.Y);

            Offset = new SKPoint(Offset.X + deltaX, Offset.Y + deltaY);
            _lastMousePos = pos;
        }

        public void EndPan()
        {
            IsPanning = false;
        }

        public void Zoom(double delta, Point mousePos)
        {
            double oldZoom = ZoomLevel;
            double zoomFactor = delta > 0 ? 1.1 : 0.9;
            ZoomLevel *= zoomFactor;

            if (ZoomLevel < 0.1) ZoomLevel = 0.1;
            if (ZoomLevel > 20.0) ZoomLevel = 20.0;

            float newX = (float)(mousePos.X - (mousePos.X - Offset.X) * (ZoomLevel / oldZoom));
            float newY = (float)(mousePos.Y - (mousePos.Y - Offset.Y) * (ZoomLevel / oldZoom));
            Offset = new SKPoint(newX, newY);
        }

        public SKPoint ScreenToImage(Point p)
        {
            return new SKPoint(
                (float)((p.X - Offset.X) / ZoomLevel),
                (float)((p.Y - Offset.Y) / ZoomLevel)
            );
        }
    }
}
