"""
Color Clicker - Clicks when target color is found in a region

Usage:
1. Capture a region using the GUI
2. Run this script
3. It will click automatically when the target color is found
"""

import time


def run(bot):
    """Main script entry point.

    Args:
        bot: BotAPI instance
    """
    # Configuration
    target_color = "#FF0000"  # Red color to find (use #RRGGBB format)
    region_index = 0  # Index of region to search (0 = first region)
    tolerance = 10  # Color matching tolerance (0-255)
    click_delay = 0.5  # Delay between clicks in seconds
    max_clicks = 100  # Maximum clicks before stopping (0 = unlimited)

    bot.log(
        f"Starting color clicker - searching for {target_color} in region {region_index}"
    )
    bot.log(f"Tolerance: {tolerance}, Click delay: {click_delay}s")

    click_count = 0
    while bot.is_running and (max_clicks == 0 or click_count < max_clicks):
        # Try to find and click the color
        if bot.find_and_click_color(target_color, region_index, tolerance=tolerance):
            click_count += 1
            bot.log(f"Clicked! Total: {click_count}")

        # Wait before next check
        time.sleep(click_delay)

    bot.log(f"Color clicker finished. Total clicks: {click_count}")
