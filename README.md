# VASbot3

VASbot3 is a hybrid automation framework that combines a .NET 10 desktop application with a Python 3.13 execution environment. It is designed for window capture and automation script execution using gRPC and shared memory for inter-process communication.

## Architecture

The system consists of two primary components:

### .NET Host (.NET 10 WPF)
*   **Capture**: Uses DXGI Desktop Duplication for frame acquisition.
*   **Data Plane**: Manages a shared memory buffer (`VASbot_FrameBuffer`) for pixel data transfer.
*   **Interface**: Provides tools for region management, a node-based visual editor, and log monitoring.
*   **Input**: Implements a C# service for system-level input simulation.

### Python Sidecar (Python 3.13)
*   **Execution**: Runs automation scripts and handles logic.
*   **Vision**: Accesses the shared memory buffer via NumPy and OpenCV for image analysis.
*   **Control Plane**: Connects to the host via gRPC (Port 50051) to receive commands and stream logs.
*   **Automation**: Supports integration with `pywinauto` for UI element interaction.

## Features

*   **Shared Memory IPC**: Zero-copy frame access between the .NET capture process and Python logic.
*   **Visual Editor**: A WPF canvas for creating automation logic that generates Python scripts.
*   **Hotkeys**: F5 (Run), F6 (Stop), and F12 (Pause) for script control.
*   **Action Recorder**: Generates Python snippets from mouse and keyboard input.
*   **Process Isolation**: Python logic runs in a separate process from the UI and capture engine.

## Getting Started

### Prerequisites
*   Windows 10/11
*   .NET 10 SDK
*   Python 3.13
*   DirectX 11 compatible hardware

### Installation
1.  Clone the repository:
    ```bash
    git clone https://github.com/MOTHblank/VASbot.git
    cd VASbot
    ```
2.  Install dependencies:
    ```bash
    pip install -r python/requirements.txt
    ```
3.  Build:
    ```bash
    dotnet build VASbot.Gui/VASbot.Gui.csproj
    ```

### Usage
```powershell
./start_vasbot.ps1
```

## Project Structure

*   `VASbot.Gui/`: C# source code for the UI and capture services.
*   `python/`: Python source code for the sidecar and script execution.
*   `shared/`: gRPC service definitions (`bot.proto`).
*   `vascripts/`: Directory for user scripts.

## IPC Protocol

Communication is handled via gRPC as defined in `shared/protos/bot.proto`:
*   **Commands**: Unary RPCs for input simulation and state changes.
*   **Logging**: Server-side streaming for real-time log transmission.
*   **Synchronization**: Coordination of shared memory buffer lifecycle.
