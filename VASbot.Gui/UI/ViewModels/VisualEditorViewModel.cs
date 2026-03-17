using System;
using System.Collections.ObjectModel;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using VASbot.Gui.Engine;
using VASbot.Gui.UI.ViewModels.VisualGraph;

namespace VASbot.Gui.UI.ViewModels
{
    public partial class VisualEditorViewModel : ObservableObject
    {
        private readonly TemplateService _templateService;
        private readonly ScriptEditorViewModel _scriptEditor;

        public ObservableCollection<VisualNode> Nodes { get; } = new();
        public ObservableCollection<NodeConnection> Connections { get; } = new();
        public ObservableCollection<ScriptTemplate> AvailableTemplates { get; } = new();

        [ObservableProperty]
        private VisualNode? _selectedNode;

        public VisualEditorViewModel(TemplateService templateService, ScriptEditorViewModel scriptEditor)
        {
            _templateService = templateService;
            _scriptEditor = scriptEditor;

            foreach (var template in _templateService.LoadTemplates())
            {
                AvailableTemplates.Add(template);
            }

            // Initialize with a start node
            var startTemplate = new ScriptTemplate(
                Name: "Start",
                Icon: "🚀",
                Category: "Logic",
                Description: "The entry point of the script",
                Template: "",
                Parameters: new List<TemplateParameter>(),
                RequiresRegion: false,
                InsertMode: "append"
            );

            var startNode = new VisualNode(startTemplate) { X = 50, Y = 50 };
            Nodes.Add(startNode);
            startNode.UpdatePinPositions();
        }

        [RelayCommand]
        public void AddNode(ScriptTemplate template)
        {
            var node = new VisualNode(template) { X = 100, Y = 100 };
            Nodes.Add(node);
            node.UpdatePinPositions();
        }

        [RelayCommand]
        public void RemoveSelectedNode()
        {
            if (SelectedNode == null) return;
            
            // Remove connections associated with this node
            var connsToRemove = Connections.Where(c => c.OutputPin.ParentNode == SelectedNode || c.InputPin.ParentNode == SelectedNode).ToList();
            foreach (var c in connsToRemove)
            {
                Connections.Remove(c);
            }

            Nodes.Remove(SelectedNode);
            SelectedNode = null;
        }

        public void ConnectPins(NodePin output, NodePin input)
        {
            // Ensure valid connection
            if (output.IsInput || !input.IsInput) return;
            if (output.ParentNode == input.ParentNode) return;

            // Remove existing connection for this output port
            var existing = Connections.FirstOrDefault(c => c.OutputPin == output);
            if (existing != null) Connections.Remove(existing);

            var existingIn = Connections.FirstOrDefault(c => c.InputPin == input);
            if (existingIn != null) Connections.Remove(existingIn);

            Connections.Add(new NodeConnection(output, input));
        }

        [RelayCommand]
        public void GenerateCode()
        {
            var startNode = Nodes.FirstOrDefault(n => n.Title == "Start");
            if (startNode == null) return;

            StringBuilder codeBuilder = new StringBuilder();
            TraverseGraph(startNode, "Next", codeBuilder, 0);

            _scriptEditor.ScriptText = codeBuilder.ToString().TrimEnd();
        }

        private void TraverseGraph(VisualNode currentNode, string outputPinName, StringBuilder builder, int indentLevel)
        {
            string indent = new string(' ', indentLevel * 4);
            var pin = currentNode.Outputs.FirstOrDefault(p => p.Name == outputPinName);
            if (pin == null) return;

            var connection = Connections.FirstOrDefault(c => c.OutputPin == pin);
            if (connection == null) return;

            var nextNode = connection.InputPin.ParentNode;

            // Generate code for next node
            var values = nextNode.Parameters.ToDictionary(p => p.Key, p => p.Value);
            string code = _templateService.ApplyTemplate(nextNode.SourceTemplate, values, "");

            if (nextNode.SourceTemplate.InsertMode == "wrap")
            {
                // A wrap node (like If, While, For) has a {selection} token that ApplyTemplate converts to 4 spaces, 
                // but actually, we should traverse its "Body" pin for the inner code.
                // ApplyTemplate currently leaves `{selection}` if not handled fully or replaces it with `    `.
                // Let's manually rebuild it for the visual graph if needed, but since it's already templated, 
                // we can just extract the first part of the template before the indent.
                
                string[] templateLines = nextNode.SourceTemplate.Template.Split(new[] { '\n' }, StringSplitOptions.None);
                string header = templateLines[0];
                foreach(var kvp in values) header = header.Replace("{" + kvp.Key + "}", kvp.Value);
                
                builder.AppendLine(indent + header);
                
                // Traverse body
                TraverseGraph(nextNode, "Body", builder, indentLevel + 1);

                // For if/else, we might have an else branch. For now we only handle the "Next" output.
            }
            else
            {
                // Standard node
                foreach (string line in code.Split(new[] { '\n' }, StringSplitOptions.RemoveEmptyEntries))
                {
                    builder.AppendLine(indent + line);
                }
            }

            // Continue to the next node in the sequence
            TraverseGraph(nextNode, "Next", builder, indentLevel);
        }
    }
}
