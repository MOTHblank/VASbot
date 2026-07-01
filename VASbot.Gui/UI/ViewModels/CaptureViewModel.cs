using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SkiaSharp;
using System;
using System.Collections.ObjectModel;
using System.Drawing;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using VASbot.Gui.Engine;

using Point = System.Windows.Point;

namespace VASbot.Gui.UI.ViewModels
{
    public partial class CaptureViewModel : ObservableObject
    {
        private readonly IBotService _botService;
        private readonly SharedMemoryService _sharedMemory;
        private readonly ScreenshotService _screenshotService;
        private readonly ReflectionService _reflectionService;
        private readonly CoordinateTransformer _transformer;
        private readonly RegionManager _regionManager;
        private readonly ColorClusterManager _colorClusterManager = new();
        private readonly System.Threading.CancellationTokenSource _bgDetectionCts = new();

        public ObservableCollection<ColorClusterModel> ColorClusters { get; } = new();

        [ObservableProperty]
        private ColorClusterModel? _selectedColorCluster;

        private async Task SyncColorClustersToSidecar()
        {
            await _botService.UpdateColorClustersAsync(ColorClusters);
        }

        public async Task SaveColorClustersAsync()
        {
            await _colorClusterManager.SaveClustersAsync(ColorClusters);
            await SyncColorClustersToSidecar();
        }

        private void HookCluster(ColorClusterModel cluster)
        {
            cluster.PropertyChanged += Cluster_PropertyChanged;
            cluster.Colors.CollectionChanged += Colors_CollectionChanged;
        }

        private void UnhookCluster(ColorClusterModel cluster)
        {
            cluster.PropertyChanged -= Cluster_PropertyChanged;
            cluster.Colors.CollectionChanged -= Colors_CollectionChanged;
        }

        private void Cluster_PropertyChanged(object? sender, System.ComponentModel.PropertyChangedEventArgs e)
        {
            _ = SaveColorClustersAsync();
        }

        private void Colors_CollectionChanged(object? sender, System.Collections.Specialized.NotifyCollectionChangedEventArgs e)
        {
            _ = SaveColorClustersAsync();
        }

        [RelayCommand]
        public async Task AddColorCluster()
        {
            var cluster = new ColorClusterModel
            {
                Name = $"Cluster {ColorClusters.Count + 1}"
            };
            HookCluster(cluster);
            ColorClusters.Add(cluster);
            SelectedColorCluster = cluster;
            await SaveColorClustersAsync();
        }

        [RelayCommand]
        public async Task DeleteColorCluster(ColorClusterModel cluster)
        {
            if (cluster == null) return;
            UnhookCluster(cluster);
            ColorClusters.Remove(cluster);
            if (SelectedColorCluster == cluster)
            {
                SelectedColorCluster = ColorClusters.FirstOrDefault();
            }
            await SaveColorClustersAsync();
        }

        [RelayCommand]
        public async Task RemoveColorFromCluster(string colorHex)
        {
            if (SelectedColorCluster == null || string.IsNullOrEmpty(colorHex)) return;
            SelectedColorCluster.Colors.Remove(colorHex);
            await SaveColorClustersAsync();
        }

        [ObservableProperty]
        private SKPoint _mousePos;

        [ObservableProperty]
        private SKBitmap? _currentFrame;

        [ObservableProperty]
        private WindowInfo? _selectedWindow;

        [ObservableProperty]
        private double _zoomLevel = 1.0;

        [ObservableProperty]
        private SKPoint _offset = new(0, 0);

        [ObservableProperty]
        private string _status = "No Window Selected";

        [ObservableProperty]
        private bool _isCapturing;

        [ObservableProperty]
        private bool _isReflecting;

        [ObservableProperty]
        private bool _isRegionsVisible = true;

        [ObservableProperty]
        private bool _isShapesVisible = true;

        [ObservableProperty]
        private bool _isClustersVisible = true;

        [ObservableProperty]
        private bool _isUiaVisible = true;

        [ObservableProperty]
        private string _viewportMode = "default";

        [ObservableProperty]
        private string _telemetryCoords = "X: 0, Y: 0";

        [ObservableProperty]
        private string _telemetryColorHex = "#000000";

        [ObservableProperty]
        private string _telemetryElementInfo = "Hover Element: None";

        [ObservableProperty]
        private bool _isOverlayMirrorActive;

        [ObservableProperty]
        private bool _isOverlayClickThrough = true;

        partial void OnIsOverlayMirrorActiveChanged(bool value)
        {
            if (value && SelectedWindow != null)
            {
                if (!IsReflecting)
                {
                    IsReflecting = true;
                }
            }
        }



        partial void OnIsReflectingChanged(bool value)
        {
            if (value && SelectedWindow != null)
            {
                _reflectionService.Start(SelectedWindow.Handle, Fps);
                Status = "🎬 Live Mirror Active";
            }
            else
            {
                _reflectionService.Stop();
                Status = "⏹ Mirror Stopped";
            }
        }

        [ObservableProperty]
        private bool _isDynamic = true;

        partial void OnIsDynamicChanged(bool value)
        {
            _reflectionService.IsDynamic = value;
            if (!value) _reflectionService.TriggerStaticCapture();
        }

        [RelayCommand]
        public void StaticCapture()
        {
            _reflectionService.TriggerStaticCapture();
        }

        [ObservableProperty]
        private bool _isMinimized;

        [ObservableProperty]
        private int _fps = 20;

        [ObservableProperty]
        private double _actualFps;

        [ObservableProperty]
        private double _renderTimeMs;

        [ObservableProperty]
        private long _memoryUsageMb;

        [ObservableProperty]
        private bool _isCreatingRegion;

        [ObservableProperty]
        private bool _isEyedropperActive;

        partial void OnIsEyedropperActiveChanged(bool value)
        {
            if (value)
            {
                IsCreatingRegion = false;
                Status = "💧 Eyedropper Active - Click to sample color";
            }
            else
            {
                Status = "Ready";
            }
        }

        [ObservableProperty]
        private string _pickedColor = "#FFFFFF";

        [ObservableProperty]
        private RegionModel? _currentCreationRegion;

        [ObservableProperty]
        private RegionModel? _selectedRegion;

        [ObservableProperty]
        private DetectedShapeResult? _selectedDetectedShape;

        public bool IsSaveShapeVisible => SelectedDetectedShape != null;

        partial void OnSelectedDetectedShapeChanged(DetectedShapeResult? value)
        {
            OnPropertyChanged(nameof(IsSaveShapeVisible));
        }

        private bool _hasMouseMovedSignificantly;

        [ObservableProperty]
        private bool _isDraggingRegion;

        public enum ResizeEdge { None, TopLeft, TopRight, BottomLeft, BottomRight }
        
        [ObservableProperty]
        private ResizeEdge _activeResizeEdge = ResizeEdge.None;

        private SKPoint _dragStartPos;
        private SKPoint _startCreationPos;
        private Rectangle _dragStartRect;

        [ObservableProperty]
        private SKRect? _highlightedRect;

        // Commands for region management - initialized in constructor

        [RelayCommand]
        public void ResetZoom()
        {
            ZoomLevel = 1.0;
            Offset = new SKPoint(0, 0);
            _transformer.UpdateTransform(Offset, ZoomLevel);
        }

        [RelayCommand]
        public void ZoomIn()
        {
            ZoomLevel = Math.Min(20.0, ZoomLevel * 1.2);
            _transformer.UpdateTransform(Offset, ZoomLevel);
        }

        [RelayCommand]
        public void ZoomOut()
        {
            ZoomLevel = Math.Max(0.1, ZoomLevel / 1.2);
            _transformer.UpdateTransform(Offset, ZoomLevel);
        }

        [ObservableProperty]
        private string _detectShapeType = "all";

        [ObservableProperty]
        private int _detectMinSize = 15;

        [ObservableProperty]
        private int _detectMaxSize = 1000;

        public ObservableCollection<DetectedShapeResult> DetectedShapes { get; } = new();

        public ObservableCollection<RegionModel> Regions { get; } = new();

        public ObservableCollection<WindowInfo> WindowList { get; } = new();

        public CaptureViewModel(
            IBotService botService, 
            SharedMemoryService sharedMemory,
            ScreenshotService screenshotService,
            ReflectionService reflectionService,
            CoordinateTransformer transformer,
            RegionManager regionManager)
        {
            _botService = botService;
            _sharedMemory = sharedMemory;
            _screenshotService = screenshotService;
            _reflectionService = reflectionService;
            _transformer = transformer;
            _regionManager = regionManager;

            // Initialize commands
            // (Commands are auto-generated)

            // Link services
            _reflectionService.SharedMemory = _sharedMemory;
            _reflectionService.BotService = _botService;

            _reflectionService.FrameUpdated += (frame) =>
            {
                App.Current.Dispatcher.Invoke(() => 
                {
                    if (frame == null)
                    {
                        IsMinimized = true;
                        Status = "⚠️ Window Minimized - View Frozen";
                    }
                    else
                    {
                        IsMinimized = false;
                        CurrentFrame = frame;
                        if (IsReflecting) Status = $"Live Mirror Active ({Fps} FPS)";
                    }
                });
            };

            InitializeAsync();
        }

        private async void InitializeAsync()
        {
            await RefreshWindowsAsync();
            var loaded = await _regionManager.LoadRegionsAsync();
            foreach(var r in loaded) Regions.Add(r);
            await SyncRegionsToSidecar();

            var loadedClusters = await _colorClusterManager.LoadClustersAsync();
            foreach(var c in loadedClusters)
            {
                HookCluster(c);
                ColorClusters.Add(c);
            }
            SelectedColorCluster = ColorClusters.FirstOrDefault();
            await SyncColorClustersToSidecar();
            _ = Task.Run(() => StartBackgroundShapeDetectionLoop(_bgDetectionCts.Token));
        }

        partial void OnSelectedWindowChanged(WindowInfo? value)
        {
            if (value != null)
            {
                _ = _botService.SetTargetWindowAsync(value.Handle, value.Title);
                
                if (IsReflecting)
                {
                    _reflectionService.Start(value.Handle, Fps);
                }
                else
                {
                    _reflectionService.TriggerStaticCapture();
                }
            }
        }

        [RelayCommand]
        public async Task DeleteRegion(RegionModel region)
        {
            if (region == null) return;
            Regions.Remove(region);
            await SyncRegionsToSidecar();
        }

        [RelayCommand]
        public async Task PickRegionColor(RegionModel region)
        {
            if (region == null) return;
            var dialog = new System.Windows.Forms.ColorDialog();
            if (dialog.ShowDialog() == System.Windows.Forms.DialogResult.OK)
            {
                var color = dialog.Color;
                region.Color = $"#{color.R:X2}{color.G:X2}{color.B:X2}";
                await _regionManager.SaveRegionsAsync(Regions);
                await SyncRegionsToSidecar();
            }
        }

        [RelayCommand]
        public async Task SaveRegionAsPngAsync(RegionModel region)
        {
            if (region == null || CurrentFrame == null) return;

            var dialog = new Microsoft.Win32.SaveFileDialog
            {
                Filter = "PNG Image (*.png)|*.png",
                DefaultExt = ".png",
                FileName = $"{region.Name.Replace(" ", "_")}.png",
                Title = "Save Region as PNG Template"
            };

            if (dialog.ShowDialog() == true)
            {
                try
                {
                    var rect = new SKRectI(region.X, region.Y, region.X + region.Width, region.Y + region.Height);
                    if (rect.Left >= 0 && rect.Top >= 0 && rect.Right <= CurrentFrame.Width && rect.Bottom <= CurrentFrame.Height && rect.Width > 0 && rect.Height > 0)
                    {
                        using var subset = new SKBitmap(rect.Width, rect.Height);
                        using (var canvas = new SKCanvas(subset))
                        {
                            canvas.DrawBitmap(CurrentFrame, -rect.Left, -rect.Top);
                        }

                        using var image = SKImage.FromBitmap(subset);
                        using var data = image.Encode(SKEncodedImageFormat.Png, 100);
                        using (var stream = System.IO.File.OpenWrite(dialog.FileName))
                        {
                            data.SaveTo(stream);
                        }

                        Status = $"Saved PNG template: {System.IO.Path.GetFileName(dialog.FileName)}";
                    }
                    else
                    {
                        Status = "Error: Region is out of current frame bounds.";
                    }
                }
                catch (Exception ex)
                {
                    Status = $"Failed to save PNG: {ex.Message}";
                }
            }
        }

        private async Task SyncRegionsToSidecar()
        {
            await _botService.UpdateRegionsAsync(Regions);
        }

        [RelayCommand]
        public async Task RefreshWindowsAsync()
        {
            WindowList.Clear();
            var windows = await _botService.ListWindowsAsync();
            foreach (var w in windows) WindowList.Add(w);
        }

        [RelayCommand]
        public async Task CaptureFrameAsync()
        {
            if (SelectedWindow == null) return;
            
            var frame = await Task.Run(() => _screenshotService.CaptureWindow(SelectedWindow.Handle));
            
            if (frame != null)
            {
                CurrentFrame = frame;
                Status = $"Capturing: {SelectedWindow.Title} ({frame.Width}x{frame.Height})";
            }
            else
            {
                Status = "Capture Failed";
            }
        }

        [RelayCommand]
        public void ToggleReflection()
        {
            if (SelectedWindow == null) return;

            if (IsReflecting)
            {
                _reflectionService.Stop();
                IsReflecting = false;
                Status = "Live Mirror Stopped";
            }
            else
            {
                _reflectionService.Start(SelectedWindow.Handle, Fps);
                IsReflecting = true;
                Status = $"Live Mirror Active ({Fps} FPS)";
            }
        }

        [RelayCommand]
        public async Task DetectShapes()
        {
            try
            {
                Status = "Detecting shapes...";
                var shapes = await _botService.DetectShapesAsync(DetectShapeType, DetectMinSize, DetectMaxSize);
                DetectedShapes.Clear();
                foreach (var s in shapes)
                {
                    DetectedShapes.Add(s);
                }
                Status = $"Detected {DetectedShapes.Count} shapes.";
                OnPropertyChanged(nameof(DetectedShapes));
            }
            catch (Exception ex)
            {
                Status = $"Detection failed: {ex.Message}";
            }
        }

        [RelayCommand]
        public void ClearDetectedShapes()
        {
            DetectedShapes.Clear();
            SelectedDetectedShape = null;
            Status = "Cleared detected shapes.";
            OnPropertyChanged(nameof(DetectedShapes));
        }

        [RelayCommand]
        public async Task SaveSelectedShapeAsRegion()
        {
            if (SelectedDetectedShape != null)
            {
                var newRegion = new RegionModel
                {
                    X = SelectedDetectedShape.X,
                    Y = SelectedDetectedShape.Y,
                    Width = SelectedDetectedShape.Width,
                    Height = SelectedDetectedShape.Height,
                    Color = PickedColor,
                    Name = $"Region {Regions.Count}"
                };

                if (SelectedWindow != null)
                {
                    newRegion.WindowTitle = SelectedWindow.Title;
                    newRegion.WindowClass = SelectedWindow.ClassName;
                }

                Regions.Add(newRegion);
                SelectedRegion = newRegion;
                SelectedDetectedShape = null; // Clear selection after saving
                
                await _regionManager.SaveRegionsAsync(Regions);
                await SyncRegionsToSidecar();
                Status = $"Saved shape as {newRegion.Name}.";
            }
        }

        private async Task StartBackgroundShapeDetectionLoop(System.Threading.CancellationToken token)
        {
            while (!token.IsCancellationRequested)
            {
                try
                {
                    await Task.Delay(1000, token);

                    if (IsShapesVisible && !_botService.IsRunning && IsReflecting && SelectedWindow != null && !IsMinimized)
                    {
                        var shapes = await _botService.DetectShapesAsync(DetectShapeType, DetectMinSize, DetectMaxSize);
                        
                        App.Current.Dispatcher.Invoke(() =>
                        {
                            // Avoid updating if both are empty to prevent property-change triggers
                            if (shapes.Count == 0 && DetectedShapes.Count == 0) return;

                            DetectedShapes.Clear();
                            foreach (var s in shapes)
                            {
                                DetectedShapes.Add(s);
                            }
                            OnPropertyChanged(nameof(DetectedShapes));
                        });
                    }
                }
                catch (OperationCanceledException)
                {
                    break;
                }
                catch (Exception)
                {
                    // Ignore background errors to prevent crashing on transient RPC disconnects
                }
            }
        }

        private DateTime _lastRenderTime = DateTime.Now;

        public void Render(SKCanvas canvas, float width, float height, bool isOverlay = false)
        {
            var startTime = DateTime.Now;
            ActualFps = 1.0 / (startTime - _lastRenderTime).TotalSeconds;
            _lastRenderTime = startTime;

            canvas.Clear(isOverlay ? SKColors.Transparent : SKColors.Black);
            if (!isOverlay && CurrentFrame == null) return;

            var renderOffset = isOverlay ? new SKPoint(0, 0) : Offset;
            var renderZoom = isOverlay ? 1.0 : ZoomLevel;

            _transformer.UpdateTransform(renderOffset, renderZoom);

            canvas.Save();
            canvas.Translate(renderOffset.X, renderOffset.Y);
            canvas.Scale((float)renderZoom);

            // 1. Draw Captured Window
            if (!isOverlay && CurrentFrame != null)
            {
                canvas.DrawBitmap(CurrentFrame, 0, 0);
            }

            // 2. Draw Regions
            using var paint = new SKPaint
            {
                Style = SKPaintStyle.Stroke,
                StrokeWidth = 2 / (float)renderZoom, 
                IsAntialias = true
            };

            if (IsRegionsVisible)
            {
                foreach (var region in Regions)
                {
                    DrawRegion(canvas, region, paint);
                    
                    if (region == SelectedRegion)
                    {
                        paint.Style = SKPaintStyle.Fill;
                        paint.Color = SKColors.White;
                        float hSize = 6 / (float)renderZoom;
                        canvas.DrawRect(region.X - hSize, region.Y - hSize, hSize * 2, hSize * 2, paint);
                        canvas.DrawRect(region.X + region.Width - hSize, region.Y + region.Height - hSize, hSize * 2, hSize * 2, paint);
                        paint.Style = SKPaintStyle.Stroke;
                    }
                }
            }

            // 2.5 Draw Active Color Cluster Highlights
            if (IsClustersVisible && SelectedColorCluster != null && SelectedColorCluster.Colors.Count > 0 && SelectedColorCluster.IsActive)
            {
                var cluster = SelectedColorCluster;
                var targetColors = new System.Collections.Generic.List<SKColor>();
                foreach (var hex in cluster.Colors)
                {
                    if (SKColor.TryParse(hex, out var col))
                    {
                        targetColors.Add(col);
                    }
                }

                if (targetColors.Count > 0)
                {
                    int tolerance = cluster.Tolerance;
                    var points = new System.Collections.Generic.List<SKPoint>();
                    int step = 2; // Downsampling by 2 matches original resolution perfectly with high rendering speed

                    for (int y = 0; y < CurrentFrame.Height; y += step)
                    {
                        for (int x = 0; x < CurrentFrame.Width; x += step)
                        {
                            var pixel = CurrentFrame.GetPixel(x, y);
                            foreach (var tc in targetColors)
                            {
                                if (Math.Abs(pixel.Red - tc.Red) <= tolerance &&
                                    Math.Abs(pixel.Green - tc.Green) <= tolerance &&
                                    Math.Abs(pixel.Blue - tc.Blue) <= tolerance)
                                {
                                    points.Add(new SKPoint(x, y));
                                    break;
                                }
                            }
                        }
                    }

                    if (points.Count > 0)
                    {
                        using var pointPaint = new SKPaint
                        {
                            Color = SKColor.Parse("#00FFFF").WithAlpha(160), // Glowing Neon Cyan
                            StrokeWidth = step * 1.2f,
                            Style = SKPaintStyle.Stroke,
                            StrokeCap = SKStrokeCap.Square
                        };
                        canvas.DrawPoints(SKPointMode.Points, points.ToArray(), pointPaint);
                    }
                }
            }

            // 3. Draw temporary region being created
            if (IsCreatingRegion && CurrentCreationRegion != null)
            {
                paint.Color = SKColors.Yellow;
                DrawRegion(canvas, CurrentCreationRegion, paint);
            }

            // 4. Draw UI Automation Highlight
            if (IsUiaVisible && HighlightedRect.HasValue)
            {
                paint.Color = SKColors.Cyan;
                paint.StrokeWidth = 3 / (float)renderZoom;
                canvas.DrawRect(HighlightedRect.Value, paint);
                
                paint.Style = SKPaintStyle.Fill;
                paint.Color = paint.Color.WithAlpha(40);
                canvas.DrawRect(HighlightedRect.Value, paint);
            }

            // 4.5. Detected Shapes Overlays
            if (IsShapesVisible)
            {
                foreach (var shape in DetectedShapes)
                {
                    float left = (float)shape.X;
                    float top = (float)shape.Y;
                    float right = (float)(shape.X + shape.Width);
                    float bottom = (float)(shape.Y + shape.Height);
                    var bbox = new SKRect(left, top, right, bottom);

                    bool isSelected = SelectedDetectedShape != null && 
                                     SelectedDetectedShape.X == shape.X && 
                                     SelectedDetectedShape.Y == shape.Y && 
                                     SelectedDetectedShape.Width == shape.Width && 
                                     SelectedDetectedShape.Height == shape.Height;

                    var color = isSelected ? SKColor.Parse("#39FF14") : (shape.Type == "circle" ? SKColor.Parse("#E000FF") : SKColors.Cyan);

                    using (var shapePaint = new SKPaint
                    {
                        Color = color,
                        Style = SKPaintStyle.Stroke,
                        StrokeWidth = (isSelected ? 3 : 2) / (float)renderZoom,
                        IsAntialias = true,
                        PathEffect = isSelected ? null : SKPathEffect.CreateDash(new float[] { 4 / (float)renderZoom, 4 / (float)renderZoom }, 0)
                    })
                    using (var labelPaint = new SKPaint
                    {
                        Color = color,
                        TextSize = 10 / (float)renderZoom,
                        IsAntialias = true
                    })
                    {
                        if (shape.Type == "circle")
                        {
                            float cx = (left + right) / 2;
                            float cy = (top + bottom) / 2;
                            float radius = (right - left) / 2;
                            canvas.DrawCircle(cx, cy, radius, shapePaint);
                        }
                        else
                        {
                            canvas.DrawRect(bbox, shapePaint);
                        }
                        canvas.DrawText($"{shape.Type.ToUpper()} ({shape.Width}x{shape.Height})", left, top - 2 / (float)renderZoom, labelPaint);
                    }
                }
            }

            canvas.Restore();

            // 5. Minimized Overlay
            if (IsMinimized)
            {
                using var overlayPaint = new SKPaint
                {
                    Color = SKColors.Black.WithAlpha(150),
                    Style = SKPaintStyle.Fill
                };
                canvas.DrawRect(0, 0, width, height, overlayPaint);

                using var textPaint = new SKPaint
                {
                    Color = SKColors.White,
                    TextSize = 24,
                    IsAntialias = true,
                    TextAlign = SKTextAlign.Center
                };
                canvas.DrawText("WINDOW MINIMIZED - VIEW FROZEN", width / 2, height / 2, textPaint);
            }

            // 6. Performance Overlay
            if (!isOverlay)
            {
                using (var perfPaint = new SKPaint { Color = SKColors.Lime, TextSize = 14, IsAntialias = true })
                {
                    MemoryUsageMb = GC.GetTotalMemory(false) / (1024 * 1024);
                    RenderTimeMs = (DateTime.Now - startTime).TotalMilliseconds;
                    
                    string perfText = $"FPS: {ActualFps:F1} | Render: {RenderTimeMs:F1}ms | RAM: {MemoryUsageMb}MB";
                    canvas.DrawText(perfText, 10, 25, perfPaint);
                }
            }

            // 7. Floating Inspector Overlay
            if (IsUiaVisible && HighlightedRect.HasValue && System.Windows.Input.Keyboard.Modifiers == System.Windows.Input.ModifierKeys.Alt)
            {
                var rect = HighlightedRect.Value;
                // Move to canvas coords
                var canvasRect = new SKRect(
                    (float)(rect.Left * renderZoom + renderOffset.X),
                    (float)(rect.Top * renderZoom + renderOffset.Y),
                    (float)((rect.Left + rect.Width) * renderZoom + renderOffset.X),
                    (float)((rect.Top + rect.Height) * renderZoom + renderOffset.Y)
                );

                using (var bgPaint = new SKPaint { Color = SKColors.Black.WithAlpha(180), Style = SKPaintStyle.Fill })
                using (var borderPaint = new SKPaint { Color = SKColors.Cyan, Style = SKPaintStyle.Stroke, StrokeWidth = 1 })
                using (var textPaint = new SKPaint { Color = SKColors.White, TextSize = 11, IsAntialias = true })
                {
                    float boxWidth = 200;
                    float boxHeight = 70;
                    float boxX = canvasRect.Right + 10;
                    float boxY = canvasRect.Top;

                    // Keep inside bounds
                    if (boxX + boxWidth > width) boxX = canvasRect.Left - boxWidth - 10;
                    if (boxY + boxHeight > height) boxY = height - boxHeight - 10;

                    var boxRect = new SKRect(boxX, boxY, boxX + boxWidth, boxY + boxHeight);
                    canvas.DrawRect(boxRect, bgPaint);
                    canvas.DrawRect(boxRect, borderPaint);

                    canvas.DrawText($"Type: {ActiveElementInfo?.Type}", boxX + 5, boxY + 15, textPaint);
                    canvas.DrawText($"ID: {ActiveElementInfo?.AutomationId}", boxX + 5, boxY + 30, textPaint);
                    canvas.DrawText($"Class: {ActiveElementInfo?.ClassName}", boxX + 5, boxY + 45, textPaint);
                    canvas.DrawText($"PID: {ActiveElementInfo?.ProcessId}", boxX + 5, boxY + 60, textPaint);
                }
            }

            // 8. Vision Overlays
            var now = DateTime.Now;
            for (int i = Overlays.Count - 1; i >= 0; i--)
            {
                var ov = Overlays[i];
                if (now > ov.Expiry)
                {
                    Overlays.RemoveAt(i);
                    continue;
                }

                using (var ovPaint = new SKPaint { Color = SKColors.Lime, Style = SKPaintStyle.Stroke, StrokeWidth = 1 })
                using (var labelPaint = new SKPaint { Color = SKColors.Lime, TextSize = 10, IsAntialias = true })
                {
                    canvas.DrawRect(ov.Bbox, ovPaint);
                    canvas.DrawText(ov.Text, ov.Bbox.Left, ov.Bbox.Top - 2, labelPaint);
                }
            }

            // 9. Coordinate Crosshair
            if (!IsMinimized)
            {
                var imgPos = _transformer.CanvasToImage(MousePos);
                using var crossPaint = new SKPaint { Color = SKColors.White.WithAlpha(100), Style = SKPaintStyle.Stroke, StrokeWidth = 1 };
                canvas.DrawLine(MousePos.X, 0, MousePos.X, height, crossPaint);
                canvas.DrawLine(0, MousePos.Y, width, MousePos.Y, crossPaint);

                using var tipPaint = new SKPaint { Color = SKColors.White, TextSize = 10, IsAntialias = true };
                string coordText = $"X: {(int)imgPos.X}, Y: {(int)imgPos.Y}";
                canvas.DrawText(coordText, MousePos.X + 5, MousePos.Y - 5, tipPaint);
            }
        }

        public record ElementDiagnosticInfo(string Type, string AutomationId, string ClassName, string ProcessId);
        public ElementDiagnosticInfo? ActiveElementInfo { get; set; }

        public record VisionOverlay(string Text, SKRect Bbox, DateTime Expiry);
        public ObservableCollection<VisionOverlay> Overlays { get; } = new();

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

        public void SampleColorAt(Point pos)
        {
            if (CurrentFrame == null) return;

            var imgPos = _transformer.CanvasToImage(new SKPoint((float)pos.X, (float)pos.Y));
            int x = (int)imgPos.X;
            int y = (int)imgPos.Y;

            if (x >= 0 && x < CurrentFrame.Width && y >= 0 && y < CurrentFrame.Height)
            {
                var color = CurrentFrame.GetPixel(x, y);
                PickedColor = $"#{color.Red:X2}{color.Green:X2}{color.Blue:X2}";
                Status = $"Color Picked: {PickedColor} at ({x}, {y})";
                
                // If a region is selected, update its color immediately
                if (SelectedRegion != null)
                {
                    SelectedRegion.Color = PickedColor;
                    OnPropertyChanged(nameof(SelectedRegion));
                    _ = _regionManager.SaveRegionsAsync(Regions);
                    _ = SyncRegionsToSidecar();
                }

                // If a color cluster is selected, append the color immediately
                if (SelectedColorCluster != null)
                {
                    if (!SelectedColorCluster.Colors.Contains(PickedColor))
                    {
                        SelectedColorCluster.Colors.Add(PickedColor);
                        _ = SaveColorClustersAsync();
                    }
                }

                // Auto-disable tool after success
                IsEyedropperActive = false;
            }
        }

        public void StartDrag(Point pos)
        {
            var imgPos = _transformer.CanvasToImage(new SKPoint((float)pos.X, (float)pos.Y));
            float handleSize = 10 / (float)ZoomLevel; 

            var region = Regions.LastOrDefault(r => 
                imgPos.X >= r.X - handleSize && imgPos.X <= r.X + r.Width + handleSize &&
                imgPos.Y >= r.Y - handleSize && imgPos.Y <= r.Y + r.Height + handleSize);
            
            if (region != null)
            {
                SelectedRegion = region;
                _dragStartPos = imgPos;
                _dragStartRect = new Rectangle(region.X, region.Y, region.Width, region.Height);

                bool nearLeft = Math.Abs(imgPos.X - region.X) < handleSize;
                bool nearRight = Math.Abs(imgPos.X - (region.X + region.Width)) < handleSize;
                bool nearTop = Math.Abs(imgPos.Y - region.Y) < handleSize;
                bool nearBottom = Math.Abs(imgPos.Y - (region.Y + region.Height)) < handleSize;

                if (nearLeft && nearTop) ActiveResizeEdge = ResizeEdge.TopLeft;
                else if (nearRight && nearTop) ActiveResizeEdge = ResizeEdge.TopRight;
                else if (nearLeft && nearBottom) ActiveResizeEdge = ResizeEdge.BottomLeft;
                else if (nearRight && nearBottom) ActiveResizeEdge = ResizeEdge.BottomRight;
                else
                {
                    ActiveResizeEdge = ResizeEdge.None;
                    IsDraggingRegion = true; 
                }
            }
            else
            {
                SelectedRegion = null;
            }
        }

        public void UpdateDrag(Point pos)
        {
            if (SelectedRegion == null) return;

            var currentPos = _transformer.CanvasToImage(new SKPoint((float)pos.X, (float)pos.Y));
            var deltaX = (int)(currentPos.X - _dragStartPos.X);
            var deltaY = (int)(currentPos.Y - _dragStartPos.Y);

            if (IsDraggingRegion)
            {
                SelectedRegion.X = _dragStartRect.X + deltaX;
                SelectedRegion.Y = _dragStartRect.Y + deltaY;
            }
            else if (ActiveResizeEdge != ResizeEdge.None)
            {
                switch (ActiveResizeEdge)
                {
                    case ResizeEdge.TopLeft:
                        SelectedRegion.X = _dragStartRect.X + deltaX;
                        SelectedRegion.Y = _dragStartRect.Y + deltaY;
                        SelectedRegion.Width = _dragStartRect.Width - deltaX;
                        SelectedRegion.Height = _dragStartRect.Height - deltaY;
                        break;
                    case ResizeEdge.BottomRight:
                        SelectedRegion.Width = _dragStartRect.Width + deltaX;
                        SelectedRegion.Height = _dragStartRect.Height + deltaY;
                        break;
                }
            }
            
            OnPropertyChanged(nameof(SelectedRegion));
        }

        public async Task EndDragAsync()
        {
            if ((IsDraggingRegion || ActiveResizeEdge != ResizeEdge.None) && SelectedRegion != null)
            {
                await _regionManager.SaveRegionsAsync(Regions);
                await SyncRegionsToSidecar();
            }
            IsDraggingRegion = false;
            ActiveResizeEdge = ResizeEdge.None;
        }

        public void StartCreation(Point pos)
        {
            IsCreatingRegion = true;
            _startCreationPos = _transformer.CanvasToImage(new SKPoint((float)pos.X, (float)pos.Y));
            _hasMouseMovedSignificantly = false;

            // Check if we clicked inside any detected shape
            DetectedShapeResult? clickedShape = null;
            double minArea = double.MaxValue;

            foreach (var shape in DetectedShapes)
            {
                if (_startCreationPos.X >= shape.X && _startCreationPos.X <= shape.X + shape.Width &&
                    _startCreationPos.Y >= shape.Y && _startCreationPos.Y <= shape.Y + shape.Height)
                {
                    double area = shape.Width * shape.Height;
                    if (area < minArea)
                    {
                        minArea = area;
                        clickedShape = shape;
                    }
                }
            }

            if (clickedShape != null)
            {
                SelectedDetectedShape = clickedShape;
                
                // Instantly pre-populate creation region with the detected shape's bounds
                CurrentCreationRegion = new RegionModel 
                { 
                    X = clickedShape.X, 
                    Y = clickedShape.Y,
                    Width = clickedShape.Width,
                    Height = clickedShape.Height,
                    Color = PickedColor
                };
                // Align start position to shape's top-left to support instant MouseUp saving
                _startCreationPos = new SKPoint(clickedShape.X, clickedShape.Y);
            }
            else
            {
                SelectedDetectedShape = null;
                CurrentCreationRegion = new RegionModel 
                { 
                    X = (int)_startCreationPos.X, 
                    Y = (int)_startCreationPos.Y,
                    Width = 0,
                    Height = 0,
                    Color = "#FFFF00"
                };
            }
        }

        public void UpdateCreation(Point pos)
        {
            if (!IsCreatingRegion || CurrentCreationRegion == null) return;

            var currentPos = _transformer.CanvasToImage(new SKPoint((float)pos.X, (float)pos.Y));
            
            // Track if user dragged significantly (e.g. > 3 pixels in image space) from the creation start pos
            double dist = Math.Sqrt(Math.Pow(currentPos.X - _startCreationPos.X, 2) + Math.Pow(currentPos.Y - _startCreationPos.Y, 2));
            if (dist > 3)
            {
                _hasMouseMovedSignificantly = true;
            }

            if (_hasMouseMovedSignificantly || SelectedDetectedShape == null)
            {
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
        }

        public async Task EndCreationAsync()
        {
            if (IsCreatingRegion && CurrentCreationRegion != null)
            {
                if (SelectedDetectedShape != null && !_hasMouseMovedSignificantly)
                {
                    // Plain click inside a shape (no significant dragging). 
                    // Select it so the neon green highlight draws, but don't add to static regions yet.
                    // The user can now click "SAVE SHAPE" to save it by choice!
                    CurrentCreationRegion = null;
                }
                else if (CurrentCreationRegion.Width > 2 && CurrentCreationRegion.Height > 2)
                {
                    CurrentCreationRegion.Color = PickedColor; // Heritage logic: Use the current picked color
                    CurrentCreationRegion.Name = $"Region {Regions.Count}";
                    
                    if (SelectedWindow != null)
                    {
                        CurrentCreationRegion.WindowTitle = SelectedWindow.Title;
                        CurrentCreationRegion.WindowClass = SelectedWindow.ClassName;
                    }

                    Regions.Add(CurrentCreationRegion);
                    SelectedRegion = CurrentCreationRegion;
                    SelectedDetectedShape = null; // Clear shape selection since we drew a custom region
                    await _regionManager.SaveRegionsAsync(Regions);
                    await SyncRegionsToSidecar();
                }
                else
                {
                    // Plain click (no drag). Check if we clicked on an existing region
                    var clickedRegion = Regions.LastOrDefault(r => 
                        _startCreationPos.X >= r.X && _startCreationPos.X <= r.X + r.Width &&
                        _startCreationPos.Y >= r.Y && _startCreationPos.Y <= r.Y + r.Height);
                    if (clickedRegion != null)
                    {
                        SelectedRegion = clickedRegion;
                        SelectedDetectedShape = null;
                    }
                    else
                    {
                        // Clicked empty space: clear selections
                        SelectedRegion = null;
                        SelectedDetectedShape = null;
                    }
                }
            }
            IsCreatingRegion = false;
            CurrentCreationRegion = null;
        }

        public Point ImageToScreen(SKPoint p)
        {
            var windowRect = GetWindowRect();
            if (!windowRect.HasValue) return new Point(0, 0);
            
            return new Point(windowRect.Value.Left + p.X, windowRect.Value.Top + p.Y);
        }

        public SKPoint ScreenToImage(Point p)
        {
            return _transformer.CanvasToImage(new SKPoint((float)p.X, (float)p.Y));
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
            
            _transformer.UpdateTransform(Offset, ZoomLevel);
        }

        public void UpdatePan(Point pos, Point lastPos)
        {
            var deltaX = (float)(pos.X - lastPos.X);
            var deltaY = (float)(pos.Y - lastPos.Y);
            Offset = new SKPoint(Offset.X + deltaX, Offset.Y + deltaY);
            
            _transformer.UpdateTransform(Offset, ZoomLevel);
        }

        public void Dispose()
        {
            try { _bgDetectionCts.Cancel(); } catch {}
            try { _bgDetectionCts.Dispose(); } catch {}
            _reflectionService.Stop();
            _screenshotService.Dispose();
        }

        public System.Windows.Rect? GetWindowRect()
        {
            if (SelectedWindow == null) return null;
            var svc = new ScreenshotService();
            if (svc.GetTrueClientScreenRect(SelectedWindow.Handle, out ScreenshotService.RECT rect))
            {
                return new System.Windows.Rect(rect.Left, rect.Top, rect.Right - rect.Left, rect.Bottom - rect.Top);
            }
            return null;
        }

        public void UpdateTransformerState()
        {
            _transformer.UpdateTransform(Offset, ZoomLevel);
        }

        public void UpdateTransformerStateForOverlay()
        {
            _transformer.UpdateTransform(new SKPoint(0, 0), 1.0);
        }

        public void HighlightScreenRect(System.Windows.Rect screenRect)
        {
            var windowRect = GetWindowRect();
            if (windowRect.HasValue)
            {
                HighlightedRect = _transformer.ScreenToImage(screenRect, windowRect.Value);
            }
        }
    }
}
