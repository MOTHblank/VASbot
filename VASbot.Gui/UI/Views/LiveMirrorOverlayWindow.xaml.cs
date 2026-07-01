using System;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Threading;
using System.Windows.Media;
using SkiaSharp;
using SkiaSharp.Views.Desktop;
using SkiaSharp.Views.WPF;
using VASbot.Gui.UI.ViewModels;

namespace VASbot.Gui.UI.Views
{
    public partial class LiveMirrorOverlayWindow : Window
    {
        private const int GWL_EXSTYLE = -20;
        private const int WS_EX_TRANSPARENT = 0x20;

        [DllImport("user32.dll", SetLastError = true)]
        private static extern int GetWindowLong(IntPtr hWnd, int nIndex);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern int SetWindowLong(IntPtr hWnd, int nIndex, int dwNewLong);

        [DllImport("user32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool IsWindow(IntPtr hWnd);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern uint GetDpiForWindow(IntPtr hwnd);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

        [DllImport("user32.dll")]
        private static extern IntPtr GetForegroundWindow();

        [DllImport("user32.dll")]
        private static extern bool SetWindowDisplayAffinity(IntPtr hWnd, uint dwAffinity);

        private const uint WDA_EXCLUDEFROMCAPTURE = 0x00000011;

        private delegate void WinEventProc(
            IntPtr hWinEventHook, 
            uint @event, 
            IntPtr hwnd, 
            int idObject, 
            int idChild, 
            uint dwEventThread, 
            uint dwmsEventTime);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern IntPtr SetWinEventHook(
            uint eventMin, 
            uint eventMax, 
            IntPtr hmodWinEventProc, 
            WinEventProc lpfnWinEventProc, 
            uint idProcess, 
            uint idThread, 
            uint dwFlags);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern bool UnhookWinEvent(IntPtr hWinEventHook);

        private const uint EVENT_OBJECT_DESTROY = 0x8001;
        private const uint EVENT_OBJECT_SHOW = 0x8002;
        private const uint EVENT_OBJECT_HIDE = 0x8003;
        private const uint EVENT_OBJECT_LOCATIONCHANGE = 0x800B;
        private const uint WINEVENT_OUTOFCONTEXT = 0;

        private readonly MainViewModel _viewModel;
        private DispatcherTimer? _positionTimer;
        private bool _isCreatingRegion;
        private bool _isDraggingRegion;

        private WinEventProc? _winEventProc;
        private IntPtr _winEventHook = IntPtr.Zero;

        public LiveMirrorOverlayWindow(MainViewModel viewModel)
        {
            InitializeComponent();
            _viewModel = viewModel;
            DataContext = _viewModel;

            this.Loaded += (s, e) => {
                var hwnd = new WindowInteropHelper(this).Handle;
                if (hwnd != IntPtr.Zero)
                {
                    try
                    {
                        SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE);
                    }
                    catch { }
                }
                UpdateClickThroughState();
                UpdatePositionAndSize();
                SetupWinEventHook();
            };

            this.Closed += (s, e) => {
                StopWinEventHook();
                if (_positionTimer != null)
                {
                    _positionTimer.Stop();
                    _positionTimer = null;
                }
            };

            SetupCaptureInvalidation();
            StartPositionTimer();
        }

        private void UpdateClickThroughState()
        {
            if (_viewModel?.Capture == null) return;
            bool clickThrough = _viewModel.Capture.IsOverlayClickThrough;
            
            // WPF hit test
            SkiaElement.IsHitTestVisible = !clickThrough;

            // Win32 exstyle
            var hwnd = new WindowInteropHelper(this).Handle;
            if (hwnd != IntPtr.Zero)
            {
                int extendedStyle = GetWindowLong(hwnd, GWL_EXSTYLE);
                if (clickThrough)
                {
                    SetWindowLong(hwnd, GWL_EXSTYLE, extendedStyle | WS_EX_TRANSPARENT);
                }
                else
                {
                    SetWindowLong(hwnd, GWL_EXSTYLE, extendedStyle & ~WS_EX_TRANSPARENT);
                }
            }
        }

        private void StartPositionTimer()
        {
            _positionTimer = new DispatcherTimer();
            _positionTimer.Interval = TimeSpan.FromMilliseconds(150);
            _positionTimer.Tick += (s, e) => {
                if (_viewModel?.Capture?.SelectedWindow != null)
                {
                    IntPtr hwnd = _viewModel.Capture.SelectedWindow.Handle;
                    if (!IsWindow(hwnd))
                    {
                        if (_viewModel.Capture != null)
                        {
                            _viewModel.Capture.IsOverlayMirrorActive = false;
                        }
                        return;
                    }
                }
                UpdatePositionAndSize();
            };
            _positionTimer.Start();
        }

        private double GetTargetDpiScale()
        {
            if (_viewModel?.Capture?.SelectedWindow != null)
            {
                try
                {
                    uint dpi = GetDpiForWindow(_viewModel.Capture.SelectedWindow.Handle);
                    if (dpi > 0)
                    {
                        return dpi / 96.0;
                    }
                }
                catch { }
            }

            try
            {
                var dpi = VisualTreeHelper.GetDpi(this);
                return dpi.DpiScaleX;
            }
            catch
            {
                return 1.0;
            }
        }

        private void SetupWinEventHook()
        {
            if (_winEventHook != IntPtr.Zero) return;

            uint processId = 0;
            uint threadId = 0;

            if (_viewModel?.Capture?.SelectedWindow != null)
            {
                IntPtr targetHwnd = _viewModel.Capture.SelectedWindow.Handle;
                threadId = GetWindowThreadProcessId(targetHwnd, out processId);
            }

            _winEventProc = new WinEventProc(OnWinEvent);
            _winEventHook = SetWinEventHook(
                EVENT_OBJECT_DESTROY,
                EVENT_OBJECT_LOCATIONCHANGE,
                IntPtr.Zero,
                _winEventProc,
                processId,
                threadId,
                WINEVENT_OUTOFCONTEXT);
        }

        private void StopWinEventHook()
        {
            if (_winEventHook != IntPtr.Zero)
            {
                UnhookWinEvent(_winEventHook);
                _winEventHook = IntPtr.Zero;
            }
            _winEventProc = null;
        }

        private void OnWinEvent(IntPtr hWinEventHook, uint @event, IntPtr hwnd, int idObject, int idChild, uint dwEventThread, uint dwmsEventTime)
        {
            if (_viewModel?.Capture?.SelectedWindow == null) return;

            IntPtr targetHwnd = _viewModel.Capture.SelectedWindow.Handle;
            if (hwnd == targetHwnd && idObject == 0) // idObject == 0 is OBJID_WINDOW
            {
                switch (@event)
                {
                    case EVENT_OBJECT_DESTROY:
                        Dispatcher.BeginInvoke(new Action(() => {
                            if (_viewModel.Capture != null)
                            {
                                _viewModel.Capture.IsOverlayMirrorActive = false;
                            }
                        }));
                        break;

                    case EVENT_OBJECT_LOCATIONCHANGE:
                    case EVENT_OBJECT_SHOW:
                    case EVENT_OBJECT_HIDE:
                        Dispatcher.BeginInvoke(new Action(() => UpdatePositionAndSize()));
                        break;
                }
            }
        }

        private void UpdatePositionAndSize()
        {
            if (_viewModel?.Capture == null) return;

            if (_viewModel.Capture.SelectedWindow == null)
            {
                Close();
                return;
            }

            // Check if the foreground window is either:
            // 1. The target window
            // 2. A window belonging to our own process (the overlay itself, the main app, etc.)
            IntPtr foregroundHwnd = GetForegroundWindow();
            bool shouldBeVisible = false;

            if (foregroundHwnd != IntPtr.Zero)
            {
                IntPtr targetHwnd = _viewModel.Capture.SelectedWindow.Handle;
                if (foregroundHwnd == targetHwnd)
                {
                    shouldBeVisible = true;
                }
                else
                {
                    GetWindowThreadProcessId(foregroundHwnd, out uint foregroundPid);
                    uint currentPid = (uint)System.Diagnostics.Process.GetCurrentProcess().Id;
                    if (foregroundPid == currentPid)
                    {
                        shouldBeVisible = true;
                    }
                }
            }

            if (!shouldBeVisible)
            {
                if (this.Visibility != Visibility.Collapsed)
                {
                    this.Visibility = Visibility.Collapsed;
                }
                return;
            }

            var rect = _viewModel.Capture.GetWindowRect();
            if (rect.HasValue && rect.Value.Width > 0 && rect.Value.Height > 0)
            {
                if (this.Visibility != Visibility.Visible)
                {
                    this.Visibility = Visibility.Visible;
                }

                try
                {
                    double scale = GetTargetDpiScale();

                    double newLeft = rect.Value.Left / scale;
                    double newTop = rect.Value.Top / scale;
                    double newWidth = rect.Value.Width / scale;
                    double newHeight = rect.Value.Height / scale;

                    if (Math.Abs(this.Left - newLeft) > 0.1 ||
                        Math.Abs(this.Top - newTop) > 0.1 ||
                        Math.Abs(this.Width - newWidth) > 0.1 ||
                        Math.Abs(this.Height - newHeight) > 0.1)
                    {
                        this.Left = newLeft;
                        this.Top = newTop;
                        this.Width = newWidth;
                        this.Height = newHeight;
                    }
                }
                catch { }
            }
            else
            {
                if (this.Visibility != Visibility.Collapsed)
                {
                    this.Visibility = Visibility.Collapsed;
                }
            }
        }

        private void SetupCaptureInvalidation()
        {
            _viewModel.Capture.PropertyChanged += (s, e) => {
                if (e.PropertyName == nameof(CaptureViewModel.CurrentFrame) || 
                    e.PropertyName == nameof(CaptureViewModel.ZoomLevel) ||
                    e.PropertyName == nameof(CaptureViewModel.Offset) ||
                    e.PropertyName == nameof(CaptureViewModel.HighlightedRect) ||
                    e.PropertyName == nameof(CaptureViewModel.IsRegionsVisible) ||
                    e.PropertyName == nameof(CaptureViewModel.IsShapesVisible) ||
                    e.PropertyName == nameof(CaptureViewModel.IsClustersVisible) ||
                    e.PropertyName == nameof(CaptureViewModel.IsUiaVisible) ||
                    e.PropertyName == nameof(CaptureViewModel.CurrentCreationRegion) ||
                    e.PropertyName == nameof(CaptureViewModel.IsCreatingRegion) ||
                    e.PropertyName == nameof(CaptureViewModel.DetectedShapes))
                {
                    Application.Current.Dispatcher.Invoke(() => SkiaElement.InvalidateVisual());
                }
                else if (e.PropertyName == nameof(CaptureViewModel.IsOverlayClickThrough))
                {
                    Application.Current.Dispatcher.Invoke(() => UpdateClickThroughState());
                }
            };
        }

        private void SkiaElement_PaintSurface(object sender, SKPaintSurfaceEventArgs e)
        {
            _viewModel.Capture.Render(e.Surface.Canvas, (float)e.Info.Width, (float)e.Info.Height, isOverlay: true);
        }

        private void SkiaElement_MouseDown(object sender, MouseButtonEventArgs e)
        {
            var pos = e.GetPosition(SkiaElement);
            
            _viewModel.Capture.UpdateTransformerStateForOverlay();

            if (_viewModel.Capture.IsEyedropperActive)
            {
                _viewModel.Capture.SampleColorAt(pos);
                e.Handled = true;
                return;
            }

            if (e.ChangedButton == MouseButton.Left && Keyboard.Modifiers == ModifierKeys.Shift)
            {
                SkiaElement.CaptureMouse();
                _viewModel.Capture.StartDrag(pos);
                _isDraggingRegion = true;
            }
            else if (e.ChangedButton == MouseButton.Left)
            {
                SkiaElement.CaptureMouse();
                _viewModel.Capture.StartCreation(pos);
                _isCreatingRegion = true;
            }
        }

        private void SkiaElement_MouseMove(object sender, MouseEventArgs e)
        {
            var pos = e.GetPosition(SkiaElement);
            
            _viewModel.Capture.UpdateTransformerStateForOverlay();
            _viewModel.Capture.MousePos = new SKPoint((float)pos.X, (float)pos.Y);

            var imgPos = _viewModel.Capture.ScreenToImage(pos);
            _viewModel.Capture.TelemetryCoords = $"Canvas: ({(int)pos.X}, {(int)pos.Y}) | Game: ({(int)imgPos.X}, {(int)imgPos.Y})";

            if (_viewModel.Capture.CurrentFrame != null)
            {
                int x = (int)imgPos.X;
                int y = (int)imgPos.Y;
                if (x >= 0 && x < _viewModel.Capture.CurrentFrame.Width && y >= 0 && y < _viewModel.Capture.CurrentFrame.Height)
                {
                    var color = _viewModel.Capture.CurrentFrame.GetPixel(x, y);
                    _viewModel.Capture.TelemetryColorHex = $"#{color.Red:X2}{color.Green:X2}{color.Blue:X2}";
                }
            }

            if (_isCreatingRegion)
            {
                _viewModel.Capture.UpdateCreation(pos);
            }
            else if (_isDraggingRegion)
            {
                _viewModel.Capture.UpdateDrag(pos);
            }
            else
            {
                if (Keyboard.Modifiers == ModifierKeys.Alt)
                {
                    var screenPos = _viewModel.Capture.ImageToScreen(imgPos);
                    var node = _viewModel.AutomationTree.FindNodeAt(screenPos.X, screenPos.Y);
                    if (node != null)
                    {
                        _viewModel.AutomationTree.SelectedNode = node;
                        _viewModel.Inspector.Update(node);
                        _viewModel.Capture.ActiveElementInfo = new CaptureViewModel.ElementDiagnosticInfo(
                            node.Type, node.AutomationId, node.Element.Current.ClassName, node.Element.Current.ProcessId.ToString()
                        );
                        _viewModel.Capture.TelemetryElementInfo = $"{node.Type} (ID: {node.AutomationId}, Class: {node.Element.Current.ClassName})";
                    }
                    else
                    {
                        _viewModel.Capture.TelemetryElementInfo = "No automation element found";
                    }
                }
                else
                {
                    _viewModel.Inspector.Update(null);
                    _viewModel.Capture.ActiveElementInfo = null;
                    _viewModel.Capture.TelemetryElementInfo = "None (Hold Alt)";
                }
            }

            SkiaElement.InvalidateVisual();
        }

        private async void SkiaElement_MouseUp(object sender, MouseButtonEventArgs e)
        {
            _viewModel.Capture.UpdateTransformerStateForOverlay();

            if (_isCreatingRegion)
            {
                _isCreatingRegion = false;
                await _viewModel.Capture.EndCreationAsync();
                SkiaElement.ReleaseMouseCapture();
            }
            else if (_isDraggingRegion)
            {
                _isDraggingRegion = false;
                await _viewModel.Capture.EndDragAsync();
                SkiaElement.ReleaseMouseCapture();
            }
        }
    }
}
