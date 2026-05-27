## 2026-05-27 - Adding AutomationProperties.Name to WPF Buttons
**Learning:** In WPF applications, icon-only buttons or buttons using custom content (like emojis or text icons) are not inherently accessible to screen readers. Relying solely on `ToolTip` or visible text is insufficient. Setting `AutomationProperties.Name` explicitly ensures screen readers can identify the button's purpose correctly.
**Action:** Always check icon-only or purely visual interactive elements in XAML and add an appropriate `AutomationProperties.Name` property to them.
