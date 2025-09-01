import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser, scrolledtext
import threading
import time
import os
import ctypes
from ctypes import wintypes
import json
import copy

from PIL import Image, ImageTk
import numpy as np

try:
    import win32gui, win32con
except ImportError:
    win32gui = win32con = None

import pyautogui

from core.script_runner import ScriptRunner
from utils.windows_utils import _get_true_hwnd_rect
from gui.visual_canvas import VisualCanvas


class ColorBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("2009scape Color Bot - High-Precision Automation v2.1")
        self.root.geometry("1600x900")
        self.root.configure(bg='#2c3e50')
        if not self.check_dependencies():
            return
        self.selected_window = None
        self.captured_image = None
        self.regions = []
        self.start_pos = None
        self.current_color = "#FF0000"
        self.selection_mode = False
        self.eyedropper_mode = False
        self.zoom_level = 1.0
        self.min_zoom = 1.0
        self.max_zoom = 20.0
        self.view_rect = [0, 0, 0, 0]
        self.panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.pan_start_view_x = 0
        self.pan_start_view_y = 0
        self.display_x = self.display_y = self.display_width = self.display_height = 0
        self.window_offset = (0, 0)
        self.script_runner = ScriptRunner(self)
        self.bounding_active = False
        self.visual_editor_window = None
        self.visual_canvas = None
        self.setup_ui()
        self.load_window_list()
        self.setup_hotkeys()
        self.poll_script_runner_queue()
        
    def setup_hotkeys(self):
        bindings = [('<F5>', self.play_script), ('<F7>', self.stop_script),
                   ('<Control-s>', self.save_code_script), ('<Control-o>', self.load_code_script), ('<Control-r>', self.capture_window)]
        for key, func in bindings:
            self.root.bind(key, lambda e, f=func: f())
        self.root.focus_set()
        
    def check_dependencies(self):
        missing = [lib for lib,var in [("pyautogui",pyautogui),("pywin32",win32gui),("numpy",np)] if var is None]
        if missing: messagebox.showerror("Missing Dependencies", f"Missing: {', '.join(missing)}"); self.root.quit(); return False
        return True
        
    def setup_ui(self):
        main = tk.Frame(self.root, bg='#2c3e50'); main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.create_title_section(main); self.create_window_section(main)
        content = tk.Frame(main, bg='#2c3e50'); content.pack(fill=tk.BOTH, expand=True, pady=10)
        self.create_capture_panel(content); self.create_scripting_panel(content); self.create_player_section(main)
        
    def create_title_section(self, parent):
        frame = tk.Frame(parent, bg='#34495e', relief=tk.RAISED, bd=2); frame.pack(fill=tk.X, pady=5)
        tk.Label(frame, text="🎮 2009scape Color Bot v2.1", font=('Arial',24,'bold'), fg='#ecf0f1', bg='#34495e').pack(pady=10)
        tk.Label(frame, text="High-Precision Automation with Background & Foreground Input + Region Management", font=('Arial',12), fg='#bdc3c7', bg='#34495e').pack()
        tk.Label(frame, text="🔥 Hotkeys: F5=Run | F7=Stop | Ctrl+S=Save | Ctrl+O=Load | Ctrl+R=Capture", font=('Arial',9), fg='#f39c12', bg='#34495e').pack(pady=(0,10))
        
    def create_window_section(self, parent):
        frame = tk.Frame(parent, bg='#34495e', relief=tk.RAISED, bd=2); frame.pack(fill=tk.X, pady=5)
        left = tk.Frame(frame, bg='#34495e'); left.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=15, pady=15)
        tk.Label(left, text="🎯 Target Window:", font=('Arial',12,'bold'), fg='#ecf0f1', bg='#34495e').pack(anchor=tk.W)
        self.window_var = tk.StringVar(); self.window_combo = ttk.Combobox(left, textvariable=self.window_var, width=50, font=('Arial',10)); self.window_combo.pack(fill=tk.X, pady=5)
        btns = tk.Frame(left, bg='#34495e'); btns.pack(fill=tk.X, pady=5)
        buttons = [("🔄 Refresh", self.load_window_list, '#3498db'), ("📷 Capture", self.capture_window, '#e74c3c'), ("🔍 Test Click", self.test_click_accuracy, '#9b59b6'), ("ℹ️ Window Info", self.show_window_info, '#34495e')]
        for text, cmd, color in buttons:
            tk.Button(btns, text=text, command=cmd, bg=color, fg='white', font=('Arial',10,'bold'), padx=15).pack(side=tk.LEFT, padx=5)
        right = tk.Frame(frame, bg='#34495e'); right.pack(side=tk.RIGHT, padx=15, pady=15)
        tk.Label(right, text="🗂️ Region & Script Management:", font=('Arial',12,'bold'), fg='#ecf0f1', bg='#34495e').pack(anchor=tk.W)
        mgmt_buttons = [
            [("💾 Save Code Script", self.save_code_script, '#27ae60'), ("📂 Load Code Script", self.load_code_script, '#f39c12')],
            [("📤 Save Regions", self.save_regions, '#8e44ad'), ("📥 Load Regions", self.load_regions, '#e67e22')],
            [("🔗 Embed Regions", self.embed_regions_in_script, '#16a085')]
        ]
        for row in mgmt_buttons:
            frow = tk.Frame(right, bg='#34495e'); frow.pack(pady=2, fill=tk.X)
            for text, cmd, color in row:
                width = 25 if len(row) == 1 else 12
                tk.Button(frow, text=text, command=cmd, bg=color, fg='white', font=('Arial',9,'bold'), width=width).pack(side=tk.LEFT, padx=1)
                
    def test_click_accuracy(self):
        if not self.selected_window or not self.regions:
            messagebox.showwarning("Warning", "Please capture a window and create regions first!")
            return
        if messagebox.askyesno("Test Click Accuracy", "This will perform test clicks on all your regions.\nMake sure the target window is visible!\nContinue?"):
            threading.Thread(target=self._perform_test_clicks, daemon=True).start()
            
    def is_window_maximized(self, hwnd):
        try:
            if win32gui:
                return bool(win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE) & win32con.WS_MAXIMIZE)
        except:
            pass
        return False
        
    def _perform_test_clicks(self):
        self.status_var.set("🔍 Testing click accuracy...")
        for i, region in enumerate(self.regions):
            test_api = getattr(self.script_runner, 'bot_api', None)
            if not test_api:
                from bot_api import BotAPI
                test_api = BotAPI(self)
            test_api.click_region(i, background=True)
            time.sleep(1.0)
        self.status_var.set("✅ Click accuracy test completed!")
        
    def create_capture_panel(self, parent):
        frame = tk.Frame(parent, bg='#34495e', relief=tk.RAISED, bd=2); frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        tk.Label(frame, text="🖥️ Screen Capture & Tools", font=('Arial',16,'bold'), fg='#ecf0f1', bg='#34495e').pack(padx=15, pady=15)
        ctrls = tk.Frame(frame, bg='#34495e'); ctrls.pack(fill=tk.X, padx=15, pady=5)
        ctrl_buttons = [("🎯 Select Region", self.toggle_selection_mode, '#9b59b6'), ("🎨 Color", self.choose_color, self.current_color), ("💧 Eyedropper", self.toggle_eyedropper_mode, '#1abc9c'), ("🔍 Reset Zoom", self.reset_zoom, '#f1c40f'), ("🧹 Clear Regions", self.clear_regions, '#e67e22')]
        for text, cmd, color in ctrl_buttons:
            if text == "🎨 Color":
                self.color_button = tk.Button(ctrls, text=text, command=cmd, bg=color, fg='white', font=('Arial',10,'bold'), padx=10)
                self.color_button.pack(side=tk.LEFT, padx=3)
            else:
                tk.Button(ctrls, text=text, command=cmd, bg=color, fg='white', font=('Arial',10,'bold'), padx=10).pack(side=tk.LEFT, padx=3)
        tol_frame = tk.Frame(ctrls, bg='#34495e'); tol_frame.pack(side=tk.LEFT, padx=10)
        tk.Label(tol_frame, text="Tolerance:", fg='#ecf0f1', bg='#34495e', font=('Arial',9)).pack(side=tk.LEFT)
        self.tolerance_var = tk.StringVar(value="10")
        tk.Entry(tol_frame, textvariable=self.tolerance_var, width=5, font=('Arial',9)).pack(side=tk.LEFT, padx=2)
        cv_cont = tk.Frame(frame, bg='#34495e'); cv_cont.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        self.canvas = tk.Canvas(cv_cont, bg='black', cursor='arrow', highlightthickness=2, highlightbackground='#3498db'); self.canvas.pack(fill=tk.BOTH, expand=True)
        canvas_events = [("<Configure>", self.on_canvas_configure), ("<Button-1>", self.start_selection), ("<B1-Motion>", self.update_selection), ("<ButtonRelease-1>", self.end_selection), ("<MouseWheel>", self.on_mouse_wheel), ("<Button-4>", self.on_mouse_wheel), ("<Button-5>", self.on_mouse_wheel), ("<ButtonPress-2>", self.start_pan), ("<B2-Motion>", self.do_pan), ("<ButtonRelease-2>", self.end_pan), ("<Double-Button-1>", self.reset_zoom), ("<Motion>", self.on_canvas_motion)]
        for event, handler in canvas_events:
            self.canvas.bind(event, handler)
            
    def create_scripting_panel(self, parent):
        rframe = tk.Frame(parent, bg='#34495e', relief=tk.RAISED, bd=2, width=550); rframe.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5); rframe.pack_propagate(False)
        bframe = tk.Frame(rframe, bg='#34495e'); bframe.pack(fill=tk.X, padx=15, pady=15)
        tk.Label(bframe, text="🛠️ Action Builder", font=('Arial',16,'bold'), fg='#ecf0f1', bg='#34495e').pack(anchor=tk.W, pady=(0,10))
        r1 = tk.Frame(bframe, bg='#34495e'); r1.pack(fill=tk.X)
        tk.Label(r1, text="Action:", fg='#ecf0f1', bg='#34495e').pack(side=tk.LEFT)
        self.action_var = tk.StringVar(value="Find & Click Color")
        action_combo = ttk.Combobox(r1, textvariable=self.action_var, values=["Find & Click Color","Click Region Center","Wait","Random Wait", "Log"], state="readonly", width=20)
        action_combo.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        tk.Label(r1, text="Target:", fg='#ecf0f1', bg='#34495e').pack(side=tk.LEFT)
        self.region_var = tk.StringVar(); self.region_combo = ttk.Combobox(r1, textvariable=self.region_var, state="readonly", width=15); self.region_combo.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        r2 = tk.Frame(bframe, bg='#34495e'); r2.pack(fill=tk.X, pady=5)
        controls = [("Button:", "button_var", "Left", ["Left","Right","Middle"], 8), ("Wait (s):", "wait_var", "1.0", None, 8)]
        for label, var_name, default, values, width in controls:
            tk.Label(r2, text=label, fg='#ecf0f1', bg='#34495e').pack(side=tk.LEFT)
            setattr(self, var_name, tk.StringVar(value=default))
            if values:
                ttk.Combobox(r2, textvariable=getattr(self, var_name), values=values, state="readonly", width=width).pack(side=tk.LEFT, padx=5)
            else:
                tk.Entry(r2, textvariable=getattr(self, var_name), width=width).pack(side=tk.LEFT, padx=5)
        self.shift_var = tk.BooleanVar(); tk.Checkbutton(r2, text="Shift", variable=self.shift_var, fg='#ecf0f1', bg='#34495e', selectcolor='#34495e').pack(side=tk.LEFT, padx=5)
        self.ctrl_var = tk.BooleanVar(); tk.Checkbutton(r2, text="Ctrl", variable=self.ctrl_var, fg='#ecf0f1', bg='#34495e', selectcolor='#34495e').pack(side=tk.LEFT, padx=5)
        r3 = tk.Frame(bframe, bg='#34495e'); r3.pack(fill=tk.X, pady=5)
        tk.Button(r3, text="➕ Add to Script", command=self.add_action_to_script, bg='#2ecc71', fg='white', font=('Arial',10,'bold')).pack(side=tk.LEFT, expand=True, fill=tk.X, ipady=5, padx=(0,2))
        tk.Button(r3, text="🧩 Add Node", command=self.add_node_to_visual, bg='#2980b9', fg='white', font=('Arial',10,'bold')).pack(side=tk.LEFT, expand=True, fill=tk.X, ipady=5, padx=(2,2))
        tk.Button(r3, text="👁️ Open Visual Editor", command=self.open_visual_editor_window, bg='#8e44ad', fg='white', font=('Arial',10,'bold')).pack(side=tk.LEFT, expand=True, fill=tk.X, ipady=5, padx=(2,0))

        # --- Code Editor and Console ---
        code_pane = tk.PanedWindow(rframe, orient=tk.VERTICAL, sashrelief=tk.RAISED, bg='#34495e')
        code_pane.pack(fill=tk.BOTH, expand=True, padx=15, pady=(10,15))

        eframe = tk.Frame(code_pane, bg='#34495e'); ehdr = tk.Frame(eframe, bg='#34495e'); ehdr.pack(fill=tk.X)
        tk.Label(ehdr, text="📝 Script Editor", font=('Arial',12,'bold'), fg='#ecf0f1', bg='#34495e').pack(side=tk.LEFT)
        tk.Button(ehdr, text=">>", font=('Consolas',8), command=self.indent_selection, width=4).pack(side=tk.RIGHT)
        tk.Button(ehdr, text="<<", font=('Consolas',8), command=lambda: self.indent_selection(True), width=4).pack(side=tk.RIGHT)
        self.script_editor = scrolledtext.ScrolledText(eframe, wrap=tk.WORD, height=15, bg='#1c2833', fg='#ecf0f1', insertbackground='white', font=('Consolas',10)); self.script_editor.pack(fill=tk.BOTH, expand=True)
        self.script_editor.insert(tk.END, "# Enhanced Color Bot Script with Region Management\nwhile bot.is_running:\n    bot.wait(1)\n"); code_pane.add(eframe)

        cframe = tk.Frame(code_pane, bg='#34495e'); tk.Label(cframe, text="Output Console", font=('Arial',12,'bold'), fg='#ecf0f1', bg='#34495e').pack(anchor=tk.W)
        self.output_console = scrolledtext.ScrolledText(cframe, wrap=tk.WORD, height=5, state=tk.DISABLED, bg='#1c2833', fg='#aed6f1', font=('Consolas',9)); self.output_console.pack(fill=tk.BOTH, expand=True); code_pane.add(cframe)

        # initial pane size adjustments
        self.root.update_idletasks()
        if len(code_pane.panes()) >= 2:
            code_pane.sash_place(0, 0, 300)

    def open_visual_editor_window(self):
        if self.visual_editor_window and self.visual_editor_window.winfo_exists():
            self.visual_editor_window.lift()
            return

        self.visual_editor_window = tk.Toplevel(self.root)
        self.visual_editor_window.title("Visual Script Editor")
        self.visual_editor_window.geometry("800x600")
        self.visual_editor_window.configure(bg="#34495e")

        def on_close():
            self.visual_editor_window.destroy()
            self.visual_editor_window = None
            self.visual_canvas = None

        self.visual_editor_window.protocol("WM_DELETE_WINDOW", on_close)

        top_frame = tk.Frame(self.visual_editor_window, bg="#34495e")
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(top_frame, text="🧩 Visual Script Canvas", font=('Arial',12,'bold'), fg='#ecf0f1', bg='#34495e').pack(side=tk.LEFT)
        
        button_frame = tk.Frame(top_frame, bg="#34495e")
        button_frame.pack(side=tk.RIGHT)

        tk.Button(button_frame, text="▶️ Run", command=self.run_visual_script, bg='#27ae60', fg='white', font=('Arial',9,'bold')).pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="💾 Save", command=self.save_visual_script, bg='#27ae60', fg='white', font=('Arial',9,'bold')).pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="📂 Load", command=self.load_visual_script, bg='#f39c12', fg='white', font=('Arial',9,'bold')).pack(side=tk.LEFT, padx=2)

        canvas_frame = tk.Frame(self.visual_editor_window, bg="#34495e")
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.visual_canvas = VisualCanvas(canvas_frame, self)
        self.visual_canvas.pack(fill=tk.BOTH, expand=True)

    def save_visual_script(self):
        pass # To be implemented

    def load_visual_script(self):
        pass # To be implemented

    def create_player_section(self, parent):
        frame = tk.Frame(parent, bg='#34495e', relief=tk.RAISED, bd=2); frame.pack(fill=tk.X, pady=5)
        tk.Label(frame, text="▶️ Script Player", font=('Arial',16,'bold'), fg='#ecf0f1', bg='#34495e').pack(pady=(15,10))
        ctrls = tk.Frame(frame, bg='#34495e'); ctrls.pack(pady=10)
        player_buttons = [("▶️ Run (F5)", self.play_script, '#27ae60', 12), ("⏹️ Stop (F7)", self.stop_script, '#e74c3c', 12)]
        for i, (text, cmd, color, width) in enumerate(player_buttons):
            btn = tk.Button(ctrls, text=text, command=cmd, bg=color, fg='white', font=('Arial',12,'bold'), width=width, padx=5)
            btn.pack(side=tk.LEFT, padx=5)
            if i == 0:
                self.play_button = btn
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(frame, textvariable=self.status_var, fg='#ecf0f1', bg='#34495e', font=('Arial',12)).pack(fill=tk.X, pady=5)
        
    def save_regions(self):
        if not self.regions:
            messagebox.showwarning("Warning", "No regions to save!")
            return
        filename = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")], title="Save Regions")
        if filename:
            try:
                data = {'regions': self.regions, 'window_title': self.window_var.get(), 'image_size': [self.captured_image.width, self.captured_image.height] if self.captured_image else None, 'created_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'version': '2.1'}
                with open(filename, 'w') as f: json.dump(data, f, indent=2)
                self.status_var.set(f"📤 Regions saved: {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save regions: {e}")
                
    def load_regions(self):
        filename = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")], title="Load Regions")
        if filename:
            try:
                with open(filename, 'r') as f: data = json.load(f)
                if 'regions' not in data:
                    messagebox.showerror("Error", "Invalid regions file format!")
                    return
                if self.captured_image and 'image_size' in data:
                    if data['image_size'] != [self.captured_image.width, self.captured_image.height]:
                        if not messagebox.askyesno("Size Mismatch", f"Saved regions: {data['image_size'][0]}x{data['image_size'][1]}\nCurrent image: {self.captured_image.width}x{self.captured_image.height}\nLoad anyway?"):
                            return
                self.regions = data['regions']
                if self.captured_image: self.draw_regions()
                self.status_var.set(f"📥 Loaded {len(self.regions)} regions")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load regions: {e}")
                
    def embed_regions_in_script(self):
        if not self.regions:
            messagebox.showwarning("Warning", "No regions to embed!")
            return
        code = f"# ============ EMBEDDED REGIONS ============\n# Auto-generated region definitions\n# Created: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        if self.captured_image: code += f"# Image size: {self.captured_image.width}x{self.captured_image.height}\n"
        if self.window_var.get(): code += f"# Window: {self.window_var.get()}\n"
        code += "\nbot.gui.regions = [\n"
        for i, region in enumerate(self.regions):
            code += f"    {{'x': {region['x']}, 'y': {region['y']}, 'width': {region['width']}, 'height': {region['height']}, 'color': '{region['color']}'}},\n"
        code += "]\nbot.gui.update_region_selector()\nbot.log('Loaded embedded regions')\n# ============ END EMBEDDED REGIONS ============\n"
        current = self.script_editor.get("1.0", tk.END)
        lines = current.split('\n')
        insert_pos = next((i for i, line in enumerate(lines) if line.strip().startswith('while ') or (line.strip() and not line.strip().startswith('#'))), 0)
        lines.insert(insert_pos, code)
        self.script_editor.delete("1.0", tk.END)
        self.script_editor.insert(tk.END, '\n'.join(lines))
        self.status_var.set(f"🔗 Embedded {len(self.regions)} regions in script")
        
    def save_code_script(self, event=None):
        code = self.script_editor.get("1.0", tk.END)
        if not code.strip():
            messagebox.showerror("Error", "Script is empty.")
            return
        has_embedded = "# ============ EMBEDDED REGIONS ============" in code
        if self.regions and not has_embedded:
            response = messagebox.askyesnocancel("Include Regions?", f"Embed {len(self.regions)} regions in script?\nYes: Portable script\nNo: Script only\nCancel: Don't save")
            if response is None: return
            elif response: self.embed_regions_in_script(); code = self.script_editor.get("1.0", tk.END)

        filename = filedialog.asksaveasfilename(
            defaultextension=".py",
            filetypes=[("Python Files", "*.py")],
            title="Save Code Script"
        )
        if filename:
            try:
                with open(filename, 'w') as f: f.write(code)
                self.status_var.set(f"💾 Script saved: {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save script: {e}")

    def load_code_script(self, event=None):
        filename = filedialog.askopenfilename(
            filetypes=[("Python Files", "*.py")]
        )
        if not filename:
            return
        try:
            with open(filename, 'r') as f:
                code = f.read()
            has_embedded = "# ============ EMBEDDED REGIONS ============" in code
            self.script_editor.delete("1.0", tk.END)
            self.script_editor.insert(tk.END, code)
            self.status_var.set(f"📂 Script loaded: {os.path.basename(filename)}")
            if has_embedded:
                messagebox.showinfo("Embedded Regions", "Script contains embedded regions that will load when run.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load script: {e}")

    def save_visual_script(self):
        if not self.visual_canvas or not self.visual_canvas.nodes:
            messagebox.showwarning("Warning", "Visual script is empty or not open.")
            return
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Visual Script JSON", "*.json")],
            title="Save Visual Script"
        )
        if filename:
            try:
                nodes_to_save = copy.deepcopy(self.visual_canvas.nodes)
                connections_to_save = copy.deepcopy(self.visual_canvas.connections)
                visual_script = {"nodes": nodes_to_save, "connections": connections_to_save}
                for node in visual_script["nodes"]:
                    node.pop("graphics", None)
                for conn in visual_script["connections"]:
                    conn.pop("graphics", None)
                with open(filename, 'w') as f:
                    json.dump(visual_script, f, indent=2)
                self.status_var.set(f"💾 Visual script saved: {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save visual script: {e}")

    def load_visual_script(self):
        if not self.visual_editor_window or not self.visual_editor_window.winfo_exists():
            self.open_visual_editor_window()

        filename = filedialog.askopenfilename(
            filetypes=[("Visual Scripts", "*.json")]
        )
        if not filename:
            return
        try:
            with open(filename, 'r') as f:
                visual_script = json.load(f)
            if hasattr(self.visual_canvas, 'load_from_dict'):
                self.visual_canvas.load_from_dict(visual_script)
                self.status_var.set(f"📂 Visual script loaded: {os.path.basename(filename)}")
            else:
                messagebox.showerror("Error", "Visual canvas does not support loading scripts.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load visual script: {e}\n\n{e}")
            
    def capture_window(self):
        hwnd_str = self.window_var.get()
        if not hwnd_str: messagebox.showwarning("Warning", "Select a window first!"); return
        try:
            hwnd = int(hwnd_str.split("HWND: ")[-1].rstrip(')'))
        except: messagebox.showerror("Error", "Invalid window format."); return
        try:
            if not win32gui.IsWindow(hwnd): messagebox.showerror("Error", "Window no longer exists."); return
            if not win32gui.IsWindowVisible(hwnd): win32gui.ShowWindow(hwnd, win32con.SW_SHOW); time.sleep(0.5)
            self.root.iconify(); time.sleep(0.5)
            left, top, right, bottom = _get_true_hwnd_rect(hwnd)
            width, height = right - left, bottom - top
            if width <= 0 or height <= 0 or width > 5000 or height > 5000:
                self.root.deiconify(); messagebox.showerror("Error", f"Invalid dimensions: {width}x{height}"); return
            self.window_offset = (left, top)
            self.captured_image = pyautogui.screenshot(region=(left, top, width, height))
            if self.captured_image is None or np.all(np.array(self.captured_image) == 0):
                raise Exception("Screenshot failed or black image")
            self.selected_window = hwnd
            self.root.deiconify()
            self.display_x = self.display_y = 0; self.display_width = self.display_height = 1
            self.reset_zoom()
            if self.regions and not self.validate_regions_for_window():
                if not messagebox.askyesno("Region Validation", "Some regions outside window bounds. Keep anyway?"):
                    self.regions = []; self.update_region_selector()
            self.status_var.set(f"✅ Window captured: {width}x{height}")
        except Exception as e:
            self.root.deiconify(); messagebox.showerror("Capture Error", f"Failed: {e}")
            
    def validate_regions_for_window(self):
        if not self.captured_image or not self.regions: return True
        img_w, img_h = self.captured_image.width, self.captured_image.height
        return all(0 <= r['x'] < img_w and 0 <= r['y'] < img_h and r['x'] + r['width'] <= img_w and r['y'] + r['height'] <= img_h for r in self.regions)
        
    def show_window_info(self):        
        hwnd_str = self.window_var.get()
        if not hwnd_str: messagebox.showwarning("Warning", "No window selected!"); return
        try: hwnd = int(hwnd_str.split("HWND: ")[-1].rstrip(')'))
        except: messagebox.showerror("Error", "Invalid window format."); return
        try:
            title = win32gui.GetWindowText(hwnd) if win32gui.IsWindow(hwnd) else "Invalid"
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE) if win32gui.IsWindow(hwnd) else 0
            is_max = bool(style & win32con.WS_MAXIMIZE)
            win_left, win_top, win_right, win_bottom = win32gui.GetWindowRect(hwnd)
            calc_rect = _get_true_hwnd_rect(hwnd)
            regions_summary = f"{len(self.regions)} regions" if self.regions else "No regions"
            info = f"""Window: {title}
HWND: {hwnd}
Maximized: {is_max}
Window Rect: ({win_left}, {win_top}) - ({win_right}, {win_bottom})
Calculated: ({calc_rect[0]}, {calc_rect[1]}) - ({calc_rect[2]}, {calc_rect[3]})
Regions: {regions_summary}"""
            dialog = tk.Toplevel(self.root); dialog.title("Window Info"); dialog.geometry("500x300")
            text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, font=('Consolas', 10))
            text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text.insert(tk.END, info); text.config(state=tk.DISABLED)
            tk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)
        except Exception as e: messagebox.showerror("Error", f"Failed to get window info: {e}")
        
    def add_node_to_visual(self):
        """Create a node on the visual canvas based on current Action Builder fields."""
        self.status_var.set("Attempting to add node...")
        if not hasattr(self, 'visual_canvas'):
            self.status_var.set("Error: Visual canvas not found!")
            return

        action = self.action_var.get()
        self.status_var.set(f"Action selected: {action}")

        region_index = 0
        try:
            region_str = self.region_var.get()
            if region_str and ' ' in region_str:
                region_index = int(region_str.split(' ')[1])
                self.status_var.set(f"Region parsed: {region_index}")
            elif region_str:
                region_index = int(region_str)
                self.status_var.set(f"Region parsed as int: {region_index}")
            else:
                self.status_var.set("No region selected, using index 0.")
                region_index = 0
        except (ValueError, IndexError) as e:
            region_index = 0
            self.status_var.set(f"⚠️ Invalid region format. Using index 0. Error: {e}")

        params = {}
        try:
            if action == "Find & Click Color":
                params = {
                    "region_index": region_index,
                    "hex_color": self.current_color,
                    "tolerance": int(self.tolerance_var.get() or 10),
                    "button": self.button_var.get().lower(),
                    "modifiers": [m for m, chk in [("shift", self.shift_var.get()), ("ctrl", self.ctrl_var.get())] if chk]
                }
            elif action == "Click Region Center":
                params = {
                    "region_index": region_index,
                    "button": self.button_var.get().lower(),
                    "modifiers": [m for m, chk in [("shift", self.shift_var.get()), ("ctrl", self.ctrl_var.get())] if chk]
                }
            elif action == "Wait":
                params = {"seconds": float(self.wait_var.get() or 1.0)}
            elif action == "Random Wait":
                params = {"base_seconds": float(self.wait_var.get() or 1.0), "variance_seconds": 0.5}
            elif action == "Log":
                params = {"message": "Your message here"}
            else:
                self.status_var.set(f"Unknown action: {action}")
                return
        except Exception as e:
            self.status_var.set(f"Error preparing node params: {e}")
            return

        self.status_var.set(f"Parameters prepared: {params}")

        # Place new node below last one
        y_pos = 50 + 120 * len(self.visual_canvas.nodes)
        self.status_var.set(f"Creating node '{action}' at (50, {y_pos})")

        try:
            self.visual_canvas.create_node(action, 50, y_pos, **params)
            self.status_var.set(f"✅ Node added: {action}")
        except Exception as e:
            self.status_var.set(f"Error creating node on canvas: {e}")

    def add_action_to_script(self):
        action, region = self.action_var.get(), self.region_var.get()
        button, use_shift, use_ctrl = self.button_var.get().lower(), self.shift_var.get(), self.ctrl_var.get()
        args = []
        if action in ["Find & Click Color", "Click Region Center"]:
            if not region:
                messagebox.showerror("Error", "Select a region.")
                return
            try:
                args.append(f"region_index={int(region.split(' ')[1])}")
            except (ValueError, IndexError):
                messagebox.showerror("Error", "Invalid region selected.")
                return

        if action == "Find & Click Color":
            args.insert(0, f"hex_color='{self.current_color}'")
            try:
                args.append(f"tolerance={int(self.tolerance_var.get())}")
            except ValueError:
                pass  # Ignore invalid tolerance

        if action in ["Find & Click Color", "Click Region Center"]:
            args.append(f"button='{button}'")
            mods = [f"'{mod}'" for mod, use in [('shift', use_shift), ('ctrl', use_ctrl)] if use]
            if mods:
                args.append(f"modifiers=[{','.join(mods)}]")

        # The 'background' parameter is no longer a user-configurable option.
        # The bot.py functions will use their default behavior.
        if action == "Find & Click Color":
            code = f"if bot.find_and_click_color({', '.join(args)}):\n    bot.wait(0.5)\nelse:\n    bot.log('Color {self.current_color} not found')\n"
        elif action == "Click Region Center":
            code = f"bot.click_region({', '.join(args)})\n"
        elif action == "Wait":
            try: code = f"bot.wait({float(self.wait_var.get())})\n"
            except: messagebox.showerror("Error", "Invalid wait time."); return
        elif action == "Random Wait":
            try: 
                base = float(self.wait_var.get())
                code = f"bot.random_wait({base}, {base * 0.5})\n"
            except: messagebox.showerror("Error", "Invalid wait time."); return
        elif action == "Log":
            # This is a placeholder; a better implementation would have a dedicated entry for the message
            code = "bot.log('User message logged.')\n"
        else: return
        try:
            line = self.script_editor.get("insert linestart", "insert lineend")
            indent = ' ' * (len(line) - len(line.lstrip()))
            self.script_editor.insert(tk.INSERT, indent + code.replace("\n", f"\n{indent}"))
        except: self.script_editor.insert(tk.INSERT, code)
        
    def indent_selection(self, reverse=False):
        try:
            start, end = self.script_editor.tag_ranges("sel")
            for line in range(int(start.string.split('.')[0]), int(end.string.split('.')[0])+1):
                if reverse:
                    if self.script_editor.get(f"{line}.0", f"{line}.4") == "    ": 
                        self.script_editor.delete(f"{line}.0", f"{line}.4")
                else: 
                    self.script_editor.insert(f"{line}.0", "    ")
        except: pass
        
    def update_region_selector(self):
        names = [f"Region {i}" for i in range(len(self.regions))]
        self.region_combo['values'] = names
        self.region_var.set(names[-1] if names else "")
        
    def canvas_to_image_coords(self, cx, cy):
        if not self.captured_image or not hasattr(self, 'display_x') or self.display_width == 0 or self.display_height == 0:
            return 0, 0
        if self.zoom_level <= self.min_zoom:
            rel_x = max(0, min(1, (cx - self.display_x) / self.display_width))
            rel_y = max(0, min(1, (cy - self.display_y) / self.display_height))
            ix, iy = int(rel_x * self.captured_image.width), int(rel_y * self.captured_image.height)
        else:
            if self.display_width == 0 or self.display_height == 0: return 0, 0
            rel_x, rel_y = cx / self.display_width, cy / self.display_height
            vw, vh = self.view_rect[2] - self.view_rect[0], self.view_rect[3] - self.view_rect[1]
            if vw == 0 or vh == 0: return 0, 0
            ix = int(self.view_rect[0] + rel_x * vw)
            iy = int(self.view_rect[1] + rel_y * vh)
        return max(0, min(self.captured_image.width - 1, ix)), max(0, min(self.captured_image.height - 1, iy))
        
    def on_mouse_wheel(self, e):
        if not self.captured_image or not hasattr(self, 'display_x') or self.display_width == 0: return
        factor = 1.1 if (e.num == 4 or e.delta > 0) else 1/1.1
        new_zoom = max(self.min_zoom, min(self.max_zoom, self.zoom_level * factor))
        if new_zoom == self.zoom_level: return
        ix, iy = self.canvas_to_image_coords(e.x, e.y)
        self.zoom_level = new_zoom
        if self.zoom_level > self.min_zoom:
            vw, vh = self.captured_image.width / self.zoom_level, self.captured_image.height / self.zoom_level
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw == 0 or ch == 0: return
            mouse_rel_x, mouse_rel_y = e.x / cw, e.y / ch
            self.view_rect = [ix - mouse_rel_x * vw, iy - mouse_rel_y * vh, 0, 0]
            self.view_rect[2], self.view_rect[3] = self.view_rect[0] + vw, self.view_rect[1] + vh
        self.update_canvas_display()
        
    def start_selection(self, e):
        if not self.captured_image or not hasattr(self, 'display_x') or self.display_width == 0: return
        if self.eyedropper_mode: self.pick_color_at_event(e); return
        if self.selection_mode: self.start_pos = (e.x, e.y)
        
    def end_selection(self, e):
        if not self.start_pos or not self.captured_image or not hasattr(self, 'display_x') or self.display_width == 0: return
        x1i, y1i = self.canvas_to_image_coords(self.start_pos[0], self.start_pos[1])
        x2i, y2i = self.canvas_to_image_coords(e.x, e.y)
        self.start_pos = None; self.canvas.delete("selection")
        x1, y1, x2, y2 = min(x1i, x2i), min(y1i, y2i), max(x1i, x2i), max(y1i, y2i)
        if x2 - x1 > 5 and y2 - y1 > 5: 
            self.regions.append({'x': x1, 'y': y1, 'width': x2 - x1, 'height': y2 - y1, 'color': self.current_color})
            self.draw_regions()
            self.status_var.set(f"✅ Region {len(self.regions)-1} added: ({x1},{y1}) {x2-x1}x{y2-y1}")
            
    def pick_color_at_event(self, e):
        if not self.captured_image or not hasattr(self, 'display_x') or self.display_width == 0: return
        try:
            ix, iy = self.canvas_to_image_coords(e.x, e.y)
            if 0 <= ix < self.captured_image.width and 0 <= iy < self.captured_image.height:
                px = self.captured_image.getpixel((ix, iy))
                self.set_current_color('#{:02x}{:02x}{:02x}'.format(px[0], px[1], px[2]))
                self.status_var.set(f"💧 Color picked: {self.current_color}")
        except Exception as e: pass
        finally: self.toggle_eyedropper_mode(force_off=True)
        
    def on_canvas_motion(self, e):
        if not self.captured_image or not hasattr(self, 'display_x') or self.display_width == 0: return
        try:
            ix, iy = self.canvas_to_image_coords(e.x, e.y)
            if 0 <= ix < self.captured_image.width and 0 <= iy < self.captured_image.height:
                px = self.captured_image.getpixel((ix, iy))
                hex_color = '#{:02x}{:02x}{:02x}'.format(px[0], px[1], px[2])
                self.status_var.set(f"Pixel: ({ix},{iy}) | RGB: {px} | Hex: {hex_color} | Zoom: {self.zoom_level:.1f}x")
        except: pass
        
    def update_canvas_display(self):
        if not self.captured_image: return
        try:
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw <= 1 or ch <= 1: self.root.after(100, self.update_canvas_display); return
            if self.zoom_level <= self.min_zoom:
                img_ratio, canvas_ratio = self.captured_image.width / self.captured_image.height, cw / ch
                if img_ratio > canvas_ratio:
                    self.display_width, self.display_height = cw, int(cw / img_ratio)
                else:
                    self.display_width, self.display_height = int(ch * img_ratio), ch
                self.display_width, self.display_height = max(1, self.display_width), max(1, self.display_height)
                self.display_x, self.display_y = (cw - self.display_width) / 2, (ch - self.display_height) / 2
                resized = self.captured_image.resize((self.display_width, self.display_height), Image.Resampling.LANCZOS)
                self.view_rect = [0, 0, self.captured_image.width, self.captured_image.height]
            else:
                vw, vh = self.captured_image.width / self.zoom_level, self.captured_image.height / self.zoom_level
                self.view_rect[0] = max(0, min(self.view_rect[0], self.captured_image.width - vw))
                self.view_rect[1] = max(0, min(self.view_rect[1], self.captured_image.height - vh))
                self.view_rect[2], self.view_rect[3] = self.view_rect[0] + vw, self.view_rect[1] + vh
                self.display_x = self.display_y = 0
                self.display_width, self.display_height = max(1, cw), max(1, ch)
                crop = tuple(map(int, [max(0, self.view_rect[0]), max(0, self.view_rect[1]), min(self.captured_image.width, self.view_rect[2]), min(self.captured_image.height, self.view_rect[3])]))
                resized = self.captured_image.crop(crop).resize((cw, ch), Image.Resampling.LANCZOS)
            self.canvas_image = ImageTk.PhotoImage(resized)
            self.canvas.delete("all")
            self.canvas.create_image(self.display_x + self.display_width/2, self.display_y + self.display_height/2, image=self.canvas_image)
            self.draw_regions()
        except Exception as e: pass
        
    def image_to_canvas_coords(self, ix, iy):
        if not hasattr(self, 'display_x') or self.display_width == 0 or self.display_height == 0: return 0, 0
        if self.zoom_level <= self.min_zoom:
            rel_x, rel_y = ix / self.captured_image.width, iy / self.captured_image.height
            return self.display_x + rel_x * self.display_width, self.display_y + rel_y * self.display_height
        else:
            vw, vh = self.view_rect[2] - self.view_rect[0], self.view_rect[3] - self.view_rect[1]
            if vw == 0 or vh == 0: return 0, 0
            rel_x, rel_y = (ix - self.view_rect[0]) / vw, (iy - self.view_rect[1]) / vh
            return rel_x * self.display_width, rel_y * self.display_height
            
    def start_pan(self, e):
        if self.zoom_level <= self.min_zoom: return
        self.panning = True
        self.pan_start_x, self.pan_start_y = e.x, e.y
        self.pan_start_view_x, self.pan_start_view_y = self.view_rect[0], self.view_rect[1]
        self.canvas.config(cursor="fleur")
        
    def do_pan(self, e):
        if not self.panning: return
        dx, dy = e.x - self.pan_start_x, e.y - self.pan_start_y
        vw, vh = self.view_rect[2] - self.view_rect[0], self.view_rect[3] - self.view_rect[1]
        self.view_rect[0] = self.pan_start_view_x - dx * (vw / self.canvas.winfo_width())
        self.view_rect[1] = self.pan_start_view_y - dy * (vh / self.canvas.winfo_height())
        self.update_canvas_display()
        
    def end_pan(self, e): 
        self.panning = False
        self.canvas.config(cursor="arrow")
        
    def reset_zoom(self, e=None):
        if self.zoom_level == self.min_zoom: return
        self.zoom_level = self.min_zoom
        self.update_canvas_display()
        self.status_var.set("🔍 Zoom reset.")
        
    def toggle_eyedropper_mode(self, force_off=False):
        if not self.captured_image: messagebox.showwarning("Warning", "Capture a window first!"); return
        if force_off or self.eyedropper_mode: 
            self.eyedropper_mode = False
            self.status_var.set("Eyedropper OFF.")
            self.canvas.config(cursor="arrow")
        else:
            if self.selection_mode: self.toggle_selection_mode(force_off=True)
            self.eyedropper_mode = True
            self.status_var.set("💧 Eyedropper ON - Click to pick color.")
            self.canvas.config(cursor="crosshair")
            
    def toggle_selection_mode(self, force_off=False):
        if not self.captured_image: messagebox.showwarning("Warning", "Capture a window first!"); return
        if force_off or self.selection_mode: 
            self.selection_mode = False
            self.status_var.set("Selection mode OFF.")
            self.canvas.config(cursor="arrow")
        else:
            if self.eyedropper_mode: self.toggle_eyedropper_mode(force_off=True)
            self.selection_mode = True
            self.status_var.set("🎯 Selection mode ON - Click and drag to create region.")
            self.canvas.config(cursor="crosshair")
            
    def bound_mouse_to_window(self):
        if not self.selected_window or self.bounding_active: return
        try:
            left, top, right, bottom = _get_true_hwnd_rect(self.selected_window)
            rect = wintypes.RECT(left, top, right, bottom)
            ctypes.windll.user32.ClipCursor(ctypes.byref(rect))
            self.bounding_active = True
            self.status_var.set("🖱️ Mouse bounded to target window")
        except Exception as e: pass
        
    def release_mouse_bound(self):
        if not self.bounding_active: return
        try:
            ctypes.windll.user32.ClipCursor(None)
            self.bounding_active = False
            self.status_var.set("🖱️ Mouse bound released")
        except: pass
        
    def _start_script_run(self):
        if not self.selected_window:
            messagebox.showwarning("Warning", "Capture a window first.")
            return False
        self.is_playing = True
        self.play_button.config(state=tk.DISABLED)
        # Add logic to disable visual run button if it exists
        self.output_console.config(state=tk.NORMAL)
        self.output_console.delete('1.0', tk.END)
        self.output_console.config(state=tk.DISABLED)
        self.bound_mouse_to_window()
        return True

    def play_script(self):
        if not self._start_script_run():
            return
        code = self.script_editor.get("1.0", tk.END)
        if not code.strip():
            messagebox.showwarning("Warning", "Script is empty.")
            self._on_script_finished_ui() # Reset UI state
            return
        self.script_runner.run_script(script_code=code)

    def run_visual_script(self):
        if not self._start_script_run():
            return
        if not self.visual_canvas or not self.visual_canvas.nodes:
            messagebox.showwarning("Warning", "Visual script is empty or not open.")
            self._on_script_finished_ui() # Reset UI state
            return
        visual_script = {
            "nodes": self.visual_canvas.nodes,
            "connections": self.visual_canvas.connections,
        }
        self.script_runner.run_script(visual_script=visual_script)
            
    def stop_script(self):
        if not hasattr(self, 'is_playing') or not self.is_playing: return
        self.script_runner.stop()
        self.release_mouse_bound()
        self.status_var.set("⏹️ Script stopped by user.")
        self._on_script_finished_ui()
        
    def log_message(self, m): 
        self.root.after(0, self._log_message_ui, m)
        
    def _log_message_ui(self, m):
        self.output_console.config(state=tk.NORMAL)
        self.output_console.insert(tk.END, m + "\n")
        self.output_console.config(state=tk.DISABLED)
        self.output_console.see(tk.END)
        
    def on_script_finished(self): 
        self.root.after(0, self._on_script_finished_ui)
        
    def _on_script_finished_ui(self):
        self.is_playing = False
        self.play_button.config(state=tk.NORMAL)
        self.release_mouse_bound()
        if "stopped" not in self.status_var.get(): 
            self.status_var.set("✅ Script finished. Ready for next run!")
            
    def load_window_list(self):
        if not win32gui: self.status_var.set("Error: win32gui not available"); return
        windows, debug_info = [], []
        def enum_cb(hwnd, w):
            try:
                title = win32gui.GetWindowText(hwnd)
                if title and title.strip() and win32gui.IsWindowVisible(hwnd):
                    w.append((hwnd, title))
            except Exception as e: debug_info.append(f"Error with HWND {hwnd}: {str(e)}")
            return True
        try:
            win32gui.EnumWindows(enum_cb, windows)
            if not windows:
                def enum_minimal(hwnd, w):
                    try:
                        title = win32gui.GetWindowText(hwnd)
                        if title: w.append((hwnd, title))
                    except: pass
                    return True
                win32gui.EnumWindows(enum_minimal, windows)
            windows.sort(key=lambda x: x[1].lower())
            window_strings = [f"{title} (HWND: {hwnd})" for hwnd, title in windows]
            self.window_combo['values'] = window_strings
            if windows:
                self.status_var.set(f"Found {len(windows)} windows.")
                if window_strings: self.window_var.set(window_strings[0])
            else:
                self.status_var.set("No windows found.")
        except Exception as e:
            self.status_var.set(f"Error loading windows: {e}")
            
    def choose_color(self):
        color = colorchooser.askcolor(color=self.current_color)
        if color[1]:
            self.set_current_color(color[1])
            self.status_var.set(f"Color selected: {color[1]}")
            
    def update_selection(self, e):
        if not self.start_pos: return
        self.canvas.delete("selection")
        self.canvas.create_rectangle(self.start_pos[0], self.start_pos[1], e.x, e.y, outline=self.current_color, width=2, tags="selection")
        
    def clear_regions(self):
        if self.regions and not messagebox.askyesno("Confirm Clear", f"Clear all {len(self.regions)} regions?"): return
        self.regions = []
        self.canvas.delete("region")
        self.status_var.set("🧹 All regions cleared.")
        self.update_region_selector()
        
    def on_canvas_configure(self, e):
        if hasattr(self, '_resize_timer'): self.root.after_cancel(self._resize_timer)
        self._resize_timer = self.root.after(100, self.update_canvas_display)
        
    def set_current_color(self, color):
        self.current_color = color
        self.color_button.config(bg=color)
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        self.color_button.config(fg='white' if brightness < 128 else 'black')
        
    def poll_script_runner_queue(self):
        """Periodically check the script runner's message queue for updates."""
        self.script_runner._process_message_queue()
        self.root.after(100, self.poll_script_runner_queue)

    def draw_regions(self):
        self.canvas.delete("region")
        if not hasattr(self, 'display_x'): return
        for i, region in enumerate(self.regions):
            x1, y1 = self.image_to_canvas_coords(region['x'], region['y'])
            x2, y2 = self.image_to_canvas_coords(region['x'] + region['width'], region['y'] + region['height'])
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if x2 > 0 and x1 < cw and y2 > 0 and y1 < ch:
                self.canvas.create_rectangle(x1, y1, x2, y2, outline=region['color'], width=3, tags="region")
                info_text = f"R{i}: {region['width']}x{region['height']}"
                text_bg_width, text_y = len(info_text) * 7, max(y1 - 20, 0)
                self.canvas.create_rectangle(x1, text_y, x1 + text_bg_width, y1, fill='black', outline=region['color'], tags="region")
                self.canvas.create_text(x1 + 2, text_y + 10, text=info_text, anchor='w', fill=region['color'], font=('Arial', 9, 'bold'), tags="region")
        self.update_region_selector()