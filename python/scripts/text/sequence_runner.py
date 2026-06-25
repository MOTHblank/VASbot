# Region Sequence Runner
# Useful for menu navigation or fixed UI interactions

bot.log("Starting Sequence Runner...")

# Define the sequence of regions to click
sequence = [0, 1, 2]

while bot.is_running:
    for region_id in sequence:
        if not bot.is_running:
            break

        bot.log(f"Clicking Region {region_id}")
        bot.click_region(region_id)
        bot.wait(1.5)  # Wait for UI to react

    bot.log("Sequence complete. Restarting in 5 seconds...")
    bot.wait(5.0)
