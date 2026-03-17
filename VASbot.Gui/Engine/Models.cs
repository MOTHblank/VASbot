using System;

namespace VASbot.Gui.Engine
{
    public record WindowInfo(nint Handle, string Title, string ClassName);

    public class RegionModel
    {
        public Guid Id { get; set; } = Guid.NewGuid();
        public string Name { get; set; } = "New Region";
        public int X { get; set; }
        public int Y { get; set; }
        public int Width { get; set; }
        public int Height { get; set; }
        public string Color { get; set; } = "#FF3A3A";
        public string WindowTitle { get; set; } = "";
        public string WindowClass { get; set; } = "";
    }
}
