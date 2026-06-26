# debug_ocr.py
import os
import cv2
import numpy as np

project_root = os.path.dirname(os.getcwd())
ghostbanker_path = os.path.join(project_root, "img", "ghostbanker.png")

bot.log("Starting Debug OCR Script...")

# 1. Find the Ghost Banker
bot.log("Searching for Ghost Banker...")
banker_pos = bot.find_image(ghostbanker_path, region_index=None, confidence=0.7)

if not banker_pos:
    bot.log("ERROR: Could not find Ghost Banker. Make sure they are visible!")
else:
    bot.log(f"Found Ghost Banker at {banker_pos}. Right-clicking...")
    bot.click(banker_pos[0], banker_pos[1], button="right", human_like=True)
    bot.wait(0.8) # Wait for menu to fully render
    
    # Capture the frame after right click
    full_frame = bot._get_current_frame()
    if full_frame is None:
        bot.log("ERROR: Could not get frame!")
    else:
        # Calculate ROI
        win_rect = bot.get_window_rect()
        if win_rect:
            win_left, win_top, _, _ = win_rect
            rel_x = banker_pos[0] - win_left
            rel_y = banker_pos[1] - win_top
        else:
            rel_x = banker_pos[0]
            rel_y = banker_pos[1]
            
        roi_x = max(0, int(rel_x - 100))
        roi_y = max(0, int(rel_y - 50))
        roi_w = 300
        roi_h = 300
        
        bot.log(f"Cropping ROI at x={roi_x}, y={roi_y}, w={roi_w}, h={roi_h}")
        
        # Crop ROI
        roi = full_frame[roi_y : roi_y + roi_h, roi_x : roi_x + roi_w]
        
        # Convert to BGR if BGRA
        if roi.shape[2] == 4:
            roi_bgr = cv2.cvtColor(roi, cv2.COLOR_BGRA2BGR)
        else:
            roi_bgr = cv2.cvtColor(roi, cv2.COLOR_RGB2BGR)
            
        # Save cropped ROI
        debug_dir = os.path.join(project_root, "artifacts", "debug_roi.png")
        # Ensure directory exists or put in the conversation's artifacts folder
        artifacts_dir = r"C:\Users\Matheus\.gemini\antigravity\brain\843a8ea1-71fc-4e3d-9279-ce86f045dfc6"
        roi_path = os.path.join(artifacts_dir, "debug_roi.png")
        
        cv2.imwrite(roi_path, roi_bgr)
        bot.log(f"SUCCESS: Saved cropped right-click ROI to {roi_path}")
        
        # Let's run a test OCR on this ROI using bot's find_text and print what words are found
        bot.log("Performing test OCR...")
        res = bot.find_text("Bank", region_index=[roi_x, roi_y, roi_w, roi_h])
        if res:
            bot.log(f"Test OCR SUCCESS: Found 'Bank' at {res}")
        else:
            bot.log("Test OCR FAILED: Could not find 'Bank' in cropped ROI.")
