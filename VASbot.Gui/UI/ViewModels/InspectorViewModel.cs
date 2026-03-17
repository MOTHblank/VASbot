using CommunityToolkit.Mvvm.ComponentModel;
using Rect = System.Windows.Rect;

namespace VASbot.Gui.UI.ViewModels
{
    public partial class InspectorViewModel : ObservableObject
    {
        [ObservableProperty]
        private string _elementName = "N/A";

        [ObservableProperty]
        private string _controlType = "N/A";

        [ObservableProperty]
        private string _automationId = "N/A";

        [ObservableProperty]
        private string _className = "N/A";

        [ObservableProperty]
        private string _processId = "N/A";

        [ObservableProperty]
        private string _windowStyle = "N/A";

        [ObservableProperty]
        private System.Windows.Rect _bounds;

        [ObservableProperty]
        private bool _isVisible;

        public void Update(AutomationTreeViewModel.AutomationNode? node)
        {
            if (node == null)
            {
                IsVisible = false;
                return;
            }

            IsVisible = true;
            ElementName = node.Name ?? "Unnamed";
            ControlType = node.Type ?? "Unknown";
            AutomationId = node.AutomationId ?? "None";
            Bounds = node.BoundingRect;
            
            try
            {
                ClassName = node.Element.Current.ClassName;
                ProcessId = node.Element.Current.ProcessId.ToString();
                
                var hwnd = (nint)node.Element.Current.NativeWindowHandle;
                if (hwnd != nint.Zero)
                {
                    int style = Engine.ScreenshotService.GetWindowLong(hwnd, Engine.ScreenshotService.GWL_STYLE);
                    WindowStyle = $"0x{style:X8}";
                }
            }
            catch { }
        }
    }
}
