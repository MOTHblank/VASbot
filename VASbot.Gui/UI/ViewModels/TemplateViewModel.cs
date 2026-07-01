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
        public ObservableCollection<TemplateCategoryGroup> GroupedTemplates { get; } = new();

        [ObservableProperty]
        private string? _selectedCategory;

        [ObservableProperty]
        private string _searchQuery = "";

        private ScriptTemplate? _selectedTemplate;
        public ScriptTemplate? SelectedTemplate
        {
            get => _selectedTemplate;
            set
            {
                if (_selectedTemplate == value) return;

                // Guard: Ignore setting to null if it's triggered by WPF listbox selection mismatched items,
                // unless we explicitly allow it (e.g. when we are resetting or filtering).
                if (value == null && !_allowNullSelection)
                {
                    return;
                }

                _selectedTemplate = value;
                OnPropertyChanged(nameof(SelectedTemplate));
                OnSelectedTemplateChanged(value);
            }
        }

        private bool _allowNullSelection = false;

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

        partial void OnSearchQueryChanged(string value) => ApplyFilter();

        private void OnSelectedTemplateChanged(ScriptTemplate? value)
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
            GroupedTemplates.Clear();

            var query = _allTemplates.AsEnumerable();
            if (SelectedCategory != "All" && SelectedCategory != null)
                query = query.Where(t => t.Category == SelectedCategory);

            if (!string.IsNullOrWhiteSpace(SearchQuery))
            {
                var q = SearchQuery.Trim();
                query = query.Where(t =>
                    (t.Name != null && t.Name.Contains(q, System.StringComparison.OrdinalIgnoreCase)) ||
                    (t.Description != null && t.Description.Contains(q, System.StringComparison.OrdinalIgnoreCase)) ||
                    (t.Category != null && t.Category.Contains(q, System.StringComparison.OrdinalIgnoreCase))
                );
            }

            var list = query.ToList();
            foreach (var t in list)
                FilteredTemplates.Add(t);

            // Group by category
            var groups = list.GroupBy(t => t.Category ?? "Helpers")
                             .OrderBy(g => g.Key);

            bool isSearching = !string.IsNullOrWhiteSpace(SearchQuery);

            foreach (var g in groups)
            {
                var categoryName = g.Key;
                var icon = GetCategoryIcon(categoryName);
                var groupObj = new TemplateCategoryGroup(categoryName, icon, g);
                groupObj.IsExpanded = isSearching; // Auto-expand when searching
                GroupedTemplates.Add(groupObj);
            }

            if (SelectedTemplate != null && !FilteredTemplates.Contains(SelectedTemplate))
            {
                _allowNullSelection = true;
                SelectedTemplate = null;
                _allowNullSelection = false;
            }
        }

        private static string GetCategoryIcon(string category)
        {
            return category switch
            {
                "Logic" => "🧠",
                "Time" => "⏱️",
                "Mouse" => "🖱️",
                "Keyboard" => "⌨️",
                "Vision" => "👁️",
                "Vision - Shapes" => "🎨",
                "Vision - Motion" => "🔄",
                "Window" => "🪟",
                "Helpers" => "🛠️",
                "Dynamic Elements" => "⚡",
                "User Snippets" => "📦",
                _ => "📁"
            };
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

    public partial class TemplateCategoryGroup : ObservableObject
    {
        public string Name { get; }
        public string Icon { get; }
        public string HeaderText => $"{Icon}  {Name} ({Templates.Count})";

        public ObservableCollection<ScriptTemplate> Templates { get; }

        [ObservableProperty]
        private bool _isExpanded;

        public TemplateCategoryGroup(string name, string icon, IEnumerable<ScriptTemplate> templates)
        {
            Name = name;
            Icon = icon;
            Templates = new ObservableCollection<ScriptTemplate>(templates);
            _isExpanded = false;
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
