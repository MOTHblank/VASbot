# VASbot3 - Project Structure & Development Roadmap

VASbot3 is a high-performance, hybrid automation engine bridging .NET 10 (UI/Capture) and Python 3.13 (Logic/Execution).

## 🏛️ Architecture: Distributed Sidecar

The system operates as two distinct processes linked by a high-speed inter-process communication (IPC) bridge.

### 📡 The Bridge
1.  **Shared Memory (Data Plane)**: A 1920x1080 BGRA buffer (`VASbot_FrameBuffer`) in system RAM. C# writes raw pixels; Python maps them as a NumPy array for zero-copy vision access.
2.  **gRPC (Control Plane)**: A binary RPC channel on port 50051. Handles command-and-control, real-time log streaming, and state synchronization.

---

## 📜 Legacy File Audit (VASbot2)

| Legacy File | Original Purpose | VASbot3 Status |
| :--- | :--- | :--- |
| `colorbot_gui.py` | Main Tkinter entry point & event orchestrator. | ❌ **REPLACED** by .NET WPF GUI. |
| `window_manager.py`| Window enumeration, title matching, & HWND focus. | ✅ **PORTED** to C# `IBotService`. |
| `canvas_manager.py`| Image preview state, eyedropper, & zoom logic. | ✅ **PORTED** to `CaptureViewModel`. |
| `region_manager.py`| Definition, persistence, & scaling of click regions. | ✅ **PORTED** to C# `RegionManager`. |
| `script_manager.py`| Script CRUD, auto-indenting, & run-loop logic. | ✅ **PORTED** to `ScriptEditorViewModel`. |
| `visual_editor.py` | Window management for the node-based canvas. | ❌ **MISSING** (Requires WPF Canvas). |
| `visual_canvas.py` | Logic for node drawing, drag-drop, & connections. | ❌ **MISSING** (Requires WPF Canvas). |
| `action_builder.py`| Tooltip-rich UI for building code snippets. | ✅ **PORTED** (WPF Template System). |
| `hotkey_editor.py` | UI for global hotkey mapping & recording. | ✅ **PORTED** to `HotkeySettingsViewModel`. |
| `tooltip.py` | Custom Tkinter tooltips for Action Builder. | ✅ **NATIVE** (Standard WPF ToolTips). |
| `player_section.py`| Compact playback/stop controls. | ✅ **PORTED** to Main Ribbon. |
| `capture_panel.py` | Preview surface for window mirroring. | ✅ **PORTED** to SkiaSharp View. |

---

## 🛠️ Feature Audit & Status

| Feature | Description | Status |
| :--- | :--- | :--- |
| **DXGI Capture** | 60FPS high-speed screen/window capture via DirectX 11. | ✅ **STABLE** |
| **Shared Memory** | Zero-copy pixel transfer between C# and Python. | ✅ **STABLE** |
| **gRPC Sidecar** | Standalone Python process for crash-resilient execution. | ✅ **STABLE** |
| **Log Streaming** | Real-time `bot.log()` output in the GUI terminal. | ✅ **STABLE** |
| **Action Recorder** | Capture mouse/keyboard and generate Python code. | ✅ **STABLE** |
| **Region Sync** | Auto-synchronize GUI regions to Python scripter. | ✅ **STABLE** |
| **Input Drivers** | `bot.click()`, `bot.type()` via kernel-level SendInput. | ✅ **STABLE** |
| **Advanced Auto** | pywinauto integration (element clicking, typing). | ✅ **STABLE** (Integrated in gRPC) |
| **Visual Scripting**| Node-based visual graph editor. | ✅ **STABLE** (WPF Canvas Integration) |
| **Drag & Drop** | Coordinated region-to-region mouse dragging. | ✅ **STABLE** |
| **Human Pathing** | Bezier curve mouse movement interpolation. | ✅ **STABLE** |

---

## 🚀 Development Plan: The Path to Parity

### Phase 1: The "High-Level" Bridge ✅
*   **Objective**: Expose legacy `pywinauto` and `windows_utils` through gRPC.
*   **Goal**: Allow scripts to use `bot.click_element("LoginButton")` instead of just pixel coordinates.

### Phase 2: Action Builder Enrichment ✅
*   **Objective**: Transform the Action Builder into a self-sufficient scripting tool capable of complete automation without manual coding.
*   **Goal**: 
    * Add comprehensive control flow templates (If/Else, Loops, Variable assignment).
    * Add advanced UI automation templates (Wait for Element, Select Dropdown, Get Text, etc.).
    * Introduce smart auto-fill: dragging/selecting from UIA Tree or Region list automatically populates template parameters.
    * Support composite snippet creation (saving custom sequences of actions).

### Phase 3: The Visual Revival ✅
*   **Objective**: Re-implement the `visual_canvas.py` logic in WPF.
*   **Goal**: A full node-based editor that generates Python code for the sidecar.

### Phase 4: High-Speed Vision ✅
*   **Objective**: Integrate `vision.py` OpenCV template matching into the core gRPC Sidecar.
*   **Goal**: Allow scripts to use `bot.find_image("template.png")` via zero-copy shared memory instead of slow base64 pipe transfers.

### Phase 5: Personal Workflow & Resilience ✅
*   **Objective**: Ensure daily usability and high uptime for local personal use.
*   **Goal**: 
    *   **Sidecar Heartbeat**: Auto-restart the Python gRPC server if it crashes during a long botting session.
    *   **Unified Startup**: A single script or launcher sequence that verifies local `requirements.txt` and starts both the .NET GUI and Python Sidecar seamlessly.
