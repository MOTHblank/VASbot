while bot.is_running:

    if bot.find_and_click_color(hex_color='#ff981f', region_index=1, tolerance=10, button='left'):
        bot.find_and_click_color(hex_color='#f3f1f1', region_index=2, tolerance=10, button='left')
        bot.find_and_click_color(hex_color='#f3f1f1', region_index=2, tolerance=10, button='left')
        bot.wait(0.6)
    else:
        bot.find_and_click_color(hex_color='#51563A', region_index=0, tolerance=10, button='left')

    if bot.find_and_click_color(hex_color='#ff0000', region_index=1, tolerance=10, button='left'):
        bot.find_and_click_color(hex_color='#f3f1f1', region_index=2, tolerance=10, button='left')
        bot.find_and_click_color(hex_color='#f3f1f1', region_index=2, tolerance=10, button='left')
        bot.wait(0.6)
    else:
        bot.find_and_click_color(hex_color='#51563A', region_index=0, tolerance=10, button='left')


# ============ EMBEDDED REGIONS ============
# Auto-generated region definitions
# Created: 2026-03-18 01:00:02
# Window: Vidyascape 8.4.7

bot.gui.regions = [
    {'x': 673, 'y': 515, 'width': 145, 'height': 169, 'color': '#51563A'},
    {'x': 1204, 'y': 60, 'width': 20, 'height': 13, 'color': '#78180d'},
    {'x': 1245, 'y': 573, 'width': 182, 'height': 253, 'color': '#D5D0CF'}
]
bot.gui.update_region_selector()
bot.log('Loaded embedded regions')
# ============ END EMBEDDED REGIONS ============
