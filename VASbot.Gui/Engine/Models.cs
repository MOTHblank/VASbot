using System;
using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;

namespace VASbot.Gui.Engine
{
    public record WindowInfo(nint Handle, string Title, string ClassName);

    public partial class RegionModel : ObservableObject
    {
        public Guid Id { get; set; } = Guid.NewGuid();
        
        [ObservableProperty]
        private string _name = "New Region";
        
        [ObservableProperty]
        private int _x;
        
        [ObservableProperty]
        private int _y;
        
        [ObservableProperty]
        private int _width;
        
        [ObservableProperty]
        private int _height;
        
        [ObservableProperty]
        private string _color = "#FF3A3A";
        
        public string WindowTitle { get; set; } = "";
        public string WindowClass { get; set; } = "";
    }

    public partial class ColorClusterModel : ObservableObject
    {
        public Guid Id { get; set; } = Guid.NewGuid();

        [ObservableProperty]
        private string _name = "New Cluster";

        [ObservableProperty]
        private int _proximity = 10;

        [ObservableProperty]
        private int _tolerance = 25;

        [ObservableProperty]
        private bool _isActive = true;

        public ObservableCollection<string> Colors { get; set; } = new ObservableCollection<string>();
    }

    public record DetectedShapeResult(string Type, int X, int Y, int Width, int Height, double Confidence);
}
