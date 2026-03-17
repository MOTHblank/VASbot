using CommunityToolkit.Mvvm.ComponentModel;
using System.Drawing;

namespace VASbot.Gui.UI.ViewModels
{
    public partial class RegionViewModel : ObservableObject
    {
        [ObservableProperty]
        private string _id = string.Empty;

        [ObservableProperty]
        private string _name = "New Region";

        [ObservableProperty]
        private Rectangle _rect;

        [ObservableProperty]
        private string _color = "#FF3A3A";

        [ObservableProperty]
        private string _windowTitle = string.Empty;

        [ObservableProperty]
        private string _windowClass = string.Empty;

        public bool IsValidForWindow(string currentTitle, string currentClass)
        {
            return WindowTitle == currentTitle && WindowClass == currentClass;
        }
    }
}
