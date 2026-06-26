using CommunityToolkit.Mvvm.ComponentModel;
using System.Collections.ObjectModel;
using VASbot.Gui.Engine;

namespace VASbot.Gui.UI.ViewModels
{
    public partial class MainViewModel : ObservableObject
    {
        private readonly IBotService _botService;

        [ObservableProperty]
        private string _status = "Ready";

        public ScriptEditorViewModel ScriptEditor { get; }
        public CaptureViewModel Capture { get; }
        public AutomationTreeViewModel AutomationTree { get; }
        public TemplateViewModel Templates { get; }
        public HotkeySettingsViewModel HotkeySettings { get; }
        public InspectorViewModel Inspector { get; }
        public SidecarViewModel Sidecar { get; }
        public VisualEditorViewModel VisualEditor { get; }
        public ObservableCollection<RegionViewModel> Regions { get; } = new();

        public MainViewModel(
            IBotService botService,
            ScriptEditorViewModel scriptEditor,
            CaptureViewModel capture,
            AutomationTreeViewModel automationTree,
            TemplateViewModel templates,
            HotkeySettingsViewModel hotkeySettings,
            InspectorViewModel inspector,
            SidecarViewModel sidecar,
            VisualEditorViewModel visualEditor)
        {
            _botService = botService;
            ScriptEditor = scriptEditor;
            Capture = capture;
            AutomationTree = automationTree;
            Templates = templates;
            HotkeySettings = hotkeySettings;
            Inspector = inspector;
            Sidecar = sidecar;
            VisualEditor = visualEditor;

            // Link ScriptEditor to MainViewModel for region access during save
            ScriptEditor.SetMainViewModel(this);

            // Global Eyedropper Sync: Push picked color to active template
            Capture.PropertyChanged += (s, e) => {
                if (e.PropertyName == nameof(CaptureViewModel.PickedColor))
                {
                    var colorParam = Templates.CurrentParams.FirstOrDefault(p => p.Key.ToLower().Contains("color"));
                    if (colorParam != null)
                    {
                        colorParam.Value = Capture.PickedColor;
                    }
                }
            };
            
            // Link status from capture for display
            Capture.PropertyChanged += (s, e) => {
                if (e.PropertyName == nameof(CaptureViewModel.Status))
                    Status = Capture.Status;
                
                if (e.PropertyName == nameof(CaptureViewModel.SelectedWindow))
                {
                    if (Capture.SelectedWindow != null)
                        AutomationTree.LoadTree(Capture.SelectedWindow.Handle);
                }
            };

            AutomationTree.PropertyChanged += (s, e) => {
                if (e.PropertyName == nameof(AutomationTreeViewModel.SelectedNode))
                {
                    var node = AutomationTree.SelectedNode;
                    if (node != null)
                    {
                        Capture.HighlightScreenRect(node.BoundingRect);
                        
                        // Auto-fill template parameters if they match
                        var currentTemplate = Templates.SelectedTemplate;
                        if (currentTemplate != null && currentTemplate.Category == "Window")
                        {
                            var nameParam = Templates.CurrentParams.FirstOrDefault(p => p.Key.ToLower() == "name");
                            if (nameParam != null) 
                            {
                                nameParam.Value = !string.IsNullOrEmpty(node.AutomationId) ? node.AutomationId : node.Name;
                            }

                            var typeParam = Templates.CurrentParams.FirstOrDefault(p => p.Key.ToLower() == "type");
                            if (typeParam != null) typeParam.Value = node.Type;
                        }
                    }
                    else
                    {
                        Capture.HighlightedRect = null;
                    }
                }
            };

            // Link regions for smart parameter selection
            Capture.Regions.CollectionChanged += (s, e) => {
                Templates.AvailableRegions.Clear();
                for (int i = 0; i < Capture.Regions.Count; i++)
                {
                    var r = Capture.Regions[i];
                    Templates.AvailableRegions.Add($"[{i}] {r.Name}");
                }
            };

            // Link region selection on canvas to template parameter region_index
            Capture.PropertyChanged += (s, e) => {
                if (e.PropertyName == nameof(CaptureViewModel.SelectedRegion))
                {
                    if (Capture.SelectedRegion != null)
                    {
                        int idx = Capture.Regions.IndexOf(Capture.SelectedRegion);
                        if (idx >= 0)
                        {
                            var regionParam = Templates.CurrentParams.FirstOrDefault(p => p.Key == "region_index");
                            if (regionParam != null)
                            {
                                regionParam.Value = $"[{idx}] {Capture.SelectedRegion.Name}";
                            }
                        }
                    }
                }
            };

            // Enhanced Smart Auto-fill: Pull color from region when parameter changes (with robust CollectionChanged listener)
            Templates.CurrentParams.CollectionChanged += (s, e) => {
                var regionParam = Templates.CurrentParams.FirstOrDefault(p => p.Key == "region_index");
                if (regionParam != null)
                {
                    regionParam.PropertyChanged -= RegionParam_PropertyChanged;
                    regionParam.PropertyChanged += RegionParam_PropertyChanged;
                    TriggerColorPull(regionParam);
                }
            };
        }

        private void RegionParam_PropertyChanged(object? sender, System.ComponentModel.PropertyChangedEventArgs e)
        {
            if (e.PropertyName == nameof(TemplateParam.Value) && sender is TemplateParam regionParam)
            {
                TriggerColorPull(regionParam);
            }
        }

        private void TriggerColorPull(TemplateParam regionParam)
        {
            var val = regionParam.Value;
            if (val != null && val.StartsWith("[") && val.Contains("]"))
            {
                try
                {
                    int idx = int.Parse(val.Substring(1, val.IndexOf("]") - 1));
                    if (idx >= 0 && idx < Capture.Regions.Count)
                    {
                        var region = Capture.Regions[idx];
                        var colorParam = Templates.CurrentParams.FirstOrDefault(p => p.Key == "hex_color" || p.Key == "color");
                        if (colorParam != null) colorParam.Value = region.Color;
                    }
                }
                catch { }
            }
        }
    }
}
