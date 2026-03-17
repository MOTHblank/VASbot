# TASKS.md - VASbot3 Development

## Epic: Personal Workflow & Resilience (Phase 5 - Current)

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