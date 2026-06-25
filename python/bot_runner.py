import grpc
from concurrent import futures
import time
import sys
import os
import re
import ast
import numpy as np
import threading
import queue
from multiprocessing import shared_memory

# --- CRITICAL: Set DPI Awareness BEFORE any other UI/GDI calls ---
try:
    import ctypes

    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
except Exception as e:
    print(f"[Sidecar] Warning: Could not set DPI awareness ({e})")

# Add python root and core to path
base_dir = os.path.dirname(__file__)
sys.path.append(base_dir)
sys.path.append(os.path.join(base_dir, "core"))

import bot_pb2
import bot_pb2_grpc
from bot_api import BotAPI
from pywinauto_api import PywinautoBot
from recorder import ActionRecorder


def extract_embedded_regions(script_code: str) -> list:
    """Extract embedded regions from script code.

    Supports formats like:
        bot.gui.regions = [
            {'x': 91, 'y': 146, 'width': 878, 'height': 534, 'color': '#78180d'},
            ...
        ]

    Returns:
        List of region dictionaries, or empty list if no regions found.
    """
    # Safety: Limit script length to prevent DoS or memory issues
    if len(script_code) > 1000000:  # 1MB limit
        return []

    regions = []

    # Find the bot.gui.regions = start
    match = re.search(r"bot\.gui\.regions\s*=\s*(\[)", script_code)

    if match:
        try:
            start_index = match.start(1)
            # Find the closing bracket with basic parsing to handle nesting and strings
            depth = 0
            in_string = None
            escaped = False
            end_index = -1

            for i in range(start_index, len(script_code)):
                char = script_code[i]

                if escaped:
                    escaped = False
                    continue

                if char == "\\":
                    escaped = True
                    continue

                if in_string:
                    if char == in_string:
                        in_string = None
                    continue

                if char in ("'", '"'):
                    in_string = char
                    continue

                if char == "[":
                    depth += 1
                    if depth > 10:  # Limit nesting depth for safety
                        print("[Sidecar] Error: Region nesting too deep")
                        return []
                elif char == "]":
                    depth -= 1
                    if depth == 0:
                        end_index = i + 1
                        break

            if end_index == -1:
                return []

            regions_str = script_code[start_index:end_index]
            regions_list = ast.literal_eval(regions_str)

            if isinstance(regions_list, list):
                for r in regions_list:
                    if isinstance(r, dict) and all(
                        k in r for k in ["x", "y", "width", "height"]
                    ):
                        regions.append(
                            {
                                "x": r.get("x", 0),
                                "y": r.get("y", 0),
                                "width": r.get("width", 0),
                                "height": r.get("height", 0),
                                "color": r.get("color", "#FFFF00"),
                                "name": r.get("name", f"Region {len(regions)}"),
                            }
                        )
                    else:
                        print(
                            f"[Sidecar] Warning: Skipping invalid region structure: {r}"
                        )
            print(f"[Sidecar] Extracted {len(regions)} embedded regions from script")
        except Exception as e:
            print(f"[Sidecar] Failed to parse embedded regions: {e}")

    return regions


class BotServicer(bot_pb2_grpc.BotServiceServicer):
    def __init__(self):
        self.bot = BotAPI()
        self.win = PywinautoBot()
        self.recorder = ActionRecorder()
        self.target_hwnd = None
        self.shm = None
        self.frame_buffer = None
        self.script_thread = None

    def CheckHealth(self, request, context):
        return bot_pb2.HealthResponse(status=bot_pb2.HealthResponse.SERVING)

    def Ping(self, request, context):
        return bot_pb2.PingResponse(timestamp=int(time.time()))

    def SetTargetWindow(self, request, context):
        self.target_hwnd = request.hwnd
        self.bot.set_target_window(request.hwnd)
        print(f"[Sidecar] Target set to: {request.title} (HWND: {request.hwnd})")
        return bot_pb2.UpdateResponse(success=True)

    def NotifyFrameUpdate(self, request, context):
        try:
            if self.shm is None or self.shm.name != request.memory_map_name:
                if self.shm:
                    self.shm.close()
                self.shm = shared_memory.SharedMemory(name=request.memory_map_name)

            byte_count = request.height * request.width * 4
            shape = (request.height, request.width, 4)

            self.frame_buffer = np.frombuffer(
                self.shm.buf, dtype=np.uint8, count=byte_count
            ).reshape(shape)
            self.bot.set_frame_buffer(self.frame_buffer)
            return bot_pb2.FrameResponse(acknowledged=True)
        except Exception as e:
            print(f"[Sidecar] Frame Error: {e}")
            return bot_pb2.FrameResponse(acknowledged=False)

    def UpdateRegions(self, request, context):
        regions = []
        for r in request.regions:
            regions.append(
                {
                    "name": r.name,
                    "x": r.x,
                    "y": r.y,
                    "width": r.width,
                    "height": r.height,
                }
            )
        self.bot.set_regions(regions)
        return bot_pb2.UpdateResponse(success=True)

    def ExecuteScript(self, request, context):
        try:
            print(f"[Sidecar] Starting execution (ID: {request.correlation_id})")
        except Exception:
            pass

        # Stop previous script thread if still running
        if self.script_thread and self.script_thread.is_alive():
            print("[Sidecar] Previous script thread still running. Stopping it...")
            self.bot.is_running = False
            self.script_thread.join(timeout=3.0)
            if self.script_thread.is_alive():
                print(
                    "[Sidecar] Warning: Previous script thread did not terminate in time."
                )

        # Extract embedded regions BEFORE execution
        embedded_regions = extract_embedded_regions(request.code)
        if embedded_regions:
            self.bot.set_regions(embedded_regions)
            # Also update the GUI proxy so bot.gui.regions works
            if hasattr(self.bot.gui, "regions"):
                self.bot.gui.regions = embedded_regions
            try:
                print(f"[Sidecar] Applied {len(embedded_regions)} embedded regions")
            except Exception:
                pass

        log_queue = queue.Queue()

        def log_callback(msg):
            log_queue.put(msg)

        globals_dict = {
            "bot": self.bot,
            "win": self.win,
            "app": self.win.get_app(self.target_hwnd) if self.target_hwnd else None,
            "regions": self.bot.regions,
            "hwnd": self.target_hwnd,
            "time": time,
            "np": np,
        }

        self.bot.on_log = log_callback
        self.bot.is_running = True

        # Run script in a background thread so we can yield logs in real-time
        def run_thread():
            try:
                exec(request.code, globals_dict)
                log_queue.put("Script completed successfully.")
            except Exception as e:
                log_queue.put(f"Python Error: {str(e)}")
            finally:
                self.bot.is_running = False
                log_queue.put(None)  # Signal end of stream

        self.script_thread = threading.Thread(target=run_thread)
        self.script_thread.start()

        # Yield logs as they arrive in the queue
        while True:
            try:
                msg = log_queue.get(timeout=0.1)
                if msg is None:
                    break
                try:
                    yield bot_pb2.ScriptLog(
                        message=str(msg), correlation_id=request.correlation_id
                    )
                except Exception as yield_err:
                    print(f"[Sidecar] Yield error: {yield_err}")
                    break
            except queue.Empty:
                if not context.is_active():
                    self.bot.is_running = False  # Handle client disconnect
                    break
                continue

    def GetStatus(self, request, context):
        return bot_pb2.StatusResponse(is_running=self.bot.is_running)

    def StopScript(self, request, context):
        """Stop the currently running script by setting is_running to False."""
        print("[Sidecar] StopScript called - setting is_running = False")
        self.bot.is_running = False
        if self.script_thread and self.script_thread.is_alive():
            self.script_thread.join(timeout=1.0)
        return bot_pb2.StopResponse(success=True)

    def StartRecording(self, request, context):
        self.recorder.start_recording()
        return bot_pb2.UpdateResponse(success=True)

    def StopRecording(self, request, context):
        self.recorder.stop_recording()
        script = self.recorder.generate_script(
            regions=self.bot.regions, target_hwnd=self.target_hwnd
        )
        return bot_pb2.RecordingResponse(success=True, script=script)

    # --- Advanced Window Automation ---

    def ClickElement(self, request, context):
        success = self.bot.click_element(
            request.identifier, request.control_type, request.double_click
        )
        return bot_pb2.UpdateResponse(success=success)

    def TypeIntoElement(self, request, context):
        success = self.bot.type_into(
            request.identifier, request.text, request.clear_first
        )
        return bot_pb2.UpdateResponse(success=success)

    def WaitWindow(self, request, context):
        success = self.bot.wait_window(request.title, request.timeout)
        if success:
            self.target_hwnd = self.bot._target_hwnd
        return bot_pb2.UpdateResponse(success=success)


def serve():
    # Ensure Windows does not lie about screen coordinates due to DPI scaling
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception as e:
        print(f"[Sidecar] Warning: Could not set DPI awareness ({e})")

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    bot_pb2_grpc.add_BotServiceServicer_to_server(BotServicer(), server)
    server.add_insecure_port("127.0.0.1:50051")
    server.start()
    print("[Sidecar] gRPC Server running on 127.0.0.1:50051")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
