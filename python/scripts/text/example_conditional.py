"""
Example: Conditional Click with Variables
Uses If/While logic with variables to create smart automation.

This script demonstrates:
- Setting variables
- Conditional logic (If)
- Loops (While)
- Using variables in conditions

Usage:
1. Create regions on the captured image
2. Run this script
"""

import time


def run(bot):
    """Main script entry point."""

    # Initialize variables
    click_count = 0
    max_clicks = 10
    target_color = bot.gui.canvas_manager.current_color
    region_index = 0

    bot.log("=== Conditional Click Script Started ===")
    bot.log(f"Target color: {target_color}")
    bot.log(f"Max clicks: {max_clicks}")

    # While loop - repeat while condition is true
    while click_count < max_clicks and bot.is_running:

        # If - conditional execution
        if bot.find_and_click_color(target_color, region_index, tolerance=10):
            click_count += 1
            bot.log(f"SUCCESS: Found color! Clicked ({click_count}/{max_clicks})")
        else:
            # This runs when color is NOT found
            bot.log("Waiting for color...")

        # Small wait between checks
        bot.wait(0.5)

    # Log final stats using Get Variable equivalent
    bot.log("=== Script Complete ===")
    bot.log(f"Total clicks: {click_count}")

    # Example of variable manipulation
    success_rate = (click_count / max_clicks) * 100
    bot.log(f"Success rate: {success_rate:.0f}%")

    if success_rate >= 50:
        bot.log("Good success rate!")
    else:
        bot.log("Low success rate - check color tolerance")
