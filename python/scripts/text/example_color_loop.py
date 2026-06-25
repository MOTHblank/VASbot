"""
Example: Color Clicker Loop
Finds and clicks a color repeatedly with a random wait between clicks.

Usage:
1. Create a region on the captured image
2. Run this script
3. It will click when the target color is found
"""

import time
import random


def run(bot):
    """Main script entry point."""

    # Configuration
    target_color = bot.gui.canvas_manager.current_color  # Use currently selected color
    region_index = 0  # First region
    tolerance = 10
    max_clicks = 50  # Stop after this many clicks (0 = unlimited)
    min_wait = 0.5
    max_wait = 2.0

    bot.log("Starting color clicker loop")
    bot.log(f"Target color: {target_color}")
    bot.log(f"Region: {region_index}, Tolerance: {tolerance}")

    click_count = 0
    while bot.is_running:
        # Try to find and click the color
        if bot.find_and_click_color(target_color, region_index, tolerance=tolerance):
            click_count += 1
            bot.log(f"Clicked! Total: {click_count}")

            # Check max clicks
            if max_clicks > 0 and click_count >= max_clicks:
                bot.log(f"Reached max clicks: {max_clicks}")
                break
        else:
            # Color not found - continue loop
            pass

        # Random wait between checks
        wait_time = random.uniform(min_wait, max_wait)
        bot.wait(wait_time)

    bot.log(f"Script finished. Total clicks: {click_count}")
