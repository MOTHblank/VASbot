# Enhanced Color Bot Script with Region Management
# ============ EMBEDDED REGIONS ============
# Auto-generated region definitions
# Created: 2025-09-01 15:45:46
# Image size: 1008x729
# Window: 2009Scape [Local] - Mthatnio (HWND: 458872)

bot.gui.regions = [
    {'x': 140, 'y': 109, 'width': 368, 'height': 183, 'color': '#c5bdbc'},
    {'x': 680, 'y': 211, 'width': 181, 'height': 256, 'color': '#b3a8a7'},
    {'x': 805, 'y': 417, 'width': 53, 'height': 50, 'color': '#b3a8a7'},
    {'x': 816, 'y': 434, 'width': 14, 'height': 21, 'color': '#433b31'},
]
bot.gui.update_region_selector()
bot.log('Loaded embedded regions')
# ============ END EMBEDDED REGIONS ============

while bot.is_running:
    if bot.find_and_click_color(hex_color='#433b31', region_index=0, tolerance=10, button='left'):
        if bot.find_and_click_color(hex_color='#433b31', region_index=2, tolerance=10, button='middle'):
            if bot.find_and_click_color(hex_color='#433b31', region_index=1, tolerance=10, button='left', modifiers=['shift']):
                bot.log('Xicara dropada')
            else:
                bot.log('xicara nao encontrada')
        else:
            bot.log('Color #433b31 not found')
        

    else:
        bot.wait(1.0)










