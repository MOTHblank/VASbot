# VASbot3

A high-performance, hybrid automation engine designed for low-latency window capture and resilient script execution. VASbot3 bridges the rich UI and high-speed capture capabilities of **.NET 10** with the flexible, logic-heavy ecosystem of **Python 3.13**.

## 🏛️ Architecture

VASbot3 utilizes a **Distributed Sidecar** architecture, separating the performance-critical UI and capture layer from the automation logic layer.

### 1. The .NET Host (.NET 10 WPF)
*   **High-Speed Capture**: Implements **DXGI (DirectX Graphics Infrastructure)** Desktop Duplication for ultra-low latency frame acquisition (60FPS+).
*   **Data Plane**: Manages a shared memory buffer (`VASbot_FrameBuffer`) in system RAM, providing zero-copy pixel access to the Python sidecar.
*   **User Interface**: A modern WPF interface for region management, visual node-based scripting, and real-time log monitoring.
*   **Input Driver**: Provides kernel-level input simulation (SendInput) via a dedicated C# service.

### 2. The Python Sidecar (Python 3.13)
*   **Logic Engine**: Executes user scripts and coordinates automation tasks.
*   **Vision Stack**: Utilizes NumPy and OpenCV to map the shared memory buffer directly into memory for instant image analysis.
*   **gRPC Control Plane**: Communicates with the .NET host via a binary RPC channel (Port 50051), handling command execution and log streaming.
*   **Integration**: Seamlessly integrates `pywinauto` for advanced UI automation and element-level interactions.

## 🚀 Key Features

*   **Zero-Copy Vision**: Instant access to captured frames via shared memory, bypassing slow serialization/deserialization.
*   **Visual Node Scripting**: A WPF-based canvas for building automation logic visually, which transpiles to Python code.
*   **Global Hotkeys**: System-wide control (F5: Run, F6: Stop, F12: Pause) for immediate intervention.
*   **Action Recorder**: Capture real-time user input to automatically generate Python automation snippets.
*   **Resilient Execution**: The Python sidecar runs as a separate process; logic crashes do not affect the capture host or UI state.

## 🛠️ Getting Started

### Prerequisites
*   Windows 10/11
*   .NET 10 SDK
*   Python 3.13 (added to PATH)
*   DirectX 11 compatible hardware

### Installation
1.  Clone the repository:
    ```bash
    git clone https://github.com/MOTHblank/VASbot.git
    cd VASbot
    ```
2.  Install Python dependencies:
    ```bash
    pip install -r python/requirements.txt
    ```
3.  Build the .NET application:
    ```bash
    dotnet build VASbot.Gui/VASbot.Gui.csproj
    ```

### Usage
Run the unified launcher script:
```powershell
./start_vasbot.ps1
```

## 📂 Project Structure

*   `VASbot.Gui/`: WPF Application and core C# services (Capture, Hotkeys, IPC).
*   `python/`: Python logic, gRPC server, and script runner.
*   `shared/`: Protocol Buffer definitions and shared assets.
*   `vascripts/`: Default directory for user automation scripts.

## 📡 IPC Protocol

The system uses a custom gRPC service defined in `shared/protos/bot.proto`. The service supports:
*   **Unary RPCs**: Simple commands (Click, Type, Move).
*   **Server Streaming**: Real-time log output and status updates from the Python sidecar to the GUI.
*   **Shared Memory Mapping**: Coordination of the `VASbot_FrameBuffer` lifecycle.

---
*Developed for performance-critical automation and research.*
