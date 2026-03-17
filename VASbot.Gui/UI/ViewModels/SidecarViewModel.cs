using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using System;
using System.Collections.ObjectModel;
using System.Windows;
using System.Threading.Tasks;
using VASbot.Gui.Engine;

namespace VASbot.Gui.UI.ViewModels
{
    public partial class SidecarViewModel : ObservableObject
    {
        private readonly PythonSidecarService _sidecarService;
        private readonly IBotService _botService;

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
                App.Current.Dispatcher.Invoke(() => {
                    LogsText += $"[{DateTime.Now:HH:mm:ss}] {msg}\n";
                });
            };

            _sidecarService.StateChanged += (running) => {
                IsRunning = running;
                StatusText = running ? "Active (Port 50051)" : "Stopped";
            };

            IsRunning = _sidecarService.IsRunning;
        }

        [RelayCommand]
        public void RestartSidecar()
        {
            _sidecarService.Stop();
            LogsText += "--- Restarting Sidecar ---\n";
            _sidecarService.Start();
            
            // Re-connect gRPC
            Task.Run(async () => {
                if (await _botService.StartAsync()) {
                    App.Current.Dispatcher.Invoke(() => StatusText = "Reconnected");
                }
            });
        }

        [RelayCommand]
        public void ClearLogs() => LogsText = "";
    }
}
