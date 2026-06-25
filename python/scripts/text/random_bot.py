# Randomized Bot
# Moves between regions with variance
import random

bot.log("Starting Randomized Bot...")

while bot.is_running:
    # Randomly pick between Region 0 and Region 1
    target = random.choice([0, 1])

    bot.log(f"Moving to Region {target}...")
    bot.move_to_region(target)

    # Perform a right-click
    bot.click_region(target, button="right")

    # Use randomized wait (base 2s, +/- 1s variance)
    bot.log("Waiting for random interval...")
    bot.random_wait(2.0, 1.0)
