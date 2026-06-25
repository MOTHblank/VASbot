"""
Auto Clicker - Clicks at a specific location repeatedly

Usage:
1. Configure the coordinates and timing below
2. Run this script
3. It will click at the specified location
"""

import time


def run(bot):
    """Main script entry point.

    Args:
        bot: BotAPI instance
    """
    # Configuration
    x = 500  # X coordinate (or use -1 for current mouse position)
    y = 500  # Y coordinate (or use -1 for current mouse position)
    clicks_per_second = 5  # Clicks per second
    max_clicks = 0  # 0 = unlimited
    button = "left"  # left, right, or middle

    click_interval = 1.0 / clicks_per_second

    bot.log(f"Starting auto clicker at ({x}, {y})")
    bot.log(f"Clicks per second: {clicks_per_second}")

    click_count = 0
    while bot.is_running and (max_clicks == 0 or click_count < max_clicks):
        # Get current mouse position if x or y is -1
        if x == -1 or y == -1:
            curr_x, curr_y = bot.get_mouse_pos()
            click_x = curr_x if x == -1 else x
            click_y = curr_y if y == -1 else y
        else:
            click_x, click_y = x, y

        # Click
        bot.click(click_x, click_y, button)
        click_count += 1

        if click_count % 10 == 0:
            bot.log(f"Clicks: {click_count}")

        # Wait
        time.sleep(click_interval)

    bot.log(f"Auto clicker finished. Total clicks: {click_count}")
