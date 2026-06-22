using System;
using System.IO;
using System.Windows;
using System.Windows.Input;
using System.Xml;
using ICSharpCode.AvalonEdit.Highlighting;
using ICSharpCode.AvalonEdit.Highlighting.Xshd;
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
                    var imgPos = _viewModel.Capture.ScreenToImage(pos);
                    var screenPos = _viewModel.Capture.ImageToScreen(imgPos);
                    var node = _viewModel.AutomationTree.FindNodeAt(screenPos.X, screenPos.Y);
                    if (node != null)
                    {
                        _viewModel.AutomationTree.SelectedNode = node;
                        _viewModel.Inspector.Update(node);
                        _viewModel.Capture.ActiveElementInfo = new CaptureViewModel.ElementDiagnosticInfo(
                            node.Type, node.AutomationId, node.Element.Current.ClassName, node.Element.Current.ProcessId.ToString()
                        );
                    }
                }
                else
                {
                    _viewModel.Inspector.Update(null);
                    _viewModel.Capture.ActiveElementInfo = null;
                }
            }
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
    }
}
