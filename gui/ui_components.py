import tkinter as tk
from tkinter import ttk, scrolledtext

def create_title_section(parent):
    frame = tk.Frame(parent, bg='#34495e', relief=tk.RAISED, bd=2)
    frame.pack(fill=tk.X, pady=5)
    tk.Label(frame, text="🎮 2009scape Color Bot v2.1", font=('Arial',24,'bold'), 
             fg='#ecf0f1', bg='#34495e').pack(pady=10)
    tk.Label(frame, text="High-Precision Automation with Background & Foreground Input + Region Management", 
             font=('Arial',12), fg='#bdc3c7', bg='#34495e').pack()
    tk.Label(frame, text="🔥 Hotkeys: F5=Run | F6=Pause/Resume | F7=Stop | ESC=Emergency Stop | Ctrl+S=Save | Ctrl+O=Load | Ctrl+R=Capture", 
             font=('Arial',9), fg='#f39c12', bg='#34495e').pack(pady=(0,10))
    return frame

def create_window_section(parent, gui_instance):
    frame = tk.Frame(parent, bg='#34495e', relief=tk.RAISED, bd=2)
    frame.pack(fill=tk.X, pady=5)
    
    left = tk.Frame(frame, bg='#34495e')
    left.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=15, pady=15)
    tk.Label(left, text="🎯 Target Window:", font=('Arial',12,'bold'), 
             fg='#ecf0f1', bg='#34495e').pack(anchor=tk.W)
    
    gui_instance.window_var = tk.StringVar()
    gui_instance.window_combo = ttk.Combobox(left, textvariable=gui_instance.window_var, 
                                           width=50, font=('Arial',10))
    gui_instance.window_combo.pack(fill=tk.X, pady=5)
    
    btns = tk.Frame(left, bg='#34495e')
    btns.pack(fill=tk.X, pady=5)
    
    buttons = [
        ("🔄 Refresh", gui_instance.load_window_list, '#3498db'),
        ("📷 Capture", gui_instance.capture_window, '#e74c3c'),
        ("🔍 Test Click", gui_instance.test_click_accuracy, '#9b59b6'),
        ("ℹ️ Window Info", gui_instance.show_window_info, '#34495e')
    ]
    
    for text, cmd, color in buttons:
        tk.Button(btns, text=text, command=cmd, bg=color, fg='white', 
                 font=('Arial',10,'bold'), padx=15).pack(side=tk.LEFT, padx=5)
    
    right = tk.Frame(frame, bg='#34495e')
    right.pack(side=tk.RIGHT, padx=15, pady=15)
    tk.Label(right, text="🗂️ Region & Script Management:", font=('Arial',12,'bold'), 
             fg='#ecf0f1', bg='#34495e').pack(anchor=tk.W)
    
    mgmt_buttons = [
        [("💾 Save Script", gui_instance.save_script, '#27ae60'), 
         ("📂 Load Script", gui_instance.load_script, '#f39c12')],
        [("📤 Save Regions", gui_instance.save_regions, '#8e44ad'), 
         ("📥 Load Regions", gui_instance.load_regions, '#e67e22')],
        [("🔗 Embed Regions", gui_instance.embed_regions_in_script, '#16a085')]
    ]
    
    for row in mgmt_buttons:
        frow = tk.Frame(right, bg='#34495e')
        frow.pack(pady=2, fill=tk.X)
        for text, cmd, color in row:
            width = 25 if len(row) == 1 else 12
            tk.Button(frow, text=text, command=cmd, bg=color, fg='white', 
                     font=('Arial',9,'bold'), width=width).pack(side=tk.LEFT, padx=1)
    
    return frame

def create_capture_panel(parent, gui_instance):
    frame = tk.Frame(parent, bg='#34495e', relief=tk.RAISED, bd=2)
    frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
    
    tk.Label(frame, text="🖥️ Screen Capture & Tools", font=('Arial',16,'bold'), 
             fg='#ecf0f1', bg='#34495e').pack(padx=15, pady=15)
    
    ctrls = tk.Frame(frame, bg='#34495e')
    ctrls.pack(fill=tk.X, padx=15, pady=5)
    
    ctrl_buttons = [
        ("🎯 Select Region", gui_instance.toggle_selection_mode, '#9b59b6'),
        ("🎨 Color", gui_instance.choose_color, gui_instance.current_color),
        ("💧 Eyedropper", gui_instance.toggle_eyedropper_mode, '#1abc9c'),
        ("🔍 Reset Zoom", gui_instance.reset_zoom, '#f1c40f'),
        ("🧹 Clear Regions", gui_instance.clear_regions, '#e67e22')
    ]
    
    for text, cmd, color in ctrl_buttons:
        if text == "🎨 Color":
            gui_instance.color_button = tk.Button(ctrls, text=text, command=cmd, bg=color, 
                                                fg='white', font=('Arial',10,'bold'), padx=10)
            gui_instance.color_button.pack(side=tk.LEFT, padx=3)
        else:
            tk.Button(ctrls, text=text, command=cmd, bg=color, fg='white', 
                     font=('Arial',10,'bold'), padx=10).pack(side=tk.LEFT, padx=3)
    
    tol_frame = tk.Frame(ctrls, bg='#34495e')
    tol_frame.pack(side=tk.LEFT, padx=10)
    tk.Label(tol_frame, text="Tolerance:", fg='#ecf0f1', bg='#34495e', 
             font=('Arial',9)).pack(side=tk.LEFT)
    gui_instance.tolerance_var = tk.StringVar(value="10")
    tk.Entry(tol_frame, textvariable=gui_instance.tolerance_var, width=5, 
             font=('Arial',9)).pack(side=tk.LEFT, padx=2)
    
    cv_cont = tk.Frame(frame, bg='#34495e')
    cv_cont.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
    gui_instance.canvas = tk.Canvas(cv_cont, bg='black', cursor='arrow', 
                                   highlightthickness=2, highlightbackground='#3498db')
    gui_instance.canvas.pack(fill=tk.BOTH, expand=True)
    
    canvas_events = [
        ("<Configure>", gui_instance.on_canvas_configure),
        ("<Button-1>", gui_instance.start_selection),
        ("<B1-Motion>", gui_instance.update_selection),
        ("<ButtonRelease-1>", gui_instance.end_selection),
        ("<MouseWheel>", gui_instance.on_mouse_wheel),
        ("<Button-4>", gui_instance.on_mouse_wheel),
        ("<Button-5>", gui_instance.on_mouse_wheel),
        ("<ButtonPress-2>", gui_instance.start_pan),
        ("<B2-Motion>", gui_instance.do_pan),
        ("<ButtonRelease-2>", gui_instance.end_pan),
        ("<Double-Button-1>", gui_instance.reset_zoom),
        ("<Motion>", gui_instance.on_canvas_motion)
    ]
    
    for event, handler in canvas_events:
        gui_instance.canvas.bind(event, handler)
    
    return frame

def create_scripting_panel(parent, gui_instance):
    rframe = tk.Frame(parent, bg='#34495e', relief=tk.RAISED, bd=2, width=550)
    rframe.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5)
    rframe.pack_propagate(False)
    
    bframe = tk.Frame(rframe, bg='#34495e')
    bframe.pack(fill=tk.X, padx=15, pady=15)
    tk.Label(bframe, text="🛠️ Action Builder", font=('Arial',16,'bold'), 
             fg='#ecf0f1', bg='#34495e').pack(anchor=tk.W, pady=(0,10))
    
    # Row 1
    r1 = tk.Frame(bframe, bg='#34495e')
    r1.pack(fill=tk.X)
    tk.Label(r1, text="Action:", fg='#ecf0f1', bg='#34495e').pack(side=tk.LEFT)
    gui_instance.action_var = tk.StringVar(value="Find & Click Color")
    ttk.Combobox(r1, textvariable=gui_instance.action_var, 
                values=["Find & Click Color","Click Region Center","Wait","Random Wait"], 
                state="readonly", width=20).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
    
    tk.Label(r1, text="Target:", fg='#ecf0f1', bg='#34495e').pack(side=tk.LEFT)
    gui_instance.region_var = tk.StringVar()
    gui_instance.region_combo = ttk.Combobox(r1, textvariable=gui_instance.region_var, 
                                           state="readonly", width=15)
    gui_instance.region_combo.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
    
    # Row 2
    r2 = tk.Frame(bframe, bg='#34495e')
    r2.pack(fill=tk.X, pady=5)
    
    controls = [
        ("Button:", "button_var", "Left", ["Left","Right","Middle"], 8),
        ("Wait (s):", "wait_var", "1.0", None, 8)
    ]
    
    for label, var_name, default, values, width in controls:
        tk.Label(r2, text=label, fg='#ecf0f1', bg='#34495e').pack(side=tk.LEFT)
        setattr(gui_instance, var_name, tk.StringVar(value=default))
        
        if values:
            ttk.Combobox(r2, textvariable=getattr(gui_instance, var_name), 
                        values=values, state="readonly", width=width).pack(side=tk.LEFT, padx=5)
        else:
            tk.Entry(r2, textvariable=getattr(gui_instance, var_name), 
                    width=width).pack(side=tk.LEFT, padx=5)
    
    gui_instance.shift_var = tk.BooleanVar()
    tk.Checkbutton(r2, text="Shift", variable=gui_instance.shift_var, fg='#ecf0f1', 
                  bg='#34495e', selectcolor='#34495e').pack(side=tk.LEFT, padx=5)
    
    gui_instance.ctrl_var = tk.BooleanVar()
    tk.Checkbutton(r2, text="Ctrl", variable=gui_instance.ctrl_var, fg='#ecf0f1', 
                  bg='#34495e', selectcolor='#34495e').pack(side=tk.LEFT, padx=5)
    
    # Row 3
    r3 = tk.Frame(bframe, bg='#34495e')
    r3.pack(fill=tk.X, pady=5)
    tk.Button(r3, text="➕ Add to Script", command=gui_instance.add_action_to_script, 
             bg='#2ecc71', fg='white', font=('Arial',12,'bold')).pack(side=tk.LEFT, expand=True, fill=tk.X, ipady=5)
    
    gui_instance.background_var = tk.BooleanVar(value=True)
    tk.Checkbutton(r3, text="Background Input", variable=gui_instance.background_var, 
                  fg='#ecf0f1', bg='#34495e', selectcolor='#34495e', 
                  font=('Arial',10,'bold')).pack(side=tk.LEFT, padx=10)
    
    # Paned window for script editor and console
    pane = tk.PanedWindow(rframe, orient=tk.VERTICAL, sashrelief=tk.RAISED, bg='#34495e')
    pane.pack(fill=tk.BOTH, expand=True, padx=15, pady=(10,15))
    
    # Script editor frame
    eframe = tk.Frame(pane, bg='#34495e')
    ehdr = tk.Frame(eframe, bg='#34495e')
    ehdr.pack(fill=tk.X)
    
    tk.Label(ehdr, text="📝 Script Editor", font=('Arial',12,'bold'), 
             fg='#ecf0f1', bg='#34495e').pack(side=tk.LEFT)
    tk.Button(ehdr, text=">>", font=('Consolas',8), command=gui_instance.indent_selection, 
             width=4).pack(side=tk.RIGHT)
    tk.Button(ehdr, text="<<", font=('Consolas',8), 
             command=lambda: gui_instance.indent_selection(True), width=4).pack(side=tk.RIGHT)
    
    gui_instance.script_editor = scrolledtext.ScrolledText(eframe, wrap=tk.WORD, height=15, 
                                                          bg='#1c2833', fg='#ecf0f1', 
                                                          insertbackground='white', font=('Consolas',10))
    gui_instance.script_editor.pack(fill=tk.BOTH, expand=True)
    gui_instance.script_editor.insert(tk.END, "# Enhanced Color Bot Script with Region Management\nwhile bot.is_running:\n    bot.wait(1)\n    \n")
    pane.add(eframe)
    
    # Console frame
    cframe = tk.Frame(pane, bg='#34495e')
    tk.Label(cframe, text="Output Console", font=('Arial',12,'bold'), 
             fg='#ecf0f1', bg='#34495e').pack(anchor=tk.W)
    gui_instance.output_console = scrolledtext.ScrolledText(cframe, wrap=tk.WORD, height=5, 
                                                           state=tk.DISABLED, bg='#1c2833', 
                                                           fg='#aed6f1', font=('Consolas',9))
    gui_instance.output_console.pack(fill=tk.BOTH, expand=True)
    pane.add(cframe)
    
    gui_instance.root.update_idletasks()
    pane.sash_place(0, 0, 450)
    
    return rframe

def create_player_section(parent, gui_instance):
    frame = tk.Frame(parent, bg='#34495e', relief=tk.RAISED, bd=2)
    frame.pack(fill=tk.X, pady=5)
    
    tk.Label(frame, text="▶️ Script Player", font=('Arial',16,'bold'), 
             fg='#ecf0f1', bg='#34495e').pack(pady=(15,10))
    
    ctrls = tk.Frame(frame, bg='#34495e')
    ctrls.pack(pady=10)
    
    player_buttons = [
        ("▶️ Run (F5)", gui_instance.play_script, '#27ae60', 12),
        ("⏸️ Pause (F6)", gui_instance.pause_resume_script, '#f39c12', 12),
        ("⏹️ Stop (F7)", gui_instance.stop_script, '#e74c3c', 12),
        ("🚨 Emergency (ESC)", gui_instance.emergency_stop, '#c0392b', 15)
    ]
    
    for i, (text, cmd, color, width) in enumerate(player_buttons):
        btn = tk.Button(ctrls, text=text, command=cmd, bg=color, fg='white', 
                       font=('Arial',12,'bold'), width=width, padx=5)
        btn.pack(side=tk.LEFT, padx=5)
        if i == 1:
            gui_instance.pause_button = btn
            btn.config(state=tk.DISABLED)
        elif i == 0:
            gui_instance.play_button = btn
    
    gui_instance.status_var = tk.StringVar(value="Ready")
    tk.Label(frame, textvariable=gui_instance.status_var, fg='#ecf0f1', 
             bg='#34495e', font=('Arial',12)).pack(fill=tk.X, pady=5)
    
    return frame