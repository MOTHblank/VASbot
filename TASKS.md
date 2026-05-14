# TASKS.md - VASbot3 Development

## Epic: Script Loading/Saving & Region Fixes (Current)

---

Name: Fix Script Loading - Regions Not Appearing in Editor
Status: [x]
Goal: Fix script loading so files appear in the editor when opened
Details: The issue was that embedded regions in scripts (`bot.gui.regions = [...]`) weren't being parsed and displayed in the UI. Added `extract_embedded_regions()` function to `bot_runner.py` that uses regex to find and parse region definitions.
Testing: Open a script with embedded regions - they should now appear in the editor.

---

Name: Fix Script Saving - Wrong Region Data Being Saved
Status: [x]
Goal: Fix script saving to include current regions from GUI
Details: Discovered two separate region collections: MainViewModel.Regions and Capture.Regions. Regions UI displays from Capture.Regions but Save was reading from MainViewModel.Regions. Fixed by updating ScriptEditorViewModel.cs to use Capture.Regions.
Testing: Load script → Edit regions in GUI → Save → Verify saved colors match what's in the GUI.

---

Name: Make Embedded Regions Work with Current API
Status: [x]
Goal: Make embedded regions (`bot.gui.regions = [...]`) work
Details: Added GUIProxy class to bot_api.py that enables `bot.gui.regions` syntax. Updated bot_runner.py to extract and sync these regions when loading scripts.
Testing: Create regions in GUI → Save → Reopen → Verify regions persist.

---

Name: Add Global Hotkeys (F5/F6/F12)
Status: [x]
Goal: Add global hotkeys that work even when VASbot window isn't focused
Details: Updated GlobalHotkeyService.cs to register F5 (Run), F6 (Stop), and F12 (Toggle Pause). F5 was previously missing. These work globally via Windows RegisterHotKey API.
Testing: Focus on another window, press F5/F6/F12 - the bot should respond.

---

Name: Add Emergency Killswitch
Status: [x]
Goal: Add emergency killswitch functionality
Details: Added killswitch button to MainWindow.xaml.cs that immediately stops the script via gRPC StopScript RPC.
Testing: Click killswitch while bot is running - should stop immediately.

---

Name: Fix Bot Clicking Indefinitely When Target Window Closes
Status: [x]
Goal: Fix bot clicking indefinitely when target window closes
Details: Added proper error handling in find_and_click_color. Now catches exceptions and logs when target window is unavailable.
Testing: Run bot against a window, close the window - bot should stop or handle gracefully.

---

Name: Implement DeleteRegion and PickRegionColor Commands
Status: [x]
Goal: Implement commands that are referenced in XAML but have no backing code
Details: DeleteRegionCommand and PickRegionColorCommand were manually declared which caused the CommunityToolkit MVVM source generator to fail or not bind correctly. By removing the manual properties and initialization, the methods decorated with `[RelayCommand]` correctly generated the async commands, fixing the issue where changing the color or deleting regions was ineffective.
Testing: Click delete on a region - should remove it. Click color picker - should let user pick a new color and save it successfully.

---

Name: Rebuild After Fixes
Status: []
Goal: Rebuild the application to apply all fixes
Details: Build was blocked because VASbot.exe was running (PID 20340). Need to close the app and run: cd VASbot.Gui && dotnet build
Testing: Build succeeds with no errors.

---

Name: Test Script Save/Load Cycle
Status: []
Goal: Verify the complete save/load cycle works correctly
Details: After rebuilding, test: Load script → Edit regions (colors/positions) → Save → Reopen → Verify regions match saved data.
Testing: Manual verification of saved JSON file matches GUI state.

---

## Epic: Personal Workflow & Resilience (Phase 5 - Previous)

---

Name: Sidecar Heartbeat & Auto-Restart
Status: [x]
Goal: Ensure the bot can recover from unexpected Python crashes during long unattended sessions.
Details: Modify `PythonSidecarService.cs` to monitor the sidecar process. If the process exits unexpectedly (non-zero exit code or sudden termination), automatically attempt to restart it and re-establish the gRPC connection, logging the event in the GUI terminal.
Testing: Manually kill the `python.exe` process via Task Manager while the GUI is open. Verify the GUI detects the crash, prints a warning, and spins up a new sidecar process.

---

Name: Unified Local Startup Script
Status: [x]
Goal: Provide a frictionless 1-click start for daily personal use.
Details: Create a `start_vasbot.ps1` script that automatically checks/installs `python/requirements.txt` via the local system Python, builds/runs the .NET GUI via `dotnet run`, and ensures everything cleans up on exit.
Testing: Run `./start_vasbot.ps1`. Verify it checks requirements and successfully launches the Studio interface.

---
