# bank_and_withdraw.py
# Advanced script utilizing transparency template matching and robust OCR with dynamic ROIs
import os

# Define absolute paths to template images in the project's /img directory
project_root = os.path.dirname(os.getcwd())  # Since python cwd is c:\sandbox\projects\VASbot3\python
ghostbanker_path = os.path.join(project_root, "img", "ghostbanker.png")
cosmicrune_path = os.path.join(project_root, "img", "cosmicrune.png")
close_path = os.path.join(project_root, "img", "close.png")

bot.log("Starting Bank & Withdraw test script...")
bot.log(f"Loading template: {ghostbanker_path}")
bot.log(f"Loading template: {cosmicrune_path}")
bot.log(f"Loading template: {close_path}")

while bot.is_running:
    # 1. Find the Ghost Banker on screen (searching the full screen)
    bot.log("Searching for Ghost Banker...")
    banker_pos = bot.find_image(ghostbanker_path, region_index=None, confidence=0.7)
    
    if not banker_pos:
        bot.log("ERROR: Could not find Ghost Banker on screen. Please ensure they are visible.")
        bot.wait(2.0)
        continue
        
    bot.log(f"Found Ghost Banker at {banker_pos}. Right-clicking...")
    bot.click(banker_pos[0], banker_pos[1], button="right", human_like=True)
    bot.wait(0.6)
    
    # Calculate relative window coordinates of the click to crop an OCR search ROI (300x300)
    rel_x, rel_y = bot.screen_to_client(banker_pos[0], banker_pos[1])

    # Crop an OCR ROI right around the right-click menu area
    banker_roi = {
        "x": max(0, int(rel_x - 100)),
        "y": max(0, int(rel_y - 50)),
        "width": 300,
        "height": 300
    }
    bot.log(f"Using dynamic OCR Region of Interest around click: {banker_roi}")
    
    # 2. Find the right-click option "Bank Ghost banker" via OCR inside the narrow ROI
    bot.log("Searching for right-click menu option 'Bank Ghost banker' inside ROI...")
    option_pos = bot.find_text("Bank Ghost banker", region_index=banker_roi, case_sensitive=False)
    
    # If not found, try a looser fallback term "Ghost banker" or just "Bank"
    if not option_pos:
        bot.log("Option 'Bank Ghost banker' not matched. Trying fallback 'Ghost banker' inside ROI...")
        option_pos = bot.find_text("Ghost banker", region_index=banker_roi, case_sensitive=False)
    if not option_pos:
        bot.log("Trying fallback 'Bank' inside ROI...")
        option_pos = bot.find_text("Bank", region_index=banker_roi, case_sensitive=False)
        
    if not option_pos:
        bot.log("ERROR: Right-click menu option not found via OCR.")
        # Click away to close menu and retry
        bot.click(banker_pos[0] - 80, banker_pos[1], button="left", human_like=True)
        bot.wait(1.5)
        continue
        
    bot.log(f"Option found at {option_pos}. Left-clicking to open bank...")
    bot.click(option_pos[0], option_pos[1], button="left", human_like=True)
    
    # 3. Wait up to 5 seconds for the bank interface to open (checking for close.png)
    bot.log("Waiting for the bank interface to open...")
    bank_open = False
    for attempt in range(10):
        if bot.find_image(close_path, region_index=None, confidence=0.75):
            bank_open = True
            break
        bot.wait(0.5)
        
    if not bank_open:
        bot.log("ERROR: Bank interface did not open in time.")
        continue
        
    bot.log("Bank interface successfully opened! Searching for Cosmic Rune...")
    bot.wait(0.5)
    
    # 4. Find Cosmic Rune template
    rune_pos = bot.find_image(cosmicrune_path, region_index=None, confidence=0.75)
    if not rune_pos:
        bot.log("ERROR: Could not locate Cosmic Rune inside the bank interface.")
        bot.is_running = False
        break
        
    bot.log(f"Found Cosmic Rune at {rune_pos}. Attempting to withdraw 5...")
    
    # 5. Right-click cosmic rune to open context menu
    bot.click(rune_pos[0], rune_pos[1], button="right", human_like=True)
    bot.wait(0.6)
    
    # Calculate relative window coordinates of the cosmic rune click
    rel_rune_x, rel_rune_y = bot.screen_to_client(rune_pos[0], rune_pos[1])

    # Crop an OCR ROI right around the cosmic rune context menu
    rune_roi = {
        "x": max(0, int(rel_rune_x - 100)),
        "y": max(0, int(rel_rune_y - 50)),
        "width": 300,
        "height": 300
    }
    bot.log(f"Using dynamic OCR Region of Interest around cosmic rune click: {rune_roi}")
    
    # 6. Locate "Withdraw-5" (or "Withdraw 5") using OCR in the narrow ROI
    bot.log("Searching for 'Withdraw-5' option in context menu inside ROI...")
    withdraw_pos = bot.find_text("Withdraw-5", region_index=rune_roi, case_sensitive=False)
    if not withdraw_pos:
        withdraw_pos = bot.find_text("Withdraw 5", region_index=rune_roi, case_sensitive=False)
        
    if withdraw_pos:
        bot.log(f"Found 'Withdraw-5' option at {withdraw_pos}. Left-clicking...")
        bot.click(withdraw_pos[0], withdraw_pos[1], button="left", human_like=True)
        bot.wait(0.8)
    else:
        # Fallback to clicking the cosmic rune 5 times if context menu OCR doesn't match
        bot.log("OCR for 'Withdraw-5' missed. Falling back to 5 single-clicks at same location...")
        # Left click somewhere away to dismiss context menu first
        bot.click(rune_pos[0] - 80, rune_pos[1], button="left", human_like=True)
        bot.wait(0.5)
        for click_num in range(1, 6):
            bot.log(f"Clicking Cosmic Rune ({click_num}/5)...")
            bot.click(rune_pos[0], rune_pos[1], button="left", human_like=True)
            bot.wait(0.6)
            
    # 7. Close Bank and Finish
    bot.log("Withdrew cosmic runes. Closing bank...")
    close_btn = bot.find_image(close_path, region_index=None, confidence=0.75)
    if close_btn:
        bot.click(close_btn[0], close_btn[1], button="left", human_like=True)
        bot.wait(0.5)
        
    bot.log("Script execution successfully completed!")
    bot.is_running = False
    break

# ============ EMBEDDED REGIONS ============
# Auto-generated region definitions
bot.gui.regions = []
bot.gui.update_region_selector()
# ============ END EMBEDDED REGIONS ============
