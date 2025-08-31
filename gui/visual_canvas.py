"""Visual scripting canvas widget.

Lightweight extraction of node-editor functionality that was previously in
`colorbot_defs.bak`.  It can be embedded inside a parent frame and provides:

* scrollable `Canvas` for drawing nodes and connections
* helpers to create nodes (start, find_click_color, click_region, wait, random_wait)
* basic drag-and-drop of nodes and connection drawing

It is NOT yet wired to the remainder of the GUI; the main `ColorBotGUI` should
instantiate `VisualCanvas` and expose `self.regions` for region-aware node
labels.
"""

from __future__ import annotations

import tkinter as tk
from typing import Any, Dict, List, Optional, Tuple


class VisualCanvas(tk.Frame):
    """Scrollable Tkinter canvas that hosts visual-scripting nodes."""

    def __init__(self, master: tk.Misc, gui_owner: Any):
        super().__init__(master, bg="#34495e")
        self.gui = gui_owner  # main ColorBotGUI instance (for regions access)

        # Scrollable canvas setup
        self.visual_canvas = tk.Canvas(
            self,
            bg="#34495e",
            highlightthickness=0,
            scrollregion=(0, 0, 2000, 2000),  # generous virtual area
        )
        h_scroll = tk.Scrollbar(self, orient="horizontal", command=self.visual_canvas.xview)
        v_scroll = tk.Scrollbar(self, orient="vertical", command=self.visual_canvas.yview)
        self.visual_canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)

        self.visual_canvas.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # Node state
        self.nodes: List[Dict[str, Any]] = []
        self.connections: List[Dict[str, Any]] = []
        self.node_counter: int = 0
        self.selected_node: Optional[Dict[str, Any]] = None
        self.selected_connection: Optional[Dict[str, Any]] = None
        self.drag_data: Dict[str, Any] = {"item": None, "x": 0, "y": 0}
        self.connection_start: Optional[Tuple[Any, str, int]] = None  # (node, "input"|"output", idx)

        self.setup_visual_canvas_events()
        self.create_start_node()

    # ------------------------------------------------------------------
    # Event setup / bindings
    # ------------------------------------------------------------------

    def setup_visual_canvas_events(self):
        """Bind mouse/keyboard events for node manipulation."""
        vc = self.visual_canvas
        vc.bind("<ButtonPress-1>", self.on_canvas_click)
        vc.bind("<B1-Motion>", self.on_canvas_drag)
        vc.bind("<ButtonRelease-1>", self.on_canvas_release)
        vc.bind("<Double-Button-1>", self.on_node_double_click)
        vc.bind("<Button-3>", self.show_node_context_menu)
        vc.bind_all("<Delete>", self.delete_selected_node)
        vc.bind_all("<BackSpace>", self.delete_selected_node)

        vc.bind("<Configure>", self.on_canvas_configure)

    # ------------------------------------------------------------------
    # Node creation helpers
    # ------------------------------------------------------------------

    def create_start_node(self):
        """Create the mandatory start node."""
        node = {
            "id": "start",
            "type": "start",
            "x": 50,
            "y": 50,
            "width": 120,
            "height": 40,
            "inputs": [],
            "outputs": [{"name": "next", "x": 110, "y": 20}],
            "params": {},
        }
        self.draw_node(node)
        self.nodes.append(node)
        return node

    def create_node(self, node_type: str, x: int, y: int, **params):
        """Factory for different node types."""
        self.node_counter += 1
        node_id = f"{node_type.lower()}_{self.node_counter}"

        # Define defaults per node type (subset of original set)
        if node_type == "Find & Click Color":
            node = {
                "id": node_id,
                "type": "find_click_color",
                "x": x,
                "y": y,
                "width": 200,
                "height": 100,
                "inputs": [{"name": "prev", "x": 0, "y": 20}],
                "outputs": [{"name": "next", "x": 200, "y": 20}],
                "params": {
                    "region_index": params.get("region_index", 0),
                    "hex_color": params.get("hex_color", "#FF0000"),
                    "tolerance": params.get("tolerance", 10),
                    "button": params.get("button", "left"),
                    "modifiers": params.get("modifiers", []),
                    "background": params.get("background", True),
                },
            }
        elif node_type == "Click Region Center":
            node = {
                "id": node_id,
                "type": "click_region",
                "x": x,
                "y": y,
                "width": 200,
                "height": 80,
                "inputs": [{"name": "prev", "x": 0, "y": 20}],
                "outputs": [{"name": "next", "x": 200, "y": 20}],
                "params": {
                    "region_index": params.get("region_index", 0),
                    "button": params.get("button", "left"),
                    "modifiers": params.get("modifiers", []),
                    "background": params.get("background", True),
                },
            }
        elif node_type == "Wait":
            node = {
                "id": node_id,
                "type": "wait",
                "x": x,
                "y": y,
                "width": 180,
                "height": 60,
                "inputs": [{"name": "prev", "x": 0, "y": 20}],
                "outputs": [{"name": "next", "x": 180, "y": 20}],
                "params": {"seconds": params.get("seconds", 1.0)},
            }
        else:
            raise ValueError(f"Unknown node_type '{node_type}'")

        self.draw_node(node)
        self.nodes.append(node)
        return node

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------

    def draw_node(self, node: Dict[str, Any]):
        """Draw rectangular node with title and param labels."""
        vc = self.visual_canvas
        fill_color = "#3498db" if node["type"] != "start" else "#2ecc71"

        # Node background and title
        node["graphics"] = {
            "bg": vc.create_rectangle(
                node["x"], node["y"], node["x"] + node["width"], node["y"] + node["height"],
                fill=fill_color, outline="#ecf0f1", width=2,
            ),
            "title": vc.create_text(
                node["x"] + node["width"] // 2,
                node["y"] + 15,
                text=node["type"].replace("_", " ").title(),
                fill="#ecf0f1", font=("Arial", 10, "bold"),
            ),
        }

        # IO points
        node["graphics"]["inputs"] = []
        for i, inp in enumerate(node["inputs"]):
            x_pt = node["x"] + inp["x"]
            y_pt = node["y"] + inp["y"]
            node["graphics"]["inputs"].append(
                vc.create_oval(x_pt - 5, y_pt - 5, x_pt + 5, y_pt + 5, fill="#2ecc71", outline="#ecf0f1")
            )

        node["graphics"]["outputs"] = []
        for i, out in enumerate(node["outputs"]):
            x_pt = node["x"] + out["x"]
            y_pt = node["y"] + out["y"]
            node["graphics"]["outputs"].append(
                vc.create_oval(x_pt - 5, y_pt - 5, x_pt + 5, y_pt + 5, fill="#e74c3c", outline="#ecf0f1")
            )

        # Quick param text (one per line)
        y_offset = 35
        if node["type"] != "start":
            for key, value in node["params"].items():
                vc.create_text(
                    node["x"] + 10,
                    node["y"] + y_offset,
                    text=f"{key.replace('_', ' ').title()}: {value}",
                    fill="#ecf0f1",
                    anchor="w",
                    font=("Arial", 8),
                )
                y_offset += 12

    # ------------------------------------------------------------------
    # Canvas event handlers (simplified)
    # ------------------------------------------------------------------

    def on_canvas_click(self, event):
        x = self.visual_canvas.canvasx(event.x)
        y = self.visual_canvas.canvasy(event.y)

        # Hit test nodes
        for node in self.nodes:
            if node["x"] <= x <= node["x"] + node["width"] and node["y"] <= y <= node["y"] + node["height"]:
                self.selected_node = node
                self.drag_data["item"] = node["graphics"]["bg"]
                self.drag_data["x"] = x - node["x"]
                self.drag_data["y"] = y - node["y"]
                return

        # empty click clears selection
        self.selected_node = None
        self.drag_data["item"] = None

    def on_canvas_drag(self, event):
        if self.drag_data["item"] and self.selected_node:
            x = self.visual_canvas.canvasx(event.x) - self.drag_data["x"]
            y = self.visual_canvas.canvasy(event.y) - self.drag_data["y"]
            self._move_node(self.selected_node, x, y)

    def on_canvas_release(self, _event):
        self.drag_data["item"] = None

    def _move_node(self, node: Dict[str, Any], new_x: int, new_y: int):
        # Update stored coords
        node["x"], node["y"] = new_x, new_y
        vc = self.visual_canvas
        vc.coords(node["graphics"]["bg"], new_x, new_y, new_x + node["width"], new_y + node["height"])
        vc.coords(node["graphics"]["title"], new_x + node["width"] // 2, new_y + 15)
        for idx, inp in enumerate(node["inputs"]):
            x_pt = new_x + inp["x"]
            y_pt = new_y + inp["y"]
            vc.coords(node["graphics"]["inputs"][idx], x_pt - 5, y_pt - 5, x_pt + 5, y_pt + 5)
        for idx, out in enumerate(node["outputs"]):
            x_pt = new_x + out["x"]
            y_pt = new_y + out["y"]
            vc.coords(node["graphics"]["outputs"][idx], x_pt - 5, y_pt - 5, x_pt + 5, y_pt + 5)

    # Placeholder stubs for un-ported features
    def on_node_double_click(self, _event):
        pass

    def show_node_context_menu(self, _event):
        pass

    def delete_selected_node(self, _event=None):
        if self.selected_node:
            # Remove graphics
            for item in self.selected_node["graphics"].values():
                if isinstance(item, list):
                    for sub in item:
                        self.visual_canvas.delete(sub)
                else:
                    self.visual_canvas.delete(item)
            self.nodes.remove(self.selected_node)
            self.selected_node = None

    # Maintain scrollregion automatically
    def on_canvas_configure(self, _event):
        self.visual_canvas.configure(scrollregion=self.visual_canvas.bbox("all"))


__all__ = ["VisualCanvas"]
