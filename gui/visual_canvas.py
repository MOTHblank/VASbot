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
        self.connection_line: Optional[int] = None

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
        vc.bind_all("<Delete>", self.delete_selection)
        vc.bind_all("<BackSpace>", self.delete_selection)

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
                "inputs": [{"name": "prev", "x": 0, "y": 50}],
                "outputs": [
                    {"name": "Success", "x": 200, "y": 35},
                    {"name": "Failure", "x": 200, "y": 65},
                ],
                "params": {
                    "region_index": params.get("region_index", 0),
                    "hex_color": params.get("hex_color", "#FF0000"),
                    "tolerance": params.get("tolerance", 10),
                    "button": params.get("button", "left"),
                    "modifiers": params.get("modifiers", []),
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
        elif node_type == "Log":
            node = {
                "id": node_id,
                "type": "log",
                "x": x,
                "y": y,
                "width": 220,
                "height": 60,
                "inputs": [{"name": "prev", "x": 0, "y": 30}],
                "outputs": [{"name": "next", "x": 220, "y": 30}],
                "params": {"message": params.get("message", "Log message")},
            }
        else:
            raise ValueError(f"Unknown node_type '{node_type}'")

        self.draw_node(node)
        self.nodes.append(node)
        self._update_scrollregion()
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
        node["graphics"]["input_labels"] = []
        for i, inp in enumerate(node["inputs"]):
            x_pt = node["x"] + inp["x"]
            y_pt = node["y"] + inp["y"]
            node["graphics"]["inputs"].append(
                vc.create_oval(x_pt - 5, y_pt - 5, x_pt + 5, y_pt + 5, fill="#2ecc71", outline="#ecf0f1")
            )
            if inp.get("name"):
                label_id = vc.create_text(
                    node["x"] + inp["x"] + 10,
                    node["y"] + inp["y"],
                    text=inp["name"],
                    fill="#ecf0f1", anchor="w", font=("Arial", 8),
                )
                node["graphics"]["input_labels"].append(label_id)

        node["graphics"]["outputs"] = []
        node["graphics"]["output_labels"] = []
        for i, out in enumerate(node["outputs"]):
            x_pt = node["x"] + out["x"]
            y_pt = node["y"] + out["y"]
            node["graphics"]["outputs"].append(
                vc.create_oval(x_pt - 5, y_pt - 5, x_pt + 5, y_pt + 5, fill="#e74c3c", outline="#ecf0f1")
            )
            if out.get("name"):
                label_id = vc.create_text(
                    node["x"] + out["x"] - 10,
                    node["y"] + out["y"],
                    text=out["name"],
                    fill="#ecf0f1", anchor="e", font=("Arial", 8),
                )
                node["graphics"]["output_labels"].append(label_id)

        # Quick param text (one per line)
        node["graphics"]["params"] = []
        y_offset = 35
        if node["type"] != "start":
            for key, value in node["params"].items():
                param_text_id = vc.create_text(
                    node["x"] + 10,
                    node["y"] + y_offset,
                    text=f"{key.replace('_', ' ').title()}: {value}",
                    fill="#ecf0f1",
                    anchor="w",
                    font=("Arial", 8),
                )
                node["graphics"]["params"].append(param_text_id)
                y_offset += 12

    def draw_connection(self, conn: Dict[str, Any]):
        """Draw a line representing a connection."""
        vc = self.visual_canvas
        from_node = next((n for n in self.nodes if n["id"] == conn["from_node"]), None)
        to_node = next((n for n in self.nodes if n["id"] == conn["to_node"]), None)
        if not from_node or not to_node:
            return  # one of the nodes was deleted

        x1 = from_node["x"] + from_node["outputs"][conn["from_port"]]["x"]
        y1 = from_node["y"] + from_node["outputs"][conn["from_port"]]["y"]
        x2 = to_node["x"] + to_node["inputs"][conn["to_port"]]["x"]
        y2 = to_node["y"] + to_node["inputs"][conn["to_port"]]["y"]

        conn["graphics"] = vc.create_line(x1, y1, x2, y2, fill="#ecf0f1", width=3)

    # ------------------------------------------------------------------
    # Canvas event handlers (simplified)
    # ------------------------------------------------------------------

    def on_canvas_click(self, event):
        x = self.visual_canvas.canvasx(event.x)
        y = self.visual_canvas.canvasy(event.y)
        self._clear_selection()

        # Hit test I/O points first
        io_hit = self._get_io_point_at(x, y)
        if io_hit:
            node, io_type, io_index = io_hit
            if io_type == "output":
                self.connection_start = (node, io_type, io_index)
                start_x = node["x"] + node["outputs"][io_index]["x"]
                start_y = node["y"] + node["outputs"][io_index]["y"]
                self.connection_line = self.visual_canvas.create_line(
                    start_x, start_y, x, y, fill="#f1c40f", width=2
                )
            return

        # Hit test nodes
        for node in self.nodes:
            if node["x"] <= x <= node["x"] + node["width"] and node["y"] <= y <= node["y"] + node["height"]:
                self.selected_node = node
                self.visual_canvas.itemconfig(node["graphics"]["bg"], outline="#f1c40f")
                self.drag_data["item"] = node["graphics"]["bg"]
                self.drag_data["x"] = x - node["x"]
                self.drag_data["y"] = y - node["y"]
                return

        # Hit test connections
        conn_hit = self._get_connection_at(x, y)
        if conn_hit:
            self.selected_connection = conn_hit
            self.visual_canvas.itemconfig(conn_hit["graphics"], fill="#f1c40f")
            return

        # empty click clears selection
        self.drag_data["item"] = None

    def on_canvas_drag(self, event):
        if self.connection_line:
            x = self.visual_canvas.canvasx(event.x)
            y = self.visual_canvas.canvasy(event.y)
            coords = self.visual_canvas.coords(self.connection_line)
            self.visual_canvas.coords(self.connection_line, coords[0], coords[1], x, y)
            return

        if self.drag_data["item"] and self.selected_node:
            x = self.visual_canvas.canvasx(event.x) - self.drag_data["x"]
            y = self.visual_canvas.canvasy(event.y) - self.drag_data["y"]
            self._move_node(self.selected_node, x, y)

    def on_canvas_release(self, event):
        if self.connection_line:
            self.visual_canvas.delete(self.connection_line)
            self.connection_line = None

            if self.connection_start:
                x = self.visual_canvas.canvasx(event.x)
                y = self.visual_canvas.canvasy(event.y)
                io_hit = self._get_io_point_at(x, y)

                if io_hit:
                    end_node, io_type, end_index = io_hit
                    start_node, _, start_index = self.connection_start
                    if io_type == "input" and end_node["id"] != start_node["id"]:
                        self.create_connection(start_node, start_index, end_node, end_index)

            self.connection_start = None
            return

        self.drag_data["item"] = None

    def _move_node(self, node: Dict[str, Any], new_x: int, new_y: int):
        # Update stored coords
        node["x"], node["y"] = new_x, new_y
        vc = self.visual_canvas

        # Move background and title
        vc.coords(node["graphics"]["bg"], new_x, new_y, new_x + node["width"], new_y + node["height"])
        vc.coords(node["graphics"]["title"], new_x + node["width"] // 2, new_y + 15)

        # Move IO points and their labels
        for i, inp in enumerate(node["inputs"]):
            x_pt, y_pt = new_x + inp["x"], new_y + inp["y"]
            vc.coords(node["graphics"]["inputs"][i], x_pt - 5, y_pt - 5, x_pt + 5, y_pt + 5)
            if i < len(node["graphics"].get("input_labels", [])):
                vc.coords(node["graphics"]["input_labels"][i], x_pt + 10, y_pt)

        for i, out in enumerate(node["outputs"]):
            x_pt, y_pt = new_x + out["x"], new_y + out["y"]
            vc.coords(node["graphics"]["outputs"][i], x_pt - 5, y_pt - 5, x_pt + 5, y_pt + 5)
            if i < len(node["graphics"].get("output_labels", [])):
                vc.coords(node["graphics"]["output_labels"][i], x_pt - 10, y_pt)

        # Move param text
        y_offset = 35
        for i, param_id in enumerate(node["graphics"].get("params", [])):
            vc.coords(param_id, new_x + 10, new_y + y_offset)
            y_offset += 12

        self.update_connections_for_node(node)
        self._update_scrollregion()

    # Placeholder stubs for un-ported features
    def on_node_double_click(self, event):
        x = self.visual_canvas.canvasx(event.x)
        y = self.visual_canvas.canvasy(event.y)
        # Find the node that was double-clicked
        for node in reversed(self.nodes):
            if node["x"] <= x <= node["x"] + node["width"] and node["y"] <= y <= node["y"] + node["height"]:
                if node["type"] != "start":  # Start node has no params to edit
                    self.edit_node_parameters(node)
                return

    def edit_node_parameters(self, node: Dict[str, Any]):
        """Open a dialog to edit a node's parameters."""
        dialog = tk.Toplevel(self)
        dialog.title(f"Edit {node['type'].replace('_', ' ').title()}")
        dialog.configure(bg="#34495e")
        dialog.resizable(False, False)

        entries = {}
        for i, (param, value) in enumerate(node["params"].items()):
            row = tk.Frame(dialog, bg="#34495e")
            row.pack(fill="x", padx=10, pady=5)
            label = tk.Label(row, text=f"{param.replace('_', ' ').title()}:", fg="#ecf0f1", bg="#34495e", width=15, anchor="w")
            label.pack(side="left")

            entry = tk.Entry(row, bg="#2c3e50", fg="#ecf0f1", insertbackground="white")
            entry.pack(side="left", fill="x", expand=True)
            entry.insert(0, str(value))
            entries[param] = entry

        def on_ok():
            try:
                for param, entry in entries.items():
                    new_value = entry.get()
                    # Use the type of the default value for robustness
                    current_type = type(node["params"].get(param))
                    try:
                        if current_type == bool:
                            node["params"][param] = new_value.lower() in ("true", "1", "yes")
                        elif current_type == list:
                            node["params"][param] = [s.strip() for s in new_value.split(',') if s.strip()]
                        else:
                            node["params"][param] = current_type(new_value)
                    except (ValueError, TypeError):
                        self.gui.status_var.set(f"Invalid value for {param}: '{new_value}'")

                self.redraw_node(node)
            finally:
                dialog.destroy()

        button_frame = tk.Frame(dialog, bg="#34495e")
        button_frame.pack(pady=10)
        ok_button = tk.Button(button_frame, text="OK", command=on_ok, bg="#2ecc71", fg="white", width=10)
        ok_button.pack(side="left", padx=5)
        cancel_button = tk.Button(button_frame, text="Cancel", command=dialog.destroy, bg="#e74c3c", fg="white", width=10)
        cancel_button.pack(side="left", padx=5)

        dialog.transient(self)
        dialog.grab_set()
        self.wait_window(dialog)

    def show_node_context_menu(self, _event):
        pass

    def delete_selection(self, _event=None):
        """Delete selected node or connection."""
        vc = self.visual_canvas
        if self.selected_connection:
            if "graphics" in self.selected_connection and vc.winfo_exists():
                vc.delete(self.selected_connection["graphics"])
            self.connections.remove(self.selected_connection)
            self.selected_connection = None
            self._update_scrollregion()
            return

        if self.selected_node:
            node_id = self.selected_node["id"]
            # Remove connections attached to this node
            conns_to_remove = [c for c in self.connections if c["from_node"] == node_id or c["to_node"] == node_id]
            for conn in conns_to_remove:
                if "graphics" in conn and vc.winfo_exists():
                    vc.delete(conn["graphics"])
                self.connections.remove(conn)

            # Remove node graphics
            for item in self.selected_node["graphics"].values():
                if isinstance(item, list):
                    for sub_item in item: vc.delete(sub_item)
                else:
                    vc.delete(item)
            self.nodes.remove(self.selected_node)
            self.selected_node = None
            self._update_scrollregion()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def redraw_node(self, node: Dict[str, Any]):
        """Deletes and redraws a node and its connections."""
        vc = self.visual_canvas
        # Delete old graphics
        if "graphics" in node:
            for key, item in node["graphics"].items():
                # Check if item is a list of graphics (like inputs/outputs)
                if isinstance(item, list):
                    for sub_item in item:
                        vc.delete(sub_item)
                else:
                    vc.delete(item)

        # Redraw the node itself
        self.draw_node(node)
        # Redraw connections attached to it
        self.update_connections_for_node(node)

    def create_connection(self, from_node, from_port_idx, to_node, to_port_idx):
        """Create and draw a connection between two nodes."""
        # For now, only one connection per output is allowed
        existing = next((c for c in self.connections if c["from_node"] == from_node["id"] and c["from_port"] == from_port_idx), None)
        if existing:
            self.visual_canvas.delete(existing["graphics"])
            self.connections.remove(existing)

        conn = {
            "from_node": from_node["id"],
            "from_port": from_port_idx,
            "to_node": to_node["id"],
            "to_port": to_port_idx,
        }
        self.connections.append(conn)
        self.draw_connection(conn)

    def update_connections_for_node(self, node: Dict[str, Any]):
        """Update connection lines attached to a specific node."""
        vc = self.visual_canvas
        for conn in self.connections:
            if conn.get("graphics") and (conn["from_node"] == node["id"] or conn["to_node"] == node["id"]):
                from_node = next((n for n in self.nodes if n["id"] == conn["from_node"]), None)
                to_node = next((n for n in self.nodes if n["id"] == conn["to_node"]), None)
                if not from_node or not to_node: continue

                x1 = from_node["x"] + from_node["outputs"][conn["from_port"]]["x"]
                y1 = from_node["y"] + from_node["outputs"][conn["from_port"]]["y"]
                x2 = to_node["x"] + to_node["inputs"][conn["to_port"]]["x"]
                y2 = to_node["y"] + to_node["inputs"][conn["to_port"]]["y"]
                vc.coords(conn["graphics"], x1, y1, x2, y2)

    def _get_io_point_at(self, x: int, y: int) -> Optional[Tuple[Dict[str, Any], str, int]]:
        """Check if (x,y) is over an input/output point."""
        for node in reversed(self.nodes):  # check topmost nodes first
            # Check inputs
            for i, inp in enumerate(node["inputs"]):
                x_pt, y_pt = node["x"] + inp["x"], node["y"] + inp["y"]
                if (x - x_pt)**2 + (y - y_pt)**2 < 7**2:  # 7px radius
                    return node, "input", i
            # Check outputs
            for i, out in enumerate(node["outputs"]):
                x_pt, y_pt = node["x"] + out["x"], node["y"] + out["y"]
                if (x - x_pt)**2 + (y - y_pt)**2 < 7**2:
                    return node, "output", i
        return None

    def _get_connection_at(self, x0: int, y0: int) -> Optional[Dict[str, Any]]:
        """Check if (x0,y0) is near any connection line."""
        vc = self.visual_canvas
        for conn in self.connections:
            if "graphics" not in conn: continue
            x1, y1, x2, y2 = vc.coords(conn["graphics"])
            # Basic distance-to-line-segment check
            dist_sq = (x2 - x1)**2 + (y2 - y1)**2
            if dist_sq == 0: continue
            t = ((x0 - x1) * (x2 - x1) + (y0 - y1) * (y2 - y1)) / dist_sq
            t = max(0, min(1, t))
            closest_x, closest_y = x1 + t * (x2 - x1), y1 + t * (y2 - y1)
            if ((x0 - closest_x)**2 + (y0 - closest_y)**2) < 5**2: # 5px tolerance
                return conn
        return None

    def _clear_selection(self):
        """Clear any node or connection selection visuals."""
        vc = self.visual_canvas
        if self.selected_node and "graphics" in self.selected_node:
            # Check if bg exists before trying to change it
            if vc.winfo_exists() and self.selected_node["graphics"]["bg"] in vc.find_all():
                fill_color = "#3498db" if self.selected_node["type"] != "start" else "#2ecc71"
                vc.itemconfig(self.selected_node["graphics"]["bg"], outline="#ecf0f1")
        if self.selected_connection and "graphics" in self.selected_connection:
            if vc.winfo_exists() and self.selected_connection["graphics"] in vc.find_all():
                vc.itemconfig(self.selected_connection["graphics"], fill="#ecf0f1")
        self.selected_node = None
        self.selected_connection = None

    # Maintain scrollregion automatically
    def on_canvas_configure(self, _event):
        self._update_scrollregion()

    def _update_scrollregion(self):
        """Updates the canvas scrollregion to encompass all items."""
        self.visual_canvas.configure(scrollregion=self.visual_canvas.bbox("all"))

    def clear_canvas(self):
        """Clear all nodes and connections from the canvas."""
        self.visual_canvas.delete("all")
        self.nodes = []
        self.connections = []
        self.selected_node = None
        self.selected_connection = None
        self.node_counter = 0
        self.create_start_node()

    def load_from_dict(self, data: Dict[str, List[Dict[str, Any]]]):
        """Load nodes and connections from a dictionary."""
        self.clear_canvas()

        if "nodes" in data:
            # Filter out start node from loaded data to prevent duplicates
            loaded_nodes = [n for n in data["nodes"] if n.get("type") != "start"]
            self.nodes.extend(loaded_nodes)

            max_id = 0
            for node in self.nodes:
                if node.get("type") == "start": continue
                self.draw_node(node)
                # Update node counter to avoid ID collisions
                try:
                    num = int(node['id'].split('_')[-1])
                    if num > max_id:
                        max_id = num
                except (ValueError, IndexError):
                    pass
            self.node_counter = max_id

        if "connections" in data:
            self.connections = data["connections"]
            for conn in self.connections:
                self.draw_connection(conn)

__all__ = ["VisualCanvas"]
