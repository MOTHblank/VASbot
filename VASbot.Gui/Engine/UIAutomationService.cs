using System;
using System.Windows;
using VASbot.Gui.Engine;
using VASbot.Gui.UI.ViewModels;
using System.Windows;
using VASbot.Gui.Engine;
using VASbot.Gui.UI.ViewModels;
using System.Collections.Generic;
using System.Windows.Automation;
using Rect = System.Windows.Rect;

namespace VASbot.Gui.Engine
{
    public class UIAutomationService
    {
        public record AutomationElementInfo(string Name, string AutomationId, string ControlType, System.Windows.Rect BoundingRectangle, AutomationElement Element);

        public List<AutomationElementInfo> GetElementTree(nint hwnd)
        {
            var results = new List<AutomationElementInfo>();
            if (hwnd == IntPtr.Zero) return results;

            try
            {
                var root = AutomationElement.FromHandle(hwnd);
                if (root == null) return results;

                WalkTree(root, results, 0);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[UIA Error] {ex.Message}");
            }

            return results;
        }

        private void WalkTree(AutomationElement element, List<AutomationElementInfo> results, int depth)
        {
            if (depth > 5) return; // Limit depth for performance

            try
            {
                var info = new AutomationElementInfo(
                    element.Current.Name,
                    element.Current.AutomationId,
                    element.Current.LocalizedControlType,
                    element.Current.BoundingRectangle,
                    element
                );
                results.Add(info);

                var children = element.FindAll(TreeScope.Children, System.Windows.Automation.Condition.TrueCondition);
                foreach (AutomationElement child in children)
                {
                    WalkTree(child, results, depth + 1);
                }
            }
            catch
            {
                // Some elements might be inaccessible
            }
        }
    }
}
