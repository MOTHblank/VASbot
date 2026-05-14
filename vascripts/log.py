# Enhanced Color Bot Script with Region Management
# ============ EMBEDDED REGIONS ============
# Auto-generated region definitions
# Created: 2025-08-31 20:09:13
# Image size: 436x912
# Window: 2009Scape [Local] - Mothblank2 (HWND: 2033290)

bot.gui.regions = [
    {'x': 48, 'y': 262, 'width': 352, 'height': 396, 'color': '#503c22'},
    {'x': 224, 'y': 577, 'width': 33, 'height': 42, 'color': '#585551'},
]
bot.gui.update_region_selector()
bot.log('Loaded embedded regions')
# ============ END EMBEDDED REGIONS ============

while bot.is_running:
    bot.wait(2)
    bot.click_region(region_index=1, button='left', background=False)
    
    if bot.find_and_click_color(hex_color='#585551', region_index=1, tolerance=10, button='left', background=False):
        bot.wait(0.5)
    else:
        bot.log('Color #585551 not found')
    if bot.find_and_click_color(hex_color='#503c22', region_index=0, tolerance=10, button='left', background=False):
        bot.wait(0.5)
    else:
        bot.log('Color #503c22 not found')





