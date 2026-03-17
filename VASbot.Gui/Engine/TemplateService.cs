using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Linq;

namespace VASbot.Gui.Engine
{
    public record TemplateParameter(string Key, string Type, string DefaultValue = "");

    public record ScriptTemplate(
        string Name, 
        string Icon,
        string Category, 
        string Description,
        string Template, 
        List<TemplateParameter> Parameters, 
        bool RequiresRegion, 
        string InsertMode);

    public class TemplateService
    {
        public List<ScriptTemplate> LoadTemplates()
        {
            try
            {
                string path = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "templates.json");
                if (File.Exists(path))
                {
                    string json = File.ReadAllText(path);
                    return JsonSerializer.Deserialize<List<ScriptTemplate>>(json) ?? new List<ScriptTemplate>();
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[TemplateError] {ex.Message}");
            }

            return new List<ScriptTemplate>();
        }

        public void SaveTemplate(ScriptTemplate template)
        {
            try
            {
                string path = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "templates.json");
                var templates = LoadTemplates();
                templates.Add(template);
                var options = new JsonSerializerOptions { WriteIndented = true };
                string json = JsonSerializer.Serialize(templates, options);
                File.WriteAllText(path, json);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[TemplateError] Save failed: {ex.Message}");
            }
        }

        public string ApplyTemplate(ScriptTemplate template, Dictionary<string, string> values, string selectedText = "")
        {
            string result = template.Template;
            foreach (var kvp in values)
            {
                string finalValue = kvp.Value;

                // Handle formatted region strings: "[0] Name" -> "0"
                if (kvp.Key == "region_index" && finalValue.StartsWith("[") && finalValue.Contains("]"))
                {
                    int end = finalValue.IndexOf("]");
                    if (end > 1)
                    {
                        finalValue = finalValue.Substring(1, end - 1);
                    }
                }

                result = result.Replace("{" + kvp.Key + "}", finalValue);
            }
            
            if (template.InsertMode == "wrap")
            {
                string indented = string.Join("\n    ", selectedText.Split('\n'));
                result = result.Replace("{selection}", "    " + indented);
            }

            return result;
        }
    }
}
