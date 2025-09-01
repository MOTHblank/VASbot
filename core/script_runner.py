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

    def is_running(self):
        """Check if the script thread is currently running."""
        return self.script_thread is not None and self.script_thread.is_alive()
        
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

    def stop(self):
        """Signal the script thread to stop."""
        if self.is_running():
            self.log("⏹️ Stop signal sent to script.")
            self._stop_event.set()

    def _visual_script_to_code(self, visual_script: dict) -> str:
        """Convert visual script dict into a runnable Python code string."""
        nodes = {n['id']: n for n in visual_script['nodes']}
        connections = visual_script['connections']

        # Build an adjacency list for the graph: from_node_id -> {from_port_idx: to_node_id}
        adj = {node_id: {} for node_id in nodes}
        for conn in connections:
            # Ensure from_node exists before adding
            if conn['from_node'] in adj:
                adj[conn['from_node']][conn['from_port']] = conn['to_node']

        start_node_id = next((n['id'] for n in nodes.values() if n['type'] == 'start'), None)
        if not start_node_id:
            self.log("Visual script error: 'start' node not found.")
            return ""

        # Generate the sequence of code lines by traversing the graph
        code_lines = self._generate_code_from_node(start_node_id, nodes, adj, set())

        # Indent and wrap the generated code in the main `while` loop
        indented_code = "\n".join([f"    {line}" for line in code_lines if line]) if code_lines else "    pass"
        return f"# Generated from visual script\nwhile bot.is_running:\n{indented_code}\n    bot.wait(0.05) # Prevent CPU-hogging loops"

    def _generate_code_from_node(self, node_id: str, nodes: dict, adj: dict, visited: set) -> list[str]:
        """Recursively generate code lines for a node and its successors, handling branches."""
        if node_id in visited:
            # A cycle is detected. This represents the end of an iteration path in the main `while` loop.
            # We stop generating code for this path, and the `while bot.is_running` loop will handle the next iteration.
            return []

        # For linear paths, add node to visited. For branches, a copy is made.
        visited.add(node_id)

        node = nodes.get(node_id)
        if not node:
            return [f"# Error: Node with id {node_id} not found."]

        node_type = node["type"]
        params = node.get("params", {})
        generated_code = []

        # --- Code generation logic for each node type ---

        if node_type == "start":
            # Start node simply connects to the next node in the sequence
            if 0 in adj.get(node_id, {}):
                next_node_id = adj[node_id][0]
                generated_code.extend(self._generate_code_from_node(next_node_id, nodes, adj, visited))

        elif node_type == "find_click_color":
            # This node type has conditional logic (Success/Failure)
            mods = f", modifiers={params.get('modifiers', [])}" if params.get("modifiers") else ""
            find_call = (f"bot.find_and_click_color(hex_color='{params['hex_color']}', "
                         f"region_index={params['region_index']}, tolerance={params['tolerance']}, "
                         f"button='{params['button']}', background={params['background']}{mods})")

            generated_code.append(f"if {find_call}:")
            # Success branch (output port 0)
            if 0 in adj.get(node_id, {}):
                next_node_id = adj[node_id][0]
                # Pass a copy of visited set to allow separate branches to merge later
                success_code = self._generate_code_from_node(next_node_id, nodes, adj, visited.copy())
                generated_code.extend([f"    {line}" for line in success_code] if success_code else ["    pass"])
            else:
                generated_code.append("    pass")

            # Failure branch (output port 1)
            if 1 in adj.get(node_id, {}):
                generated_code.append("else:")
                next_node_id = adj[node_id][1]
                failure_code = self._generate_code_from_node(next_node_id, nodes, adj, visited.copy())
                generated_code.extend([f"    {line}" for line in failure_code] if failure_code else ["    pass"])

        elif node_type == "click_region":
            mods = f", modifiers={params.get('modifiers', [])}" if params.get("modifiers") else ""
            generated_code.append(f"bot.click_region(region_index={params['region_index']}, button='{params['button']}', background={params['background']}{mods})")
            if 0 in adj.get(node_id, {}):
                next_node_id = adj[node_id][0]
                generated_code.extend(self._generate_code_from_node(next_node_id, nodes, adj, visited))

        elif node_type == "wait":
            generated_code.append(f"bot.wait({params.get('seconds', 1.0)})")
            if 0 in adj.get(node_id, {}):
                next_node_id = adj[node_id][0]
                generated_code.extend(self._generate_code_from_node(next_node_id, nodes, adj, visited))

        elif node_type == "log":
            message = params.get('message', '').replace("'", "\\'") # basic escaping
            generated_code.append(f"bot.log('{message}')")
            if 0 in adj.get(node_id, {}):
                next_node_id = adj[node_id][0]
                generated_code.extend(self._generate_code_from_node(next_node_id, nodes, adj, visited))

        # Other node types would be added here...

        return generated_code

    def _execute_visual_script(self, visual_script):
        python_code = self._visual_script_to_code(visual_script)
        self._execute(python_code)

    def run_script(self, script_code=None, visual_script=None):
        if self.is_running():
            self.log("Script execution requested, but a script is already running.")
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