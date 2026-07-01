## 2026-07-01 - Added missing AutomationProperties.Name to icon-only buttons
**Learning:** Found multiple icon-only buttons (like ✕ for deleting items, 🎨 for color picking) that lacked `AutomationProperties.Name`, making them inaccessible to screen readers in this WPF application.
**Action:** Always add `AutomationProperties.Name` or `ToolTip` to icon-only buttons or custom content buttons to ensure screen reader compatibility, as highlighted in memory.
