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
        private MainViewModel? _mainViewModel;

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

        // Event to notify when script text is updated externally (e.g., file load)
        public event Action? ScriptTextUpdated;

        public ObservableCollection<string> Logs { get; } = new();

        public ScriptEditorViewModel(IBotService botService)
        {
            _botService = botService;
        }

        public void SetMainViewModel(MainViewModel mainVm)
        {
            _mainViewModel = mainVm;
        }

        public void ExtractAndSyncRegions()
        {
            if (_mainViewModel == null) 
            {
                AddLog("ERROR: _mainViewModel is null - cannot sync regions");
                return;
            }
            
            try
            {
                // Look for bot.gui.regions = [...] in the script
                var match = System.Text.RegularExpressions.Regex.Match(
                    ScriptText, 
                    @"bot\.gui\.regions\s*=\s*(\[.*?\])",
                    System.Text.RegularExpressions.RegexOptions.Singleline
                );
                
                if (!match.Success)
                {
                    AddLog("No embedded regions found in script.");
                    return;
                }
                
                var regionsContent = match.Groups[1].Value;
                AddLog($"Found regions content: {regionsContent.Substring(0, Math.Min(50, regionsContent.Length))}...");
                
                // Clear existing regions in BOTH collections
                _mainViewModel.Regions.Clear();
                _mainViewModel.Capture.Regions.Clear();
                
                // Parse each region entry
                var regionMatches = System.Text.RegularExpressions.Regex.Matches(
                    regionsContent,
                    @"\{'x':\s*(\d+),\s*'y':\s*(\d+),\s*'width':\s*(\d+),\s*'height':\s*(\d+),\s*'color':\s*'([^']+)'\}"
                );
                
                int index = 0;
                foreach (System.Text.RegularExpressions.Match rMatch in regionMatches)
                {
                    int x = int.Parse(rMatch.Groups[1].Value);
                    int y = int.Parse(rMatch.Groups[2].Value);
                    int w = int.Parse(rMatch.Groups[3].Value);
                    int h = int.Parse(rMatch.Groups[4].Value);
                    string color = rMatch.Groups[5].Value;
                    
                    // Create RegionModel for Capture (UI display)
                    var regionModel = new RegionModel
                    {
                        Id = Guid.NewGuid(),
                        Name = $"Region {index}",
                        X = x,
                        Y = y,
                        Width = w,
                        Height = h,
                        Color = color
                    };
                    
                    // Also create RegionViewModel for MainViewModel
                    var regionViewModel = new RegionViewModel
                    {
                        Id = Guid.NewGuid().ToString(),
                        Name = $"Region {index}",
                        Rect = new System.Drawing.Rectangle(x, y, w, h),
                        Color = color
                    };
                    
                    // Add to BOTH collections
                    _mainViewModel.Capture.Regions.Add(regionModel);
                    _mainViewModel.Regions.Add(regionViewModel);
                    
                    AddLog($"Added region {index}: x={x}, y={y}, color={color}");
                    index++;
                }
                
                AddLog($"Total regions loaded: {index}");
            }
            catch (Exception ex)
            {
                AddLog($"ERROR extracting regions: {ex.GetType().Name}: {ex.Message}");
                AddLog($"Stack: {ex.StackTrace}");
            }
        }

        partial void OnScriptTextChanged(string value)
        {
            // Notify subscribers (like MainWindow) that the script text changed
            ScriptTextUpdated?.Invoke();
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
                
                // Extract and sync embedded regions to GUI
                ExtractAndSyncRegions();
            }
        }

        [RelayCommand]
        public void SaveScript()
        {
            if (string.IsNullOrEmpty(CurrentFilePath))
            {
                SaveScriptAs();
                return;
            }

            string contentToSave = GenerateScriptWithRegions();
            File.WriteAllText(CurrentFilePath, contentToSave);
            AddLog($"Saved: {Path.GetFileName(CurrentFilePath)}");
        }

        [RelayCommand]
        public void SaveScriptAs()
        {
            var dialog = new Microsoft.Win32.SaveFileDialog
            {
                Filter = "Python Scripts (*.py)|*.py",
                DefaultExt = ".py",
                Title = "Save VASbot Script As"
            };
            
            // Pre-fill with current filename if available
            if (!string.IsNullOrEmpty(CurrentFilePath))
            {
                dialog.FileName = Path.GetFileName(CurrentFilePath);
            }
            
            if (dialog.ShowDialog() == true)
            {
                CurrentFilePath = dialog.FileName;
                string contentToSave = GenerateScriptWithRegions();
                File.WriteAllText(CurrentFilePath, contentToSave);
                AddLog($"Saved as: {Path.GetFileName(CurrentFilePath)}");
            }
        }

        private string GenerateScriptWithRegions()
        {
            // Get current regions from Capture (which is what the GUI actually edits!)
            if (_mainViewModel == null || _mainViewModel.Capture.Regions.Count == 0)
            {
                return ScriptText;
            }

            // Generate embedded regions code
            var regionsCode = new System.Text.StringBuilder();
            regionsCode.AppendLine();
            regionsCode.AppendLine("# ============ EMBEDDED REGIONS ============");
            regionsCode.AppendLine("# Auto-generated region definitions");
            regionsCode.AppendLine($"# Created: {DateTime.Now:yyyy-MM-dd HH:mm:ss}");
            
            // Get current window info if available
            if (_mainViewModel.Capture?.SelectedWindow != null)
            {
                regionsCode.AppendLine($"# Window: {_mainViewModel.Capture.SelectedWindow.Title}");
            }
            
            regionsCode.AppendLine();
            regionsCode.AppendLine("bot.gui.regions = [");
            
            for (int i = 0; i < (_mainViewModel?.Capture?.Regions?.Count ?? 0); i++)
            {
                var r = _mainViewModel!.Capture!.Regions![i]!;
                string line = $"    {{'x': {r.X}, 'y': {r.Y}, 'width': {r.Width}, 'height': {r.Height}, 'color': '{r.Color}'}}";
                if (i < _mainViewModel.Capture.Regions.Count - 1)
                    line += ",";
                regionsCode.AppendLine(line);
            }
            
            regionsCode.AppendLine("]");
            regionsCode.AppendLine("bot.gui.update_region_selector()");
            regionsCode.AppendLine("bot.log('Loaded embedded regions')");
            regionsCode.AppendLine("# ============ END EMBEDDED REGIONS ============");
            
            string regionsBlock = regionsCode.ToString();
            
            // Check if script already has embedded regions - if so, replace them
            if (ScriptText.Contains("bot.gui.regions = ["))
            {
                // Remove old embedded regions block and append new one
                int startIdx = ScriptText.IndexOf("# ============ EMBEDDED REGIONS");
                int endIdx = ScriptText.IndexOf("# ============ END EMBEDDED REGIONS");
                
                if (startIdx >= 0 && endIdx >= 0)
                {
                    // Remove old block
                    string before = ScriptText.Substring(0, startIdx).TrimEnd();
                    string after = ScriptText.Substring(endIdx + "# ============ END EMBEDDED REGIONS".Length);
                    return before + regionsBlock + after;
                }
            }
            
            // Append regions to end of script
            return ScriptText + "\n" + regionsBlock;
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
            // First try to stop via gRPC (tells Python to set is_running = False)
            await _botService.StopScriptAsync();
            
            // Also dispose the stream
            await _botService.StopAsync();
            
            AddLog("Stop command sent to Sidecar.");
        }
    }
}
