using System;
using System.Threading;
using System.Threading.Tasks;
using SkiaSharp;
using VASbot.Gui.Engine;

namespace VASbot.Gui.Engine
{
    public class ReflectionService
    {
        private readonly ScreenshotService _screenshotService;
        private CancellationTokenSource? _cts;
        private nint _targetHwnd;
        private int _fps = 20;

        public event Action<SKBitmap>? FrameUpdated;

        public SharedMemoryService? SharedMemory { get; set; }
        public IBotService? BotService { get; set; }
        public bool IsDynamic { get; set; } = true;

        public ReflectionService(ScreenshotService screenshotService)
        {
            _screenshotService = screenshotService;
        }

        public void Start(nint hwnd, int fps = 20)
        {
            Stop();
            _targetHwnd = hwnd;
            _fps = fps;
            _cts = new CancellationTokenSource();
            
            Task.Run(() => CaptureLoop(_cts.Token));
        }

        public void Stop()
        {
            _cts?.Cancel();
            _cts?.Dispose();
            _cts = null;
        }

        public void TriggerStaticCapture()
        {
            if (_targetHwnd == IntPtr.Zero) return;
            var bitmap = _screenshotService.CaptureWindowBitBlt(_targetHwnd);
            if (bitmap != null)
            {
                FrameUpdated?.Invoke(bitmap);
                UpdateSharedMemory(bitmap);
            }
        }

        private void UpdateSharedMemory(SKBitmap bitmap)
        {
            if (SharedMemory != null && BotService != null)
            {
                SharedMemory.WriteFrame(bitmap);
                _ = BotService.NotifyFrameUpdateAsync(
                    SharedMemory.Name, 
                    bitmap.Width, 
                    bitmap.Height, 
                    bitmap.RowBytes
                );
            }
        }

        private async Task CaptureLoop(CancellationToken token)
        {
            int delay = 1000 / _fps;
            SKBitmap? lastBitmap = null;

            while (!token.IsCancellationRequested)
            {
                if (!IsDynamic)
                {
                    await Task.Delay(500, token);
                    continue;
                }

                var startTime = DateTime.Now;
                try
                {
                    var bitmap = _screenshotService.CaptureWindow(_targetHwnd);
                    if (bitmap != null)
                    {
                        FrameUpdated?.Invoke(bitmap);
                        UpdateSharedMemory(bitmap);
                        
                        lastBitmap?.Dispose();
                        lastBitmap = bitmap;
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"[ReflectionService] Capture failed: {ex.Message}");
                }

                var elapsed = (int)(DateTime.Now - startTime).TotalMilliseconds;
                int actualDelay = Math.Max(1, delay - elapsed);
                await Task.Delay(actualDelay, token);
            }
            lastBitmap?.Dispose();
        }
    }
}
