using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using System;
using System.Collections.Concurrent;
using System.Collections.ObjectModel;
using System.Text;
using System.Windows;
using System.Windows.Threading;
using System.Threading.Tasks;
using VASbot.Gui.Engine;

namespace VASbot.Gui.UI.ViewModels
{
    public partial class SidecarViewModel : ObservableObject
    {
        private readonly PythonSidecarService _sidecarService;
        private readonly IBotService _botService;
        private readonly ConcurrentQueue<string> _logQueue = new();
        private readonly DispatcherTimer _logTimer;
        private readonly StringBuilder _logBuffer = new();
        private const int MaxLogChars = 100000;

        [ObservableProperty]
        private bool _isRunning;

        [ObservableProperty]
        private string _statusText = "Disconnected";

        [ObservableProperty]
        private string _logsText = "";

        public SidecarViewModel(PythonSidecarService sidecarService, IBotService botService)
        {
            _sidecarService = sidecarService;
            _botService = botService;

            _sidecarService.OutputReceived += (msg) => {
                _logQueue.Enqueue($"[{DateTime.Now:HH:mm:ss}] {msg}");
            };

            _sidecarService.StateChanged += (running) => {
                IsRunning = running;
                StatusText = running ? "Active (Port 50051)" : "Stopped";
            };

            IsRunning = _sidecarService.IsRunning;

            _logTimer = new DispatcherTimer
            {
                Interval = TimeSpan.FromMilliseconds(100)
            };
            _logTimer.Tick += ProcessLogQueue;
            _logTimer.Start();
        }

        private void ProcessLogQueue(object? sender, EventArgs e)
        {
            if (_logQueue.IsEmpty) return;

            bool changed = false;
            while (_logQueue.TryDequeue(out var msg))
            {
                _logBuffer.AppendLine(msg);
                changed = true;
            }

            if (changed)
            {
                if (_logBuffer.Length > MaxLogChars)
                {
                    int toRemove = _logBuffer.Length - MaxLogChars;
                    int nextNewLine = -1;
                    for (int i = toRemove; i < _logBuffer.Length; i++)
                    {
                        if (_logBuffer[i] == '\n')
                        {
                            nextNewLine = i;
                            break;
                        }
                    }
                    if (nextNewLine != -1)
                    {
                        _logBuffer.Remove(0, nextNewLine + 1);
                    }
                    else
                    {
                        _logBuffer.Remove(0, toRemove);
                    }
                }
                LogsText = _logBuffer.ToString();
            }
        }

        [RelayCommand]
        public void RestartSidecar()
        {
            _sidecarService.Stop();
            _logQueue.Enqueue($"[{DateTime.Now:HH:mm:ss}] --- Restarting Sidecar ---");
            _sidecarService.Start();
            
            // Re-connect gRPC
            Task.Run(async () => {
                if (await _botService.StartAsync()) {
                    App.Current.Dispatcher.Invoke(() => StatusText = "Reconnected");
                }
            });
        }

        [RelayCommand]
        public void ClearLogs()
        {
            _logQueue.Clear();
            _logBuffer.Clear();
            LogsText = "";
        }
    }
}
