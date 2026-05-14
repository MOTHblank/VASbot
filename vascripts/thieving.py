# ============ EMBEDDED REGIONS ============
# Auto-generated region definitions
# Created: 2025-09-23 19:24:51
# Image size: 1530x1006
# Window: Vidyascape 8.4.6 (HWND: 460704)

bot.gui.regions = [
    {'x': 91, 'y': 146, 'width': 878, 'height': 534, 'color': '#78180d'},
    {'x': 1047, 'y': 103, 'width': 33, 'height': 38, 'color': '#78180d'},
    {'x': 1119, 'y': 418, 'width': 341, 'height': 494, 'color': '#ba6215'},
]
bot.gui.update_region_selector()
bot.log('Loaded embedded regions')
# ============ END EMBEDDED REGIONS ============

while bot.is_running:

    if bot.find_and_click_color(hex_color='#ff0000', region_index=1, tolerance=10, button='left'):
        bot.find_and_click_color(hex_color='#ba6215', region_index=2, tolerance=10, button='left')
        bot.find_and_click_color(hex_color='#ba6215', region_index=2, tolerance=10, button='left')
        bot.wait(0.6)
    else:
        bot.find_and_click_color(hex_color='#480e82', region_index=0, tolerance=10, button='left')





