using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using System;
using System.Collections.ObjectModel;
using System.Threading.Tasks;
using System.Windows.Automation;
using VASbot.Gui.Engine;

namespace VASbot.Gui.UI.ViewModels
{
    public partial class AutomationTreeViewModel : ObservableObject
    {
        private readonly UIAutomationService _uiaService;
        private readonly IBotService _botService;

        public record AutomationNode(string Name, string Type, string AutomationId, System.Windows.Rect BoundingRect, AutomationElement Element)
        {
            public ObservableCollection<AutomationNode> Children { get; } = new();
        }

        [ObservableProperty]
        private AutomationNode? _selectedNode;

        public ObservableCollection<AutomationNode> RootNodes { get; } = new();

        public AutomationTreeViewModel(UIAutomationService uiaService, IBotService botService)
        {
            _uiaService = uiaService;
            _botService = botService;
        }

        [RelayCommand]
        public async Task ClickNodeAsync(AutomationNode? node)
        {
            var target = node ?? SelectedNode;
            if (target == null) return;

            // Use AutomationId if available, else Name
            string identifier = !string.IsNullOrEmpty(target.AutomationId) ? target.AutomationId : target.Name;
            
            if (string.IsNullOrEmpty(identifier)) return;

            await _botService.ClickElementAsync(identifier, target.Type);
        }

        public void LoadTree(nint hwnd)
        {
            RootNodes.Clear();
            if (hwnd == nint.Zero) return;

            try
            {
                var root = AutomationElement.FromHandle(hwnd);
                if (root == null) return;

                var rootNode = new AutomationNode(root.Current.Name, root.Current.LocalizedControlType, root.Current.AutomationId, root.Current.BoundingRectangle, root);
                WalkTree(root, rootNode, 0);
                RootNodes.Add(rootNode);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[AutomationTree Error] {ex.Message}");
            }
        }

        private void WalkTree(AutomationElement element, AutomationNode parentNode, int depth)
        {
            if (depth > 5) return;

            try
            {
                var children = element.FindAll(TreeScope.Children, Condition.TrueCondition);
                foreach (AutomationElement child in children)
                {
                    var node = new AutomationNode(child.Current.Name, child.Current.LocalizedControlType, child.Current.AutomationId, child.Current.BoundingRectangle, child);
                    parentNode.Children.Add(node);
                    WalkTree(child, node, depth + 1);
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[AutomationTree Error] {ex.Message}");
            }
        }

        public AutomationNode? FindNodeAt(double x, double y)
        {
            foreach (var root in RootNodes)
            {
                var found = SearchNodes(root, x, y);
                if (found != null) return found;
            }
            return null;
        }

        private AutomationNode? SearchNodes(AutomationNode node, double x, double y)
        {
            // Search children first (more specific)
            foreach (var child in node.Children)
            {
                var found = SearchNodes(child, x, y);
                if (found != null) return found;
            }

            if (node.BoundingRect.Contains(x, y))
                return node;

            return null;
        }
    }
}
