using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using SkiaSharp;
using VASbot.Gui.Engine;

namespace VASbot.Gui.Engine
{
    public interface IBotService
    {
        bool IsRunning { get; }
        
        Task<bool> StartAsync();
        Task StopAsync();
        
        // Executes a script and streams logs back via the onLog action
        Task ExecuteScriptAsync(string scriptCode, Action<string> onLog);
        
        Task<bool> NotifyFrameUpdateAsync(string mapName, int width, int height, int stride);
        
        // Sync methods
        Task<bool> UpdateRegionsAsync(IEnumerable<RegionModel> regions);
        Task<bool> SetTargetWindowAsync(nint hwnd, string title);

        // Recorder
        Task<bool> StartRecordingAsync();
        Task<string?> StopRecordingAsync();

        // Window management
        Task<List<WindowInfo>> ListWindowsAsync();
        Task<SKBitmap?> CaptureWindowAsync(WindowInfo window);

        // Advanced Window Automation
        Task<bool> ClickElementAsync(string identifier, string controlType = "Button", bool doubleClick = false);
        Task<bool> TypeIntoElementAsync(string identifier, string text, bool clearFirst = true);
        Task<bool> WaitWindowAsync(string title, float timeout = 10);
        
        // Script control
        Task StopScriptAsync();
    }
}
