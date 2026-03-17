using System;
using System.Windows;
using VASbot.Gui.Engine;
using VASbot.Gui.UI.ViewModels;
using System.Windows;
using VASbot.Gui.Engine;
using VASbot.Gui.UI.ViewModels;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;


namespace VASbot.Gui.Engine
{
    public class RegionManager
    {
        private const string RegionsFile = "regions.json";

        public async Task SaveRegionsAsync(IEnumerable<RegionModel> regions)
        {
            try
            {
                var options = new JsonSerializerOptions { WriteIndented = true };
                string json = JsonSerializer.Serialize(regions, options);
                await File.WriteAllTextAsync(RegionsFile, json);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[RegionManager] Save failed: {ex.Message}");
            }
        }

        public async Task<List<RegionModel>> LoadRegionsAsync()
        {
            try
            {
                if (File.Exists(RegionsFile))
                {
                    string json = await File.ReadAllTextAsync(RegionsFile);
                    return JsonSerializer.Deserialize<List<RegionModel>>(json) ?? new List<RegionModel>();
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[RegionManager] Load failed: {ex.Message}");
            }
            return new List<RegionModel>();
        }
    }
}
