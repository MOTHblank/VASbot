while bot.is_running:

    if bot.find_and_click_color(hex_color='#ff981f', region_index=1, tolerance=10, button='left'):
        bot.find_and_click_color(hex_color='#f3f1f1', region_index=2, tolerance=10, button='left')
        bot.find_and_click_color(hex_color='#f3f1f1', region_index=2, tolerance=10, button='left')
        bot.wait(0.6)
    else:
        bot.find_and_click_color(hex_color='#6817bd', region_index=0, tolerance=10, button='left')

    if bot.find_and_click_color(hex_color='#ff0000', region_index=1, tolerance=10, button='left'):
        bot.find_and_click_color(hex_color='#f3f1f1', region_index=2, tolerance=10, button='left')
        bot.find_and_click_color(hex_color='#f3f1f1', region_index=2, tolerance=10, button='left')
        bot.wait(0.6)
    else:
        bot.find_and_click_color(hex_color='#6817bd', region_index=0, tolerance=10, button='left')







# ============ EMBEDDED REGIONS ============
# Auto-generated region definitions
# Created: 2026-03-17 23:28:41
# Window: Vidyascape 8.4.7

bot.gui.regions = [
    {'x': 383, 'y': 209, 'width': 646, 'height': 516, 'color': '#6714BA'},
    {'x': 1047, 'y': 103, 'width': 33, 'height': 38, 'color': '#78180d'},
    {'x': 1119, 'y': 418, 'width': 341, 'height': 494, 'color': '#ba6215'}
]
bot.gui.update_region_selector()
bot.log('Loaded embedded regions')
# ============ END EMBEDDED REGIONS ============
