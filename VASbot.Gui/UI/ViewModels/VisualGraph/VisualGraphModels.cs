using System;
using System.Collections.ObjectModel;
using System.Linq;
using CommunityToolkit.Mvvm.ComponentModel;
using VASbot.Gui.Engine;

namespace VASbot.Gui.UI.ViewModels.VisualGraph
{
    public partial class NodePin : ObservableObject
    {
        public Guid Id { get; } = Guid.NewGuid();
        public VisualNode ParentNode { get; }
        public string Name { get; }
        public bool IsInput { get; }

        [ObservableProperty]
        private double _x;

        [ObservableProperty]
        private double _y;

        public NodePin(VisualNode parent, string name, bool isInput)
        {
            ParentNode = parent;
            Name = name;
            IsInput = isInput;
        }

        public void UpdatePosition(double nodeX, double nodeY, double offsetX, double offsetY)
        {
            X = nodeX + offsetX;
            Y = nodeY + offsetY;
        }
    }

    public partial class NodeConnection : ObservableObject
    {
        public Guid Id { get; } = Guid.NewGuid();

        [ObservableProperty]
        private NodePin _outputPin;

        [ObservableProperty]
        private NodePin _inputPin;

        public NodeConnection(NodePin outputPin, NodePin inputPin)
        {
            if (outputPin.IsInput || !inputPin.IsInput)
                throw new ArgumentException("Connection must go from Output to Input");
                
            _outputPin = outputPin;
            _inputPin = inputPin;
        }
    }

    public partial class VisualNode : ObservableObject
    {
        public Guid Id { get; } = Guid.NewGuid();
        
        [ObservableProperty]
        private string _title;
        
        [ObservableProperty]
        private string _type;
        
        [ObservableProperty]
        private string _category;

        [ObservableProperty]
        private double _x;

        [ObservableProperty]
        private double _y;
        
        [ObservableProperty]
        private double _width = 180;
        
        [ObservableProperty]
        private double _height = 80;

        public ObservableCollection<NodePin> Inputs { get; } = new();
        public ObservableCollection<NodePin> Outputs { get; } = new();
        public ObservableCollection<TemplateParam> Parameters { get; } = new();
        public ScriptTemplate SourceTemplate { get; }

        public VisualNode(ScriptTemplate template)
        {
            SourceTemplate = template;
            Title = template.Name;
            Type = template.Name.Replace(" ", "_").ToLower();
            Category = template.Category;

            // Generate inputs/outputs based on template logic type (simplified for now)
            if (Title == "Start")
            {
                Outputs.Add(new NodePin(this, "Next", false));
            }
            else
            {
                Inputs.Add(new NodePin(this, "Prev", true));
                
                if (template.InsertMode == "wrap")
                {
                    // Branching / looping nodes
                    if (Title.Contains("If") || Title.Contains("While"))
                    {
                        Outputs.Add(new NodePin(this, "Body", false));
                        Outputs.Add(new NodePin(this, "Next", false));
                        Height = 100;
                    }
                    else if (Title.Contains("For"))
                    {
                        Outputs.Add(new NodePin(this, "Body", false));
                        Outputs.Add(new NodePin(this, "Next", false));
                        Height = 100;
                    }
                    else
                    {
                        Outputs.Add(new NodePin(this, "Body", false));
                        Outputs.Add(new NodePin(this, "Next", false));
                    }
                }
                else if (Title == "Find & Click Color" || Title == "Find & Click Text (OCR)")
                {
                    Outputs.Add(new NodePin(this, "Success", false));
                    Outputs.Add(new NodePin(this, "Failure", false));
                    Height = 100;
                }
                else
                {
                    Outputs.Add(new NodePin(this, "Next", false));
                }
            }

            foreach (var p in template.Parameters)
            {
                Parameters.Add(new TemplateParam(p.Key, p.Type, p.DefaultValue));
                Height += 30; // increase height for each parameter
            }
        }

        partial void OnXChanged(double value) => UpdatePinPositions();
        partial void OnYChanged(double value) => UpdatePinPositions();

        public void UpdatePinPositions()
        {
            double inSpacing = Height / (Inputs.Count + 1);
            for (int i = 0; i < Inputs.Count; i++)
            {
                Inputs[i].UpdatePosition(X, Y, 0, inSpacing * (i + 1));
            }

            double outSpacing = Height / (Outputs.Count + 1);
            for (int i = 0; i < Outputs.Count; i++)
            {
                Outputs[i].UpdatePosition(X, Y, Width, outSpacing * (i + 1));
            }
        }
    }
}
