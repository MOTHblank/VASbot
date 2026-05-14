while bot.is_running:

    if bot.find_and_click_color(hex_color='#543426', region_index=0, tolerance=10, button='left'):
        bot.wait(0.3)
    else:
        bot.find_and_click_color(hex_color='#3f261d', region_index=1, tolerance=10, button='left')
        bot.wait(0.3)
    
    if bot.find_and_click_color(hex_color='#4c2e22', region_index=3, tolerance=10, button='right'):
        bot.click_region(region_index=3, button='left')
        bot.click_region(region_index=3, button='right')
        bot.click_region(region_index=4, button='left')
        bot.click_region(region_index=2, button='right')
        bot.click_region(region_index=2, button='left')
        bot.click_region(region_index=2, button='right')
        bot.click_region(region_index=4, button='left')
    
    






