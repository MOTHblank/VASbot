"""
Example: Multi-Region Automation
Demonstrates using multiple regions with logic.

This script:
1. Clicks one region
2. Waits
3. Clicks another region
4. Repeats with counting

Usage:
1. Create at least 2 regions on the captured image
2. Run this script
"""

import time


def run(bot):
    """Main script entry point."""

    bot.log("=== Multi-Region Automation Started ===")

    # Define regions to click in order
    regions = [0, 1]  # Region indices
    max_cycles = 5

    for cycle in range(max_cycles):
        if not bot.is_running:
            break

        bot.log(f"--- Cycle {cycle + 1}/{max_cycles} ---")

        for i, region_idx in enumerate(regions):
            if not bot.is_running:
                break

            # Click the region
            bot.click_region(region_idx)
            bot.log(f"Clicked region {region_idx}")

            # Wait between clicks
            bot.wait(0.3)

        # Random wait between cycles
        bot.random_wait(1.0, 0.5)

    bot.log("=== Multi-Region Automation Complete ===")
