using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;

namespace VASbot.Gui.Engine
{
    public class ColorClusterManager
    {
        private static readonly string ClustersFile = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "color_clusters.json");

        public async Task SaveClustersAsync(IEnumerable<ColorClusterModel> clusters)
        {
            try
            {
                var options = new JsonSerializerOptions { WriteIndented = true };
                string json = JsonSerializer.Serialize(clusters, options);
                await File.WriteAllTextAsync(ClustersFile, json);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[ColorClusterManager] Save failed: {ex.Message}");
            }
        }

        public async Task<List<ColorClusterModel>> LoadClustersAsync()
        {
            try
            {
                if (File.Exists(ClustersFile))
                {
                    string json = await File.ReadAllTextAsync(ClustersFile);
                    return JsonSerializer.Deserialize<List<ColorClusterModel>>(json) ?? new List<ColorClusterModel>();
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[ColorClusterManager] Load failed: {ex.Message}");
            }
            return new List<ColorClusterModel>();
        }
    }
}
