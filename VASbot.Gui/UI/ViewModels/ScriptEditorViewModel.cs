using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using System.Collections.ObjectModel;
using System.Threading.Tasks;
using System;
using System.Windows;
using System.IO;
using System.Linq;
using VASbot.Gui.Engine;

namespace VASbot.Gui.UI.ViewModels
{
    public partial class ScriptEditorViewModel : ObservableObject
    {
        private readonly IBotService _botService;

        [ObservableProperty]
        private string _scriptText = "# VASbot Python Script\nbot.log('WPF script system online.')";

        [ObservableProperty]
        private bool _isRunning;

        [ObservableProperty]
        private bool _isRecording;

        [ObservableProperty]
        private string? _currentFilePath;

        [ObservableProperty]
        private string _logsText = "";

        public ObservableCollection<string> Logs { get; } = new();

        public ScriptEditorViewModel(IBotService botService)
        {
            _botService = botService;
        }

        public void AddLog(string message)
        {
            string formatted = $"[{DateTime.Now:HH:mm:ss}] {message}";
            Logs.Add(formatted);
            LogsText += formatted + "\n";
        }

        [RelayCommand]
        public async Task ToggleRecordingAsync()
        {
            if (!IsRecording)
            {
                if (await _botService.StartRecordingAsync())
                {
                    IsRecording = true;
                    AddLog("[Recorder] Started recording mouse/keyboard...");
                }
            }
            else
            {
                var script = await _botService.StopRecordingAsync();
                IsRecording = false;
                if (!string.IsNullOrEmpty(script))
                {
                    ScriptText += "\n\n# --- RECORDED ACTIONS ---\n" + script;
                    AddLog("[Recorder] Finished. Script appended to editor.");
                }
            }
        }

        [RelayCommand]
        public void NewScript()
        {
            ScriptText = "# New VASbot Script\nbot.log('Ready.')";
            CurrentFilePath = null;
        }

        [RelayCommand]
        public void OpenScript()
        {
            var dialog = new Microsoft.Win32.OpenFileDialog
            {
                Filter = "Python Scripts (*.py)|*.py|All files (*.*)|*.*",
                Title = "Open VASbot Script"
            };

            if (dialog.ShowDialog() == true)
            {
                ScriptText = File.ReadAllText(dialog.FileName);
                CurrentFilePath = dialog.FileName;
                AddLog($"Loaded: {Path.GetFileName(dialog.FileName)}");
            }
        }

        [RelayCommand]
        public void SaveScript()
        {
            if (string.IsNullOrEmpty(CurrentFilePath))
            {
                var dialog = new Microsoft.Win32.SaveFileDialog
                {
                    Filter = "Python Scripts (*.py)|*.py",
                    DefaultExt = ".py"
                };
                if (dialog.ShowDialog() == true)
                {
                    CurrentFilePath = dialog.FileName;
                }
                else return;
            }

            File.WriteAllText(CurrentFilePath, ScriptText);
            AddLog($"Saved: {Path.GetFileName(CurrentFilePath)}");
        }

        [RelayCommand]
        public async Task RunScriptAsync()
        {
            if (IsRunning) return;

            IsRunning = true;
            LogsText = ""; // Clear for new run
            AddLog("Executing via Sidecar...");

            try
            {
                // Start streaming execution
                await _botService.ExecuteScriptAsync(ScriptText, (logMessage) => 
                {
                    App.Current.Dispatcher.Invoke(() => AddLog(logMessage));
                });
            }
            catch (Exception ex)
            {
                AddLog($"[Error] {ex.Message}");
            }
            finally
            {
                IsRunning = false;
                AddLog("Execution finished.");
            }
        }

        [RelayCommand]
        public async Task StopScript()
        {
            await _botService.StopAsync();
            AddLog("Stop command sent to Sidecar.");
        }
    }
}
