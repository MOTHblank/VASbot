#!/usr/bin/env python3
import tkinter as tk
from tkinter import messagebox
from gui.colorbot_gui import ColorBotGUI

class ColorBot:
    def __init__(self): 
        self.root = tk.Tk()
        self.gui = ColorBotGUI(self.root)
    def run(self): 
        self.root.mainloop()

def main():
    try: 
        bot = ColorBot()
        bot.run()
    except Exception as e: 
        messagebox.showerror("Error", f"Failed to start: {e}")

if __name__ == "__main__": 
    main()