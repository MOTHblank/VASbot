# Automated Typer
# Focuses the window and types a message
import time

bot.log("Starting Auto Typer...")

while bot.is_running:
    # Ensure window is active
    bot.focus_window()
    bot.wait(0.5)
    
    # Type a message
    message = "Hello from VASbot! Current time: " + time.strftime("%H:%M:%S")
    bot.type_text(message)
    
    # Press Enter
    bot.press_key('enter')
    
    bot.log("Message sent.")
    bot.wait(10.0) # Wait 10 seconds before next message
