"""
Window Automator - Opens an application and performs automated tasks

Usage:
1. Configure the application path below
2. Run this script
3. It will open the app and perform the configured actions
"""
import time

def run(bot):
    """Main script entry point.
    
    Args:
        bot: BotAPI instance
    """
    # Configuration
    app_path = "notepad.exe"  # Application to open
    app_title = "Notepad"  # Window title to wait for
    wait_time = 2  # Seconds to wait for app to open
    
    bot.log(f"Starting window automator - opening {app_path}")
    
    # Open the application
    bot.shell_run(app_path)
    bot.log(f"Opened {app_path}, waiting {wait_time}s...")
    time.sleep(wait_time)
    
    # Wait for window to appear and focus it
    if bot.pywinauto:
        try:
            window = bot.pywinauto.wait_window(app_title, timeout=5)
            bot.pywinauto.maximize_window(window)
            bot.log(f"Maximized window: {app_title}")
        except Exception as e:
            bot.log(f"Pywinauto error: {e}")
    
    # Type some text
    bot.type("Hello from VASbot!")
    bot.log("Typed text")
    time.sleep(0.5)
    
    # Press Enter
    bot.press_key("return")
    time.sleep(0.3)
    
    # Type more text
    bot.type("This is an automated message.")
    bot.log("Typed second line")
    
    # Save the file (Ctrl+S)
    bot.key_down("ctrl")
    bot.type("s")
    bot.key_up("ctrl")
    time.sleep(0.5)
    
    # Type a filename
    bot.type("automated_note.txt")
    bot.press_key("return")
    bot.log("Saved file")
    
    bot.log("Window automator finished!")
