import grpc
from concurrent import futures
import time
import sys
import os
import numpy as np
import threading
import queue
from multiprocessing import shared_memory

# Add python root and core to path
base_dir = os.path.dirname(__file__)
sys.path.append(base_dir)
sys.path.append(os.path.join(base_dir, 'core'))

import bot_pb2
import bot_pb2_grpc
from bot_api import BotAPI
from pywinauto_api import PywinautoBot
from recorder import ActionRecorder

class BotServicer(bot_pb2_grpc.BotServiceServicer):
    def __init__(self):
        self.bot = BotAPI()
        self.win = PywinautoBot()
        self.recorder = ActionRecorder()
        self.target_hwnd = None
        self.shm = None
        self.frame_buffer = None

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
                if self.shm: self.shm.close()
                self.shm = shared_memory.SharedMemory(name=request.memory_map_name)
            
            byte_count = request.height * request.width * 4
            shape = (request.height, request.width, 4)
            
            self.frame_buffer = np.frombuffer(self.shm.buf, dtype=np.uint8, count=byte_count).reshape(shape)
            self.bot.set_frame_buffer(self.frame_buffer)
            return bot_pb2.FrameResponse(acknowledged=True)
        except Exception as e:
            print(f"[Sidecar] Frame Error: {e}")
            return bot_pb2.FrameResponse(acknowledged=False)

    def UpdateRegions(self, request, context):
        regions = []
        for r in request.regions:
            regions.append({
                'name': r.name,
                'x': r.x, 'y': r.y,
                'width': r.width, 'height': r.height
            })
        self.bot.set_regions(regions)
        return bot_pb2.UpdateResponse(success=True)

    def ExecuteScript(self, request, context):
        print(f"[Sidecar] Starting execution (ID: {request.correlation_id})")
        
        log_queue = queue.Queue()
        def log_callback(msg):
            log_queue.put(msg)

        globals_dict = {
            'bot': self.bot,
            'win': self.win,
            'app': self.win.get_app(self.target_hwnd) if self.target_hwnd else None,
            'regions': self.bot.regions,
            'hwnd': self.target_hwnd,
            'time': time,
            'np': np
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
                log_queue.put(None) # Signal end of stream

        thread = threading.Thread(target=run_thread)
        thread.start()

        # Yield logs as they arrive in the queue
        while True:
            try:
                msg = log_queue.get(timeout=0.1)
                if msg is None: break
                yield bot_pb2.ScriptLog(message=str(msg), correlation_id=request.correlation_id)
            except queue.Empty:
                if not context.is_active():
                    self.bot.is_running = False # Handle client disconnect
                    break
                continue

    def GetStatus(self, request, context):
        return bot_pb2.StatusResponse(is_running=self.bot.is_running)

    def StartRecording(self, request, context):
        self.recorder.start()
        return bot_pb2.UpdateResponse(success=True)

    def StopRecording(self, request, context):
        script = self.recorder.stop()
        return bot_pb2.RecordingResponse(success=True, script=script)

    # --- Advanced Window Automation ---

    def ClickElement(self, request, context):
        success = self.bot.click_element(
            request.identifier, 
            request.control_type, 
            request.double_click
        )
        return bot_pb2.UpdateResponse(success=success)

    def TypeIntoElement(self, request, context):
        success = self.bot.type_into(
            request.identifier, 
            request.text, 
            request.clear_first
        )
        return bot_pb2.UpdateResponse(success=success)

    def WaitWindow(self, request, context):
        success = self.bot.wait_window(request.title, request.timeout)
        if success:
            self.target_hwnd = self.bot._target_hwnd
        return bot_pb2.UpdateResponse(success=success)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    bot_pb2_grpc.add_BotServiceServicer_to_server(BotServicer(), server)
    server.add_insecure_port('127.0.0.1:50051')
    server.start()
    print("[Sidecar] gRPC Server running on 127.0.0.1:50051")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
