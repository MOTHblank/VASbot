using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Shapes;
using VASbot.Gui.UI.ViewModels;
using VASbot.Gui.UI.ViewModels.VisualGraph;

namespace VASbot.Gui.UI.Views
{
    public partial class VisualEditorView : UserControl
    {
        private bool _isDraggingNode;
        private Point _dragStartPoint;
        private VisualNode? _draggedNode;

        private bool _isDrawingConnection;
        private NodePin? _startPin;

        public VisualEditorView()
        {
            InitializeComponent();
        }

        private VisualEditorViewModel? ViewModel => DataContext as VisualEditorViewModel;

        // --- Node Dragging ---
        private void Node_MouseDown(object sender, MouseButtonEventArgs e)
        {
            if (e.ChangedButton != MouseButton.Left) return;

            if (sender is FrameworkElement fe && fe.DataContext is VisualNode node)
            {
                _isDraggingNode = true;
                _draggedNode = node;
                if (ViewModel != null) ViewModel.SelectedNode = node;
                _dragStartPoint = e.GetPosition(GraphCanvas);
                fe.CaptureMouse();
                e.Handled = true;
            }
        }

        private void Node_MouseMove(object sender, MouseEventArgs e)
        {
            if (_isDraggingNode && _draggedNode != null && sender is FrameworkElement fe)
            {
                var currentPoint = e.GetPosition(GraphCanvas);
                double deltaX = currentPoint.X - _dragStartPoint.X;
                double deltaY = currentPoint.Y - _dragStartPoint.Y;

                _draggedNode.X += deltaX;
                _draggedNode.Y += deltaY;

                _dragStartPoint = currentPoint;
                e.Handled = true;
            }
        }

        private void Node_MouseUp(object sender, MouseButtonEventArgs e)
        {
            if (_isDraggingNode && sender is FrameworkElement fe)
            {
                _isDraggingNode = false;
                _draggedNode = null;
                fe.ReleaseMouseCapture();
                e.Handled = true;
            }
        }

        // --- Pin Connection Drawing ---
        private void Pin_MouseDown(object sender, MouseButtonEventArgs e)
        {
            if (e.ChangedButton != MouseButton.Left) return;

            if (sender is FrameworkElement fe && fe.DataContext is NodePin pin)
            {
                // Start drawing line
                _isDrawingConnection = true;
                _startPin = pin;
                
                ActiveConnectionLine.Visibility = Visibility.Visible;
                ActiveConnectionLine.X1 = pin.X;
                ActiveConnectionLine.Y1 = pin.Y;
                ActiveConnectionLine.X2 = pin.X;
                ActiveConnectionLine.Y2 = pin.Y;

                GraphCanvas.CaptureMouse();
                e.Handled = true;
            }
        }

        private void Canvas_MouseMove(object sender, MouseEventArgs e)
        {
            if (_isDrawingConnection)
            {
                var pos = e.GetPosition(GraphCanvas);
                ActiveConnectionLine.X2 = pos.X;
                ActiveConnectionLine.Y2 = pos.Y;
            }
        }

        private void Canvas_MouseUp(object sender, MouseButtonEventArgs e)
        {
            if (_isDrawingConnection)
            {
                _isDrawingConnection = false;
                ActiveConnectionLine.Visibility = Visibility.Collapsed;
                GraphCanvas.ReleaseMouseCapture();

                // Hit test for drop pin
                var pt = e.GetPosition(GraphCanvas);
                var hitResult = VisualTreeHelper.HitTest(GraphCanvas, pt);

                if (hitResult != null && hitResult.VisualHit is FrameworkElement fe && fe.DataContext is NodePin endPin)
                {
                    if (_startPin != null && ViewModel != null)
                    {
                        var outPin = _startPin.IsInput ? endPin : _startPin;
                        var inPin = _startPin.IsInput ? _startPin : endPin;

                        ViewModel.ConnectPins(outPin, inPin);
                    }
                }
            }
        }

        private void Pin_MouseUp(object sender, MouseButtonEventArgs e)
        {
            // If mouse goes up directly over a pin while drawing, canvas mouse up handles it via HitTest, 
            // but we can also handle it here.
            if (_isDrawingConnection && sender is FrameworkElement fe && fe.DataContext is NodePin endPin)
            {
                if (_startPin != null && ViewModel != null)
                {
                    var outPin = _startPin.IsInput ? endPin : _startPin;
                    var inPin = _startPin.IsInput ? _startPin : endPin;

                    ViewModel.ConnectPins(outPin, inPin);
                }

                _isDrawingConnection = false;
                ActiveConnectionLine.Visibility = Visibility.Collapsed;
                GraphCanvas.ReleaseMouseCapture();
                e.Handled = true;
            }
        }
    }
}
