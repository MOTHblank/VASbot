import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import copy

from .visual_canvas import VisualCanvas

class VisualEditorWindow(tk.Toplevel):
    def __init__(self, master, gui_owner):
        super().__init__(master)
        self.gui = gui_owner

        self.title("Visual Script Editor")
        self.geometry("800x600")
        self.configure(bg="#34495e")

        # Set self.gui.visual_canvas and window so other parts of the app can find it
        self.gui.visual_editor_window = self

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        top_frame = tk.Frame(self, bg="#34495e")
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(top_frame, text="🧩 Visual Script Canvas", font=('Arial',12,'bold'), fg='#ecf0f1', bg='#34495e').pack(side=tk.LEFT)

        button_frame = tk.Frame(top_frame, bg="#34495e")
        button_frame.pack(side=tk.RIGHT)

        self.run_button = tk.Button(button_frame, text="▶️ Run", command=self.run_visual_script, bg='#27ae60', fg='white', font=('Arial',9,'bold'))
        self.run_button.pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="💾 Save", command=self.save_visual_script, bg='#27ae60', fg='white', font=('Arial',9,'bold')).pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="📂 Load", command=self.load_visual_script, bg='#f39c12', fg='white', font=('Arial',9,'bold')).pack(side=tk.LEFT, padx=2)

        canvas_frame = tk.Frame(self, bg="#34495e")
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.visual_canvas = VisualCanvas(canvas_frame, self.gui)
        self.visual_canvas.pack(fill=tk.BOTH, expand=True)

        # Set the canvas on the main GUI object
        self.gui.visual_canvas = self.visual_canvas

    def on_close(self):
        # Clean up references on the main GUI object
        self.gui.visual_editor_window = None
        self.gui.visual_canvas = None
        self.destroy()

    def run_visual_script(self):
        if not self.gui._start_script_run():
            return
        if not self.visual_canvas or not self.visual_canvas.nodes:
            messagebox.showwarning("Warning", "Visual script is empty.", parent=self)
            self.gui._on_script_finished_ui() # Reset UI state
            return

        # Disable run button in this window
        self.run_button.config(state=tk.DISABLED)

        visual_script = {
            "nodes": self.visual_canvas.nodes,
            "connections": self.visual_canvas.connections,
        }
        self.gui.script_runner.run_script(visual_script=visual_script)

    def save_visual_script(self):
        if not self.visual_canvas or not self.visual_canvas.nodes:
            messagebox.showwarning("Warning", "Visual script is empty.", parent=self)
            return
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Visual Script JSON", "*.json")],
            title="Save Visual Script",
            parent=self
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
                self.gui.status_var.set(f"💾 Visual script saved: {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save visual script: {e}", parent=self)

    def load_visual_script(self):
        filename = filedialog.askopenfilename(
            filetypes=[("Visual Scripts", "*.json")],
            parent=self
        )
        if not filename:
            return
        try:
            with open(filename, 'r') as f:
                visual_script = json.load(f)
            if hasattr(self.visual_canvas, 'load_from_dict'):
                self.visual_canvas.load_from_dict(visual_script)
                self.gui.status_var.set(f"📂 Visual script loaded: {os.path.basename(filename)}")
            else:
                messagebox.showerror("Error", "Visual canvas does not support loading scripts.", parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load visual script: {e}\n\n{e}", parent=self)
