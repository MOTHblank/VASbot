# GEMINI.md - VASbot3 Development Guidelines

## Code Quality
- Write clean, readable code
- Follow consistent naming conventions
- Add meaningful comments
- Write unit tests for all functions
- Write integration tests at relevant levels

## Version Control
- Make atomic commits
- Write descriptive commit messages using conventional commits standards
- Use feature branches

## Planning
- Think through the problem at hand deeply
- Ask follow up questions and confirm EVERYTHING
- Reduce the problem into either epics and then stories or only stories depending on how big the problem is
- Document all epics/stories in TASKS.md

## Tasks
- All tasks should be clearly defined
- All tasks should be as small as possible while still being meaningful
- All tasks should defined their goal
- All tasks should define how they can be tested

## Task format
---

Name: name of the task
Status: []
Goal: the goal of the task
Details: any details relating to requirements or implementation details
Testing: description of how this can be tested

---

## Project-Specific Guidelines

### Architecture
- VASbot3 is a hybrid .NET 10 (UI/Capture) + Python 3.13 (Logic/Execution) system
- Communication via gRPC on port 50051 + shared memory for frame buffer
- Python runs as a sidecar process, not in-process

### Key Files (DO NOT MODIFY WITHOUT UNDERSTANDING)
- `VASbot.Gui/UI/ViewModels/CaptureViewModel.cs` - Region management commands
- `VASbot.Gui/UI/ViewModels/ScriptEditorViewModel.cs` - Script load/save logic
- `VASbot.Gui/Engine/GlobalHotkeyService.cs` - Global hotkey registration
- `python/core/bot_api.py` - Python bot API (GUIProxy for regions)
- `python/bot_runner.py` - Script execution and region extraction

### Critical Bug Patterns to Avoid
1. **Region Sync**: Never read from MainViewModel.Regions when saving - always use Capture.Regions
2. **TextChanged Loops**: Always use `_isSyncingText` flag when updating TextBox from code
3. **Global Hotkeys**: Register F5/F6/F12 all together, not selectively
4. **Embedded Regions**: Must extract and sync via extract_embedded_regions() on load

### Testing Protocol
1. Close VASbot before building (check for running process)
2. Build with `dotnet build` in VASbot.Gui directory
3. Test save/load cycle manually - verify JSON matches GUI state
4. Test global hotkeys from another window

### Known Issues
- DeleteRegionCommand and PickRegionColorCommand need implementation in CaptureViewModel.cs
- Build may fail if VASbot.exe is still running
