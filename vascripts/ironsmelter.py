# 0 coal 1 iron 2 deposit
# ============ EMBEDDED REGIONS ============
# Auto-generated region definitions
# Created: 2025-10-13 09:02:43
# Image size: 1530x1006
# Window: Vidyascape 8.4.6 (HWND: 721946)

bot.gui.regions = [
    {'x': 804, 'y': 247, 'width': 54, 'height': 60, 'color': '#FF0000'},
    {'x': 804, 'y': 325, 'width': 61, 'height': 65, 'color': '#FF0000'},
    {'x': 947, 'y': 601, 'width': 54, 'height': 61, 'color': '#FF0000'},
    {'x': 859, 'y': 411, 'width': 95, 'height': 33, 'color': '#FF0000'},
    {'x': 870, 'y': 454, 'width': 91, 'height': 28, 'color': '#FF0000'},
    {'x': 971, 'y': 34, 'width': 31, 'height': 37, 'color': '#FF0000'},
    {'x': 475, 'y': 76, 'width': 14, 'height': 27, 'color': '#FF0000'},
    {'x': 438, 'y': 809, 'width': 51, 'height': 53, 'color': '#FF0000'},
    {'x': 464, 'y': 907, 'width': 78, 'height': 23, 'color': '#FF0000'},
    {'x': 622, 'y': 647, 'width': 14, 'height': 28, 'color': '#FF0000'},
    {'x': 518, 'y': 437, 'width': 12, 'height': 21, 'color': '#FF0000'},
    {'x': 495, 'y': 521, 'width': 62, 'height': 23, 'color': '#FF0000'},
]
bot.gui.update_region_selector()
bot.log('Loaded embedded regions')
# ============ END EMBEDDED REGIONS ============

while bot.is_running:
    bot.wait(0.6)
    bot.click_region(region_index=1, button='right')
    bot.click_region(region_index=1, button='left')
    bot.click_region(region_index=1, button='right')
    bot.click_region(region_index=4, button='left')
    bot.wait(0.6)
    bot.click_region(region_index=0, button='right')
    bot.click_region(region_index=0, button='left')
    bot.click_region(region_index=0, button='right')
    bot.click_region(region_index=3, button='left')
    bot.wait(0.6)
    
    bot.click_region(region_index=5, button='right')
    bot.click_region(region_index=5, button='left')
    bot.click_region(region_index=5, button='left')
    
    bot.click_region(region_index=6, button='right')
    bot.click_region(region_index=6, button='left')
    bot.click_region(region_index=6, button='left')
    bot.wait(6)
    
    bot.click_region(region_index=7, button='right')
    bot.click_region(region_index=7, button='left')
    bot.click_region(region_index=7, button='right')
    bot.click_region(region_index=8, button='left')
    bot.wait(27)
    
    bot.click_region(region_index=9, button='left')
    bot.click_region(region_index=9, button='left')
    bot.wait(5.6)
    
    bot.click_region(region_index=10, button='right')
    bot.click_region(region_index=10, button='left')
    bot.click_region(region_index=10, button='right')
    bot.click_region(region_index=11, button='left')
    bot.wait(2)
    
    bot.click_region(region_index=2, button='left')
    bot.click_region(region_index=2, button='left')
    bot.wait(1.2)
    bot.click_region(region_index=2, button='left')



