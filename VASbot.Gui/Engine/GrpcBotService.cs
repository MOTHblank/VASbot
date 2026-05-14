using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using Grpc.Core;
using Grpc.Net.Client;
using SkiaSharp;
using VASbot.Gui.Protos;

namespace VASbot.Gui.Engine
{
    public class GrpcBotService : IBotService, IDisposable
    {
        private readonly GrpcChannel _channel;
        private readonly BotService.BotServiceClient _client;
        private readonly ScreenshotService _screenshotService;
        private AsyncServerStreamingCall<ScriptLog>? _currentScriptStream;
        
        public bool IsRunning { get; private set; }

        public GrpcBotService(string address, ScreenshotService screenshotService)
        {
            _channel = GrpcChannel.ForAddress(address);
            _client = new BotService.BotServiceClient(_channel);
            _screenshotService = screenshotService;
        }

        public async Task<bool> StartAsync()
        {
            int retries = 10;
            while (retries > 0)
            {
                try
                {
                    var response = await _client.CheckHealthAsync(new HealthRequest(), deadline: DateTime.UtcNow.AddSeconds(1));
                    if (response.Status == HealthResponse.Types.ServingStatus.Serving)
                    {
                        IsRunning = true;
                        return true;
                    }
                }
                catch
                {
                    retries--;
                    if (retries > 0) await Task.Delay(1000);
                }
            }
            return false;
        }

        public async Task StopAsync()
        {
            IsRunning = false;
            if (_currentScriptStream != null)
            {
                _currentScriptStream.Dispose();
                _currentScriptStream = null;
            }
            await Task.CompletedTask;
        }

        public async Task ExecuteScriptAsync(string scriptCode, Action<string> onLog)
        {
            string correlationId = Guid.NewGuid().ToString().Substring(0, 8);
            try
            {
                _currentScriptStream = _client.ExecuteScript(new ScriptRequest { 
                    Code = scriptCode, 
                    CorrelationId = correlationId 
                });
                
                await foreach (var log in _currentScriptStream.ResponseStream.ReadAllAsync())
                {
                    onLog?.Invoke(log.Message);
                }
            }
            catch (Exception ex)
            {
                onLog?.Invoke($"[System] gRPC Error ({correlationId}): {ex.Message}");
            }
            finally
            {
                _currentScriptStream?.Dispose();
                _currentScriptStream = null;
            }
        }

        private CallOptions WithDeadline(int seconds = 2) => new CallOptions(deadline: DateTime.UtcNow.AddSeconds(seconds));

        public async Task<bool> NotifyFrameUpdateAsync(string mapName, int width, int height, int stride)
        {
            try
            {
                var response = await _client.NotifyFrameUpdateAsync(new FrameNotification
                {
                    MemoryMapName = mapName,
                    Width = width,
                    Height = height,
                    Stride = stride
                }, WithDeadline(1));
                return response.Acknowledged;
            }
            catch { return false; }
        }

        public async Task<bool> UpdateRegionsAsync(IEnumerable<RegionModel> regions)
        {
            try
            {
                var list = new RegionList();
                list.RefWidth = _screenshotService.LastWidth; 
                list.RefHeight = _screenshotService.LastHeight;

                int index = 0;
                foreach (var r in regions)
                {
                    list.Regions.Add(new VASbot.Gui.Protos.Region {
                        Name = r.Name, X = r.X, Y = r.Y, Width = r.Width, Height = r.Height, Index = index++
                    });
                }                var response = await _client.UpdateRegionsAsync(list, WithDeadline());
                return response.Success;
            }
            catch { return false; }
        }

        public async Task<bool> SetTargetWindowAsync(nint hwnd, string title)
        {
            try
            {
                var response = await _client.SetTargetWindowAsync(new WindowContext { 
                    Hwnd = (ulong)hwnd, Title = title 
                }, WithDeadline());
                return response.Success;
            }
            catch { return false; }
        }

        public async Task<bool> StartRecordingAsync()
        {
            try
            {
                var response = await _client.StartRecordingAsync(new Empty(), WithDeadline());
                return response.Success;
            }
            catch { return false; }
        }

        public async Task<string?> StopRecordingAsync()
        {
            try
            {
                var response = await _client.StopRecordingAsync(new Empty(), WithDeadline());
                return response.Success ? response.Script : null;
            }
            catch { return null; }
        }

        public async Task<List<WindowInfo>> ListWindowsAsync()
        {
            // This remains local PInvoke for speed and direct access
            return await Task.Run(() =>
            {
                var windows = new List<WindowInfo>();
                EnumWindows((hwnd, lParam) =>
                {
                    if (IsWindowVisible(hwnd))
                    {
                        var titleBuilder = new System.Text.StringBuilder(256);
                        GetWindowText(hwnd, titleBuilder, 256);
                        string title = titleBuilder.ToString();

                        if (!string.IsNullOrEmpty(title) && title != "Program Manager")
                        {
                            var classBuilder = new System.Text.StringBuilder(256);
                            GetClassName(hwnd, classBuilder, 256);
                            windows.Add(new WindowInfo(hwnd, title, classBuilder.ToString()));
                        }
                    }
                    return true;
                }, IntPtr.Zero);
                return windows.OrderBy(w => w.Title).ToList();
            });
        }

        [DllImport("user32.dll")] private static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
        private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
        [DllImport("user32.dll", CharSet = CharSet.Auto)] private static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder lpString, int nMaxCount);
        [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr hWnd);
        [DllImport("user32.dll", CharSet = CharSet.Auto)] private static extern int GetClassName(IntPtr hWnd, System.Text.StringBuilder lpClassName, int nMaxCount);

        public async Task<SKBitmap?> CaptureWindowAsync(WindowInfo window)
        {
            return await Task.Run(() => _screenshotService.CaptureWindow(window.Handle));
        }

        public async Task<bool> ClickElementAsync(string identifier, string controlType = "Button", bool doubleClick = false)
        {
            try
            {
                var response = await _client.ClickElementAsync(new ElementRequest
                {
                    Identifier = identifier,
                    ControlType = controlType,
                    DoubleClick = doubleClick
                }, WithDeadline());
                return response.Success;
            }
            catch { return false; }
        }

        public async Task<bool> TypeIntoElementAsync(string identifier, string text, bool clearFirst = true)
        {
            try
            {
                var response = await _client.TypeIntoElementAsync(new TypeRequest
                {
                    Identifier = identifier,
                    Text = text,
                    ClearFirst = clearFirst
                }, WithDeadline());
                return response.Success;
            }
            catch { return false; }
        }

        public async Task<bool> WaitWindowAsync(string title, float timeout = 10)
        {
            try
            {
                var response = await _client.WaitWindowAsync(new WindowRequest
                {
                    Title = title,
                    Timeout = timeout
                }, WithDeadline());
                return response.Success;
            }
            catch { return false; }
        }

        public async Task StopScriptAsync()
        {
            try
            {
                await _client.StopScriptAsync(new StopRequest(), WithDeadline(5));
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[gRPC] StopScript error: {ex.Message}");
            }
        }

        public void Dispose()
        {
            _channel.Dispose();
        }
    }
}
