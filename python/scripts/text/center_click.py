# Center Click Verification
# Focuses the window and clicks the center

bot.log("Starting Center Click Verification...")

while bot.is_running:
    bot.focus_window()
    bot.wait(1.0)
    
    # Calculate screen coordinates for the center of the window
    hwnd = bot.gui.window_manager.selected_window
    from utils.windows_utils import _get_true_hwnd_rect
    left, top, right, bottom = _get_true_hwnd_rect(hwnd)
    
    center_x = left + (right - left) // 2
    center_y = top + (bottom - top) // 2
    
    bot.log(f"Calculated Center: ({center_x}, {center_y})")
    
    # Use Bot low-level API directly for verification
    bot.bot.move_to(center_x, center_y)
    bot.wait(1.0)
    bot.bot.click(center_x, center_y)
    
    bot.log("Clicked center of the window.")
    bot.wait(5.0)
