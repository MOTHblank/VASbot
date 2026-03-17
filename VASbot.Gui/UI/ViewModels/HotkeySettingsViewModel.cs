using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using System.Collections.ObjectModel;
using System.Windows.Input;
using System.Linq;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;
using System;
using System.Windows;
using VASbot.Gui.Engine;

namespace VASbot.Gui.UI.ViewModels
{
    public partial class HotkeySettingsViewModel : ObservableObject
    {
        private const string HotkeysFile = "hotkeys_config.json";

        public partial class HotkeyConfig : ObservableObject
        {
            public string ActionName { get; init; } = "";
            
            [ObservableProperty]
            private ModifierKeys _modifiers;

            [ObservableProperty]
            private Key _key;

            [ObservableProperty]
            private bool _isConflict;

            public HotkeyConfig() { }
            public HotkeyConfig(string name, ModifierKeys mod, Key k) 
            { 
                ActionName = name; 
                Modifiers = mod; 
                Key = k; 
            }
        }

        public ObservableCollection<HotkeyConfig> Hotkeys { get; } = new();

        public HotkeySettingsViewModel()
        {
            LoadSettings();
        }

        public async void LoadSettings()
        {
            try
            {
                if (File.Exists(HotkeysFile))
                {
                    string json = File.ReadAllText(HotkeysFile);
                    var loaded = JsonSerializer.Deserialize<List<HotkeyConfig>>(json);
                    if (loaded != null)
                    {
                        Hotkeys.Clear();
                        foreach (var h in loaded) Hotkeys.Add(h);
                        return;
                    }
                }
            }
            catch { }

            // Defaults if load fails
            ResetToDefaults();
        }

        [RelayCommand]
        public async Task SaveSettingsAsync()
        {
            try
            {
                string json = JsonSerializer.Serialize(Hotkeys.ToList(), new JsonSerializerOptions { WriteIndented = true });
                await File.WriteAllTextAsync(HotkeysFile, json);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[HotkeySettings] Save failed: {ex.Message}");
            }
        }

        [RelayCommand]
        public void ResetToDefaults()
        {
            Hotkeys.Clear();
            Hotkeys.Add(new HotkeyConfig("Run Script", ModifierKeys.Control, Key.F5));
            Hotkeys.Add(new HotkeyConfig("Stop Script", ModifierKeys.Control, Key.F7));
            Hotkeys.Add(new HotkeyConfig("Capture Window", ModifierKeys.Control, Key.F6));
        }
    }
}
