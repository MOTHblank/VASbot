import threading
import time
import queue
import traceback
from datetime import datetime
import tkinter as tk

from core.bot_api import BotAPI

class ScriptRunner:
    def __init__(self, gui_instance):
        self.gui = gui_instance
        self.script_thread = None
        self.bot_api = None
        self._pause_event = threading.Event()
        self._stop_event = threading.Event()
        self._pause_event.set()  # Start in unpaused state
        
        # Performance monitoring
        self._start_time = None
        self._execution_time = 0
        self._actions_count = 0
        self._errors_count = 0
        
        # Script state
        self._script_state = "idle"  # idle, running, paused, stopped, error
        self._last_error = None
        
        # Communication queue for thread-safe GUI updates
        self._message_queue = queue.Queue()
        
        # Debugging
        self._debug_mode = False
        self._performance_log = []
        
    def enable_debug_mode(self):
        """Enable debug mode for detailed logging and performance metrics"""
        self._debug_mode = True
        self.log("Debug mode enabled - detailed logging and performance metrics active")
        
    def log(self, message):
        """Thread-safe logging method"""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        full_message = f"[{timestamp}] {message}"
        
        # Put message in queue for GUI thread to process
        self._message_queue.put(('log', full_message))
        
        # Also print to console if in debug mode
        if self._debug_mode:
            print(f"[DEBUG] {full_message}")
            
    def _process_message_queue(self):
        """Process messages from the script thread (called from GUI thread)"""
        try:
            while True:
                msg_type, msg_data = self._message_queue.get_nowait()
                
                if msg_type == 'log':
                    if hasattr(self.gui, 'log_message'):
                        self.gui.log_message(msg_data)
                elif msg_type == 'status':
                    self.gui.status_var.set(msg_data)
                elif msg_type == 'state':
                    self._update_script_state(msg_data)
                elif msg_type == 'performance':
                    self._performance_log.append(msg_data)
                    
        except queue.Empty:
            pass
            
    def _update_script_state(self, new_state):
        """Update script state and GUI accordingly"""
        self._script_state = new_state
        
        if new_state == "running":
            self.gui.play_button.config(state=tk.DISABLED)
            self.gui.pause_button.config(text="⏸️ Pause (F6)", state=tk.NORMAL)
        elif new_state == "paused":
            self.gui.pause_button.config(text="▶️ Resume (F6)")
        elif new_state == "stopped" or new_state == "idle" or new_state == "error":
            self.gui.play_button.config(state=tk.NORMAL)
            self.gui.pause_button.config(text="⏸️ Pause (F6)", state=tk.DISABLED)
    def _execute(self, script_code):
        try:
            # Set up script environment
            script_globals = {
                'bot': self.bot_api,
                'time': time,
                'print': self.bot_api.log,
                '__builtins__': __builtins__,
                'debug': self._debug_mode
            }
            
            # Pre-script setup
            self._message_queue.put(('state', 'running'))
            self.log("=== Script execution started ===")
            self._start_time = time.time()
            
            # Execute the script
            exec(script_code, script_globals)
            
            # Post-script cleanup
            self._execution_time = time.time() - self._start_time
            self.log(f"=== Script completed in {self._execution_time:.2f} seconds ===")
            self.log(f"Performance: {self._actions_count} actions, {self._errors_count} errors")
            
            if self._debug_mode:
                self.log("=== Performance Metrics ===")
                for entry in self._performance_log:
                    self.log(f"  {entry}")
                    
        except KeyboardInterrupt:
            self.log("Script interrupted by user")
            self._message_queue.put(('state', 'stopped'))
        except SystemExit:
            self.log("Script exited normally")
            self._message_queue.put(('state', 'stopped'))
        except Exception as e:
            self._errors_count += 1
            self._last_error = str(e)
            error_details = traceback.format_exc()
            self.log(f"SCRIPT ERROR: {self._last_error}")
            self.log(f"Error details:\n{error_details}")
            self._message_queue.put(('state', 'error'))
        finally:
            # Ensure cleanup happens
            if self.bot_api and self.bot_api.is_running:
                self.bot_api.is_running = False
                self.log("Script execution finished.")
                
            # Notify GUI on main thread
            if hasattr(self.gui, 'on_script_finished'):
                self.gui.on_script_finished()
                
            # Final state update
            if self._script_state not in ["stopped", "error"]:
                self._message_queue.put(('state', 'idle'))
                
    def _visual_script_to_code(self, visual_script):
        """Convert visual script dict into Python code string (subset)."""
        code = "# generated from visual script\nwhile bot.is_running:\n"
        order = self._get_visual_execution_order(visual_script)
        for node in order:
            t = node["type"]
            p = node.get("params", {})
            if t == "find_click_color":
                mods = f", modifiers={p['modifiers']}" if p.get("modifiers") else ""
                code += f"    bot.find_and_click_color(hex_color='{p['hex_color']}', region_index={p['region_index']}, tolerance={p['tolerance']}, button='{p['button']}', background={p['background']}{mods})\n"
                code += "    bot.wait(0.5)\n"
            elif t == "click_region":
                mods = f", modifiers={p['modifiers']}" if p.get("modifiers") else ""
                code += f"    bot.click_region(region_index={p['region_index']}, button='{p['button']}', background={p['background']}{mods})\n"
            elif t == "wait":
                code += f"    bot.wait({p['seconds']})\n"
            elif t == "random_wait":
                code += f"    bot.random_wait({p['base_seconds']}, {p['variance_seconds']})\n"
        return code

    def _get_visual_execution_order(self, visual_script):
        """Simple linear traversal based on connections starting from 'start'."""
        nodes = {n['id']: n for n in visual_script['nodes']}
        conn_map = {c['from_node']: c['to_node'] for c in visual_script['connections'] if c['from_port'] == 0}
        order = []
        current = next((n['id'] for n in visual_script['nodes'] if n['type'] == 'start'), None)
        visited = set()
        while current and current in conn_map and current not in visited:
            next_id = conn_map[current]
            if next_id in nodes:
                order.append(nodes[next_id])
                visited.add(next_id)
                current = next_id
            else:
                break
        return order

    def _execute_visual_script(self, visual_script):
        python_code = self._visual_script_to_code(visual_script)
        self._execute(python_code)

    def run_script(self, script_code=None, visual_script=None):
        if self.is_running():
            self._message_queue.put(('status', "⚠️ A script is already running."))
            return
    
        # Reset control events
        self._pause_event.set()  # Start unpaused
        self._stop_event.clear()
        
        # Reset performance metrics
        self._start_time = None
        self._execution_time = 0
        self._actions_count = 0
        self._errors_count = 0
        self._last_error = None
        self._performance_log = []
        
        # Create a new BotAPI instance for this run
        self.bot_api = BotAPI(self.gui)
        self.bot_api._is_running = True
        # Link the pause event to the API for wait() function
        self.bot_api._pause_event = self._pause_event
        self.bot_api._stop_event = self._stop_event
        
        # Add action counter to BotAPI
        original_log = self.bot_api.log
        def counting_log(message):
            self._actions_count += 1
            if self._debug_mode and ("clicked" in message.lower() or "pressed" in message.lower()):
                action_time = time.time() - (self._start_time or time.time())
                self._performance_log.append(f"T+{action_time:.2f}s: {message}")
            return original_log(message)
        self.bot_api.log = counting_log
        
        # Enhanced wait function
        original_wait = self.bot_api.wait
        def enhanced_wait(seconds):
            """Enhanced wait that can be paused and stopped"""
            if not self.bot_api.is_running:
                return
            start_wait = time.time()
            if self._debug_mode:
                self.log(f"Waiting for {seconds} seconds")
            # Break wait into smaller chunks to be more responsive
            chunk_size = 0.1
            total_waited = 0
            while total_waited < seconds and self.bot_api.is_running:
                # Wait for unpause
                self._pause_event.wait()
                # Check if stopped while paused
                if not self.bot_api.is_running:
                    break
                # Wait for a small chunk
                remaining = seconds - total_waited
                wait_time = min(chunk_size, remaining)
                time.sleep(wait_time)
                total_waited += wait_time
            actual_wait = time.time() - start_wait
            if self._debug_mode and abs(actual_wait - seconds) > 0.1:
                self.log(f"Wait requested: {seconds}s, actual: {actual_wait:.2f}s")
        
        # Override the wait function
        self.bot_api.wait = enhanced_wait
        
        # Determine which type of script to run
        if visual_script:
            # Run visual script
            self.script_thread = threading.Thread(
                target=self._execute_visual_script,
                args=(visual_script,),
                name="VisualScriptRunner",
                daemon=True
            )
        else:
            # Run text script
            self.script_thread = threading.Thread(
                target=self._execute,
                args=(script_code,),
                name="ScriptRunner",
                daemon=True
            )
        
        self.script_thread.start()
        self._message_queue.put(('status', "▶️ Script running... Use hotkeys for control!"))
        # Start processing messages in the GUI thread
        self._process_gui_messages()