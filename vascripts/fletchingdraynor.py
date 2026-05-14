while bot.is_running:
    bot.wait(0.2)
    bot.click_region(region_index=1, button='left', modifiers=[], human_like=True)
    bot.wait(0.8)
    bot.click_region(region_index=0, button='right', modifiers=[], human_like=True)
    bot.wait(0.8)
    bot.click_region(region_index=3, button='left', modifiers=[], human_like=True)
    bot.wait(0.8)
    bot.click_region(region_index=2, button='left', modifiers=[], human_like=True)
    bot.wait(0.8)
    bot.click_region(region_index=4, button='left', modifiers=[], human_like=True)
    bot.wait(0.8)
    bot.click_region(region_index=5, button='left', modifiers=[], human_like=True)
    bot.wait(1)
    bot.click_region(region_index=6, button='right', modifiers=[], human_like=True)
    bot.wait(0.8)
    bot.click_region(region_index=7, button='left', modifiers=[], human_like=True)
    bot.wait(1.6)
    bot.type_text('30', delay=0.05, press_enter=True)
    bot.wait(47)
    bot.click_region(region_index=0, button='right', modifiers=[], human_like=True)
    bot.wait(0.8)
    bot.click_region(region_index=8, button='left', modifiers=[], human_like=True)
    bot.wait(0.8)
    bot.click_region(region_index=9, button='left', modifiers=[], human_like=True)
    bot.click_region(region_index=9, button='left', modifiers=[], human_like=True)
    bot.wait(0.8)

# ============ EMBEDDED REGIONS ============
# Auto-generated region definitions
# Created: 2026-04-04 12:21:49
# Window: Vidyascape 8.4.7

bot.gui.regions = [
    {'x': 564, 'y': 396, 'width': 36, 'height': 35, 'color': '#FFFFFF'},
    {'x': 610, 'y': 396, 'width': 43, 'height': 35, 'color': '#FFFFFF'},
    {'x': 843, 'y': 221, 'width': 18, 'height': 17, 'color': '#FFFFFF'},
    {'x': 621, 'y': 482, 'width': 16, 'height': 14, 'color': '#FFFFFF'},
    {'x': 1262, 'y': 582, 'width': 29, 'height': 30, 'color': '#FFFFFF'},
    {'x': 1259, 'y': 622, 'width': 33, 'height': 25, 'color': '#FFFFFF'},
    {'x': 348, 'y': 753, 'width': 64, 'height': 56, 'color': '#FFFFFF'},
    {'x': 364, 'y': 840, 'width': 17, 'height': 15, 'color': '#FFFFFF'},
    {'x': 576, 'y': 451, 'width': 24, 'height': 9, 'color': '#FFFFFF'},
    {'x': 832, 'y': 504, 'width': 25, 'height': 22, 'color': '#FFFFFF'}
]
bot.gui.update_region_selector()
bot.log('Loaded embedded regions')
# ============ END EMBEDDED REGIONS ============
