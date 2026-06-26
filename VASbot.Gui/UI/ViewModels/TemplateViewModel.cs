using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using System.Collections.ObjectModel;
using System.Collections.Generic;
using System.Linq;
using VASbot.Gui.Engine;

namespace VASbot.Gui.UI.ViewModels
{
    public partial class TemplateViewModel : ObservableObject
    {
        private readonly TemplateService _templateService;
        private List<ScriptTemplate> _allTemplates = new();

        public ObservableCollection<ScriptTemplate> FilteredTemplates { get; } = new();
        public ObservableCollection<string> Categories { get; } = new();

        [ObservableProperty]
        private string? _selectedCategory;

        [ObservableProperty]
        private ScriptTemplate? _selectedTemplate;

        [ObservableProperty]
        private string _codePreview = "";

        // Smart parameter options
        public ObservableCollection<string> AvailableRegions { get; } = new();

        // Current parameter values being filled by user
        public ObservableCollection<TemplateParam> CurrentParams { get; } = new();

        public event System.Action<string>? TemplateApplied;

        public TemplateViewModel(TemplateService templateService)
        {
            _templateService = templateService;
            LoadTemplates();
        }

        public void LoadTemplates()
        {
            _allTemplates = _templateService.LoadTemplates();
            
            Categories.Clear();
            Categories.Add("All");
            foreach (var cat in _allTemplates.Select(t => t.Category).Distinct())
                Categories.Add(cat);
            
            SelectedCategory = "All";
            ApplyFilter();
        }

        partial void OnSelectedCategoryChanged(string? value) => ApplyFilter();

        partial void OnSelectedTemplateChanged(ScriptTemplate? value)
        {
            CurrentParams.Clear();
            if (value != null)
            {
                foreach (var p in value.Parameters)
                {
                    var param = new TemplateParam(p.Key, p.Type, p.DefaultValue);
                    param.PropertyChanged += (s, e) => {
                        if (e.PropertyName == nameof(TemplateParam.Value))
                        {
                            UpdateCodePreview();
                        }
                    };
                    CurrentParams.Add(param);
                }
            }
            UpdateCodePreview();
        }

        public void UpdateCodePreview()
        {
            if (SelectedTemplate == null)
            {
                CodePreview = "";
                return;
            }

            var values = CurrentParams.ToDictionary(p => p.Key, p => p.Value);
            CodePreview = _templateService.ApplyTemplate(SelectedTemplate, values, "[Selected Code]");
        }

        private void ApplyFilter()
        {
            FilteredTemplates.Clear();
            var query = _allTemplates.AsEnumerable();
            if (SelectedCategory != "All")
                query = query.Where(t => t.Category == SelectedCategory);
            
            foreach (var t in query)
                FilteredTemplates.Add(t);
        }

        [RelayCommand]
        public void ApplyTemplate(string selectedText)
        {
            if (SelectedTemplate == null) return;

            var values = CurrentParams.ToDictionary(p => p.Key, p => p.Value);
            string code = _templateService.ApplyTemplate(SelectedTemplate, values, selectedText);
            TemplateApplied?.Invoke(code);
        }

        [RelayCommand]
        public void PickColor(TemplateParam param)
        {
            var dialog = new System.Windows.Forms.ColorDialog();
            if (dialog.ShowDialog() == System.Windows.Forms.DialogResult.OK)
            {
                var color = dialog.Color;
                param.Value = $"#{color.R:X2}{color.G:X2}{color.B:X2}";
            }
        }

        public void SaveSnippet(string name, string code)
        {
            if (string.IsNullOrWhiteSpace(code)) return;

            var newTemplate = new ScriptTemplate(
                Name: name,
                Icon: "📦",
                Category: "User Snippets",
                Description: "Custom user sequence",
                Template: code,
                Parameters: new List<TemplateParameter>(),
                RequiresRegion: false,
                InsertMode: "append"
            );

            _templateService.SaveTemplate(newTemplate);
            LoadTemplates();
            SelectedCategory = "User Snippets";
        }
    }

    public partial class TemplateParam : ObservableObject
    {
        public string Key { get; }
        public string Type { get; }
        
        [ObservableProperty]
        private string _value = "";

        public TemplateParam(string key, string type, string defaultValue = "") 
        { 
            Key = key; 
            Type = type; 
            Value = defaultValue;
        }
    }
}
