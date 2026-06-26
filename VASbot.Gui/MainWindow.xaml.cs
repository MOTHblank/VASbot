using System;
using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Input;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Xml;
using ICSharpCode.AvalonEdit;
using ICSharpCode.AvalonEdit.Highlighting;
using ICSharpCode.AvalonEdit.Highlighting.Xshd;
using ICSharpCode.AvalonEdit.Rendering;
using ModernWpf;
using SkiaSharp;
using SkiaSharp.Views.Desktop;
using VASbot.Gui.Engine;
using VASbot.Gui.UI.ViewModels;
using Point = System.Windows.Point;

namespace VASbot.Gui
{
    public partial class MainWindow : Window
    {
        private readonly MainViewModel _viewModel;
        private readonly PythonSidecarService _sidecar;
        private readonly SharedMemoryService _sharedMemory;
        private HotkeyService? _hotkeyService;
        private GlobalHotkeyService? _globalHotkeyService;
        private ErrorLineBackgroundRenderer? _errorRenderer;
        private ToolTip? _imageTooltip;

        public MainWindow(
            MainViewModel viewModel, 
            PythonSidecarService sidecar, 
            SharedMemoryService sharedMemory)
        {
            InitializeComponent();
            _viewModel = viewModel;
            _sidecar = sidecar;
            _sharedMemory = sharedMemory;

            DataContext = _viewModel;

            LoadPythonSyntax();
            InitializeSidecar();
            SetupEventHandlers();
            ThemeManager.Current.ApplicationTheme = ApplicationTheme.Dark;
        }

        private void InitializeSidecar()
        {
            _sidecar.Start();
        }

        private void SetupEventHandlers()
        {
            SetupScriptEditorSync();
            SetupCaptureInvalidation();
            SetupGlobalHotkeys();
            SetupTemplateListener();
        }

        private void SetupScriptEditorSync()
        {
            // Initialize editor text from VM
            ScriptEditor.Text = _viewModel.ScriptEditor.ScriptText;

            // Configure modern dark mode aesthetic theme for AvalonEdit
            ScriptEditor.Background = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(18, 18, 18));
            ScriptEditor.Foreground = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(224, 224, 224));
            ScriptEditor.LineNumbersForeground = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(90, 90, 90));

            // Initialize error renderer
            _errorRenderer = new ErrorLineBackgroundRenderer(ScriptEditor);
            ScriptEditor.TextArea.TextView.BackgroundRenderers.Add(_errorRenderer);

            // Listen for external script text changes (e.g., file load) to update editor
            _viewModel.ScriptEditor.ScriptTextUpdated += () => {
                Dispatcher.Invoke(() => {
                    if (!_isSyncingText && ScriptEditor.Text != _viewModel.ScriptEditor.ScriptText)
                    {
                        _isSyncingText = true;
                        ScriptEditor.Text = _viewModel.ScriptEditor.ScriptText;
                        _isSyncingText = false;
                    }
                });
            };

            // Listen to VM property changes for ErrorLineNumber to highlight and scroll
            _viewModel.ScriptEditor.PropertyChanged += (s, ev) => {
                if (ev.PropertyName == nameof(ScriptEditorViewModel.ErrorLineNumber))
                {
                    Dispatcher.Invoke(() => {
                        int lineNum = _viewModel.ScriptEditor.ErrorLineNumber;
                        if (_errorRenderer != null)
                        {
                            _errorRenderer.ErrorLineNumber = lineNum;
                        }
                        if (lineNum > 0 && lineNum <= ScriptEditor.Document.LineCount)
                        {
                            ScriptEditor.ScrollTo(lineNum, 1);
                        }
                    });
                }
            };
        }

        private void SetupCaptureInvalidation()
        {
            // Invalidation trigger for the Skia canvas
            _viewModel.Capture.PropertyChanged += (s, e) => {
                if (e.PropertyName == nameof(CaptureViewModel.CurrentFrame) || 
                    e.PropertyName == nameof(CaptureViewModel.ZoomLevel) ||
                    e.PropertyName == nameof(CaptureViewModel.Offset) ||
                    e.PropertyName == nameof(CaptureViewModel.HighlightedRect))
                {
                    Application.Current.Dispatcher.Invoke(() => SkiaElement.InvalidateVisual());
                }
            };
        }

        private void SetupGlobalHotkeys()
        {
            // Global Hotkey Registration - works even when window is not focused!
            // F5 = Run, F6 = Stop, F12 = Killswitch
            try
            {
                Action runAction = () => {
                    Application.Current.Dispatcher.Invoke(() => {
                        try { _viewModel.ScriptEditor.RunScriptCommand.Execute(null); } catch { }
                    });
                };
                
                Action stopAction = () => {
                    Application.Current.Dispatcher.Invoke(() => {
                        try { _viewModel.ScriptEditor.StopScriptCommand.Execute(null); } catch { }
                    });
                };
                
                Action killAction = () => {
                    Application.Current.Dispatcher.Invoke(() => {
                        try
                        {
                            // Stop the script first
                            _viewModel.ScriptEditor.StopScriptCommand.Execute(null);
                            
                            // Kill all Python processes
                            foreach (var process in System.Diagnostics.Process.GetProcessesByName("python"))
                            {
                                try { process.Kill(); } catch { }
                            }
                            foreach (var process in System.Diagnostics.Process.GetProcessesByName("python3"))
                            {
                                try { process.Kill(); } catch { }
                            }
                            
                            // Kill the GUI itself
                            System.Diagnostics.Process.GetCurrentProcess().Kill();
                        }
                        catch { }
                    });
                };
                
                _globalHotkeyService = new GlobalHotkeyService(runAction, stopAction, killAction);
                _globalHotkeyService.Start();
                Console.WriteLine("[Hotkeys] Global F5/F6/F12 hotkeys registered");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[Hotkeys] Failed to register global hotkeys: {ex.Message}");
                
                // Fallback to window-bound hotkeys if global fails
                var hwnd = new System.Windows.Interop.WindowInteropHelper(this).Handle;
                _hotkeyService = new HotkeyService(hwnd);
                _hotkeyService.Register(ModifierKeys.None, Key.F5, () => _viewModel.ScriptEditor.RunScriptCommand.Execute(null));
                _hotkeyService.Register(ModifierKeys.None, Key.F6, () => _viewModel.ScriptEditor.StopScriptCommand.Execute(null));
            }
        }

        private void SetupTemplateListener()
        {
            // Template system listener
            _viewModel.Templates.TemplateApplied += (code) => {
                ScriptEditor.Document.Replace(ScriptEditor.SelectionStart, ScriptEditor.SelectionLength, code);
            };
        }

        private void LoadPythonSyntax()
        {
            try
            {
                string xshdPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Resources", "Python.xshd");
                if (File.Exists(xshdPath))
                {
                    using (Stream s = File.OpenRead(xshdPath))
                    using (XmlTextReader reader = new XmlTextReader(s))
                    {
                        ScriptEditor.SyntaxHighlighting = HighlightingLoader.Load(reader, HighlightingManager.Instance);
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[UI] Failed to load syntax: {ex.Message}");
            }
        }

        private bool _isSyncingText = false;
        
        private void ScriptEditor_TextChanged(object sender, EventArgs e)
        {
            if (_isSyncingText) return;
            
            try
            {
                _isSyncingText = true;
                if (_viewModel?.ScriptEditor != null)
                {
                    _viewModel.ScriptEditor.ScriptText = ScriptEditor.Text;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"ScriptEditor_TextChanged error: {ex.Message}");
            }
            finally
            {
                _isSyncingText = false;
            }
        }

        private void Terminal_TextChanged(object sender, System.Windows.Controls.TextChangedEventArgs e)
        {
            if (sender is System.Windows.Controls.TextBox tb)
            {
                tb.ScrollToEnd();
            }
        }

        private void SkiaElement_PaintSurface(object sender, SKPaintSurfaceEventArgs e)
        {
            _viewModel.Capture.Render(e.Surface.Canvas, (float)e.Info.Width, (float)e.Info.Height);
        }

        private void AutomationTree_SelectedItemChanged(object sender, RoutedPropertyChangedEventArgs<object> e)
        {
            if (e.NewValue is AutomationTreeViewModel.AutomationNode node)
            {
                _viewModel.AutomationTree.SelectedNode = node;
            }
        }

        private void InsertTemplate_Click(object sender, RoutedEventArgs e)
        {
            _viewModel.Templates.ApplyTemplate(ScriptEditor.SelectedText);
        }

        private void SaveSnippet_Click(object sender, RoutedEventArgs e)
        {
            string text = ScriptEditor.SelectedText;
            if (string.IsNullOrEmpty(text))
            {
                text = ScriptEditor.Text; // fallback to all
            }
            string name = SnippetNameInput.Text;
            if (string.IsNullOrWhiteSpace(name)) name = "My Snippet " + DateTime.Now.ToString("HHmmss");

            _viewModel.Templates.SaveSnippet(name, text);
            SnippetNameInput.Text = "";
        }

        private void InsertImage_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                var dialog = new Microsoft.Win32.OpenFileDialog
                {
                    Filter = "PNG Image (*.png)|*.png|All Files (*.*)|*.*",
                    Title = "Select Image Template to Insert"
                };

                // Try to set initial directory to the project's /img directory
                try
                {
                    string baseDir = AppDomain.CurrentDomain.BaseDirectory;
                    string? current = baseDir;
                    while (current != null)
                    {
                        string imgPath = Path.Combine(current, "img");
                        if (Directory.Exists(imgPath))
                        {
                            dialog.InitialDirectory = imgPath;
                            break;
                        }
                        current = Path.GetDirectoryName(current);
                    }
                }
                catch { }

                if (dialog.ShowDialog() == true)
                {
                    string fullPath = dialog.FileName;
                    string fileName = Path.GetFileName(fullPath);
                    
                    // Format template code:
                    // Use simple relative pathing: "img/filename.png"
                    string relativePath = "img/" + fileName;
                    string codeSnippet = $"pos = bot.find_image(\"{relativePath}\", region_index=None, confidence=0.8)\nif pos:\n    bot.click(pos[0], pos[1], button='left', human_like=True)";
                    
                    ScriptEditor.Document.Replace(ScriptEditor.SelectionStart, ScriptEditor.SelectionLength, codeSnippet);
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Failed to insert image template: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void Killswitch_Click(object sender, RoutedEventArgs e)
        {
            // F12 KILLSWITCH - Forcefully stop everything
            try
            {
                // Stop the script first
                _viewModel.ScriptEditor.StopScriptCommand.Execute(null);
                
                // Kill all Python processes
                foreach (var process in System.Diagnostics.Process.GetProcessesByName("python"))
                {
                    try { process.Kill(); } catch { }
                }
                foreach (var process in System.Diagnostics.Process.GetProcessesByName("python3"))
                {
                    try { process.Kill(); } catch { }
                }
                
                // Also kill the VASbot GUI itself
                System.Diagnostics.Process.GetCurrentProcess().Kill();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Killswitch error: {ex.Message}");
            }
        }

        private async void RegionName_LostFocus(object sender, RoutedEventArgs e)
        {
            await _viewModel.Capture.EndDragAsync(); // Re-use the save/sync logic
        }

        // --- Interaction Handlers ---

        private void SkiaElement_MouseDown(object sender, MouseButtonEventArgs e)
        {
            var pos = e.GetPosition(SkiaElement);
            if (_viewModel.Capture.IsEyedropperActive)
            {
                _viewModel.Capture.SampleColorAt(pos);
                e.Handled = true;
                return;
            }

            if (e.ChangedButton == MouseButton.Middle || (e.ChangedButton == MouseButton.Left && Keyboard.Modifiers == ModifierKeys.Control))
            {
                SkiaElement.CaptureMouse();
                _mouseDownPos = pos;
                _isPanning = true;
            }
            else if (e.ChangedButton == MouseButton.Left && Keyboard.Modifiers == ModifierKeys.Shift)
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

        private bool _isPanning;
        private bool _isCreatingRegion;
        private bool _isDraggingRegion;
        private Point _mouseDownPos;

        private void SkiaElement_MouseMove(object sender, MouseEventArgs e)
        {
            var pos = e.GetPosition(SkiaElement);
            _viewModel.Capture.MousePos = new SKPoint((float)pos.X, (float)pos.Y);

            // Live Telemetry Coords & Color sampling
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

            if (_isPanning)
            {
                _viewModel.Capture.UpdatePan(pos, _mouseDownPos);
                _mouseDownPos = pos;
            }
            else if (_isCreatingRegion)
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

            // Smooth live rendering for cursor/crosshairs
            SkiaElement.InvalidateVisual();
        }

        private async void SkiaElement_MouseUp(object sender, MouseButtonEventArgs e)
        {
            if (_isPanning)
            {
                _isPanning = false;
                SkiaElement.ReleaseMouseCapture();
            }
            else if (_isCreatingRegion)
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

        private void SkiaElement_MouseWheel(object sender, MouseWheelEventArgs e)
        {
            _viewModel.Capture.Zoom(e.Delta, e.GetPosition(SkiaElement));
        }

        protected override void OnClosed(EventArgs e)
        {
            // Note: Services are stopped by the AppHost in App.xaml.cs, 
            // but we ensure immediate disposal here if necessary.
            _viewModel.Capture.Dispose();
            _sidecar.Stop();
            _sharedMemory.Dispose();
            _globalHotkeyService?.Dispose();
            _hotkeyService?.Dispose();
            base.OnClosed(e);
        }

        private void ToggleDrawer_Click(object sender, RoutedEventArgs e)
        {
            if (SnippetDrawer.Visibility == Visibility.Visible)
            {
                SnippetDrawer.Visibility = Visibility.Collapsed;
            }
            else
            {
                SnippetDrawer.Visibility = Visibility.Visible;
            }
        }

        private void SnippetList_MouseDoubleClick(object sender, MouseButtonEventArgs e)
        {
            if (sender is ListBox listBox && listBox.SelectedItem is ListBoxItem item)
            {
                string snippet = item.Tag as string ?? "";
                if (!string.IsNullOrEmpty(snippet))
                {
                    ScriptEditor.Document.Replace(ScriptEditor.SelectionStart, ScriptEditor.SelectionLength, snippet);
                    ScriptEditor.Focus();
                }
            }
        }

        private void ScriptEditor_PreviewMouseMove(object sender, MouseEventArgs e)
        {
            try
            {
                var textView = ScriptEditor.TextArea.TextView;
                var pos = e.GetPosition(textView);
                var position = textView.GetPositionFloor(pos);
                
                if (position.HasValue)
                {
                    int lineNum = position.Value.Line;
                    if (lineNum > 0 && lineNum <= ScriptEditor.Document.LineCount)
                    {
                        var line = ScriptEditor.Document.GetLineByNumber(lineNum);
                        string lineText = ScriptEditor.Document.GetText(line.Offset, line.Length);
                        
                        var matches = System.Text.RegularExpressions.Regex.Matches(lineText, @"[""']([^""']+\.png)[""']");
                        bool foundPng = false;
                        
                        foreach (System.Text.RegularExpressions.Match match in matches)
                        {
                            int startColumn = match.Index + 1; // 1-based column
                            int endColumn = startColumn + match.Length;
                            
                            int cursorColumn = position.Value.Column;
                            if (cursorColumn >= startColumn && cursorColumn <= endColumn)
                            {
                                string relativePath = match.Groups[1].Value;
                                ShowImageTooltip(relativePath);
                                foundPng = true;
                                break;
                            }
                        }
                        
                        if (!foundPng)
                        {
                            HideImageTooltip();
                        }
                    }
                    else
                    {
                        HideImageTooltip();
                    }
                }
                else
                {
                    HideImageTooltip();
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Image hover parse error: {ex.Message}");
                HideImageTooltip();
            }
        }

        private void ShowImageTooltip(string relativePath)
        {
            if (_imageTooltip != null && _imageTooltip.IsOpen && _imageTooltip.Tag as string == relativePath)
            {
                return;
            }

            try
            {
                string absolutePath = relativePath;
                if (!Path.IsPathRooted(absolutePath))
                {
                    string baseDir = AppDomain.CurrentDomain.BaseDirectory;
                    string? current = baseDir;
                    while (current != null)
                    {
                        string candidate = Path.Combine(current, relativePath);
                        if (File.Exists(candidate))
                        {
                            absolutePath = candidate;
                            break;
                        }
                        if (relativePath.StartsWith("img/"))
                        {
                            string rawName = relativePath.Substring("img/".Length);
                            string candidateImg = Path.Combine(current, "img", rawName);
                            if (File.Exists(candidateImg))
                            {
                                absolutePath = candidateImg;
                                break;
                            }
                        }
                        current = Path.GetDirectoryName(current);
                    }
                }

                if (!File.Exists(absolutePath))
                {
                    HideImageTooltip();
                    return;
                }

                var bitmap = new BitmapImage();
                bitmap.BeginInit();
                bitmap.UriSource = new Uri(absolutePath);
                bitmap.CacheOption = BitmapCacheOption.OnLoad;
                bitmap.EndInit();

                var panel = new StackPanel();

                var tooltipContent = new System.Windows.Controls.Border
                {
                    Background = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(26, 26, 26)),
                    Padding = new Thickness(8),
                    BorderBrush = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(40, 40, 40)),
                    BorderThickness = new Thickness(1),
                    CornerRadius = new CornerRadius(4),
                    Child = panel
                };

                var border = new System.Windows.Controls.Border
                {
                    BorderBrush = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(68, 68, 68)),
                    BorderThickness = new Thickness(1),
                    CornerRadius = new CornerRadius(4),
                    Child = new System.Windows.Controls.Image
                    {
                        Source = bitmap,
                        Width = Math.Min(bitmap.PixelWidth, 200),
                        Height = Math.Min(bitmap.PixelHeight, 200),
                        Stretch = Stretch.Uniform
                    }
                };

                var infoText = new TextBlock
                {
                    Text = $"{Path.GetFileName(relativePath)}\nDimensions: {bitmap.PixelWidth}x{bitmap.PixelHeight} px",
                    Foreground = System.Windows.Media.Brushes.LightGray,
                    FontSize = 10,
                    FontFamily = new System.Windows.Media.FontFamily("Consolas"),
                    HorizontalAlignment = HorizontalAlignment.Center,
                    TextAlignment = TextAlignment.Center,
                    Margin = new Thickness(0, 6, 0, 0)
                };

                panel.Children.Add(border);
                panel.Children.Add(infoText);

                if (_imageTooltip == null)
                {
                    _imageTooltip = new ToolTip
                    {
                        PlacementTarget = ScriptEditor,
                        Placement = System.Windows.Controls.Primitives.PlacementMode.Mouse,
                        BorderThickness = new Thickness(0),
                        Background = System.Windows.Media.Brushes.Transparent,
                        Padding = new Thickness(0)
                    };
                }

                _imageTooltip.Content = tooltipContent;
                _imageTooltip.Tag = relativePath;
                _imageTooltip.IsOpen = true;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error showing image tooltip: {ex.Message}");
                HideImageTooltip();
            }
        }

        private void HideImageTooltip()
        {
            if (_imageTooltip != null && _imageTooltip.IsOpen)
            {
                _imageTooltip.IsOpen = false;
            }
        }
    }

    public class ErrorLineBackgroundRenderer : IBackgroundRenderer
    {
        private readonly TextEditor _editor;
        private int _errorLineNumber = -1;

        public ErrorLineBackgroundRenderer(TextEditor editor)
        {
            _editor = editor;
        }

        public int ErrorLineNumber
        {
            get => _errorLineNumber;
            set
            {
                if (_errorLineNumber != value)
                {
                    _errorLineNumber = value;
                    _editor.TextArea.TextView.InvalidateVisual();
                }
            }
        }

        public KnownLayer Layer => KnownLayer.Background;

        public void Draw(TextView textView, DrawingContext drawingContext)
        {
            if (_errorLineNumber < 1 || _errorLineNumber > textView.Document.LineCount) return;

            textView.EnsureVisualLines();
            var line = textView.Document.GetLineByNumber(_errorLineNumber);
            if (line == null) return;

            var builder = new BackgroundGeometryBuilder();
            builder.AddSegment(textView, line);
            var geometry = builder.CreateGeometry();
            if (geometry != null)
            {
                var brush = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromArgb(45, 255, 0, 0));
                var pen = new System.Windows.Media.Pen(System.Windows.Media.Brushes.Red, 1.5);
                drawingContext.DrawGeometry(brush, pen, geometry);
            }
        }
    }
}
