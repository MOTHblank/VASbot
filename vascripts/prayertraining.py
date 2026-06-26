while bot.is_running:
    # take items
    bot.click(x=777, y=428, button='left', modifiers=[], human_like=True)
    bot.click(x=928, y=456, button='right', modifiers=[], human_like=True)
    bot.click(x=924, y=513, button='left', modifiers=[], human_like=True)
    bot.click(x=926, y=461, button='left', modifiers=[], human_like=True)
    bot.click(x=925, y=461, button='left', modifiers=[], human_like=False)
    bot.click(x=925, y=461, button='left', modifiers=[], human_like=False)
    bot.click(x=828, y=461, button='right', modifiers=[], human_like=True)
    bot.click(x=837, y=520, button='left', modifiers=[], human_like=True)
    bot.click(x=831, y=463, button='left', modifiers=[], human_like=True)
    bot.click(x=831, y=463, button='left', modifiers=[], human_like=False)
    bot.click(x=831, y=463, button='left', modifiers=[], human_like=False)

    # close bank, use ectophial
    bot.click(x=1092, y=344, button='left', modifiers=[], human_like=True)
    bot.wait(0.6)
    bot.click(x=1752, y=806, button='left', modifiers=[], human_like=True)
    bot.wait(3)

    # pray (keep trying each click until it finds the color)
    for i in range(10):
        while not bot.find_and_click_color(hex_color='#8CC787', region_index=3, tolerance=10, button='left', modifiers=[], human_like=False):
            bot.wait(0.1)
        bot.wait(0.6)  # let the ectofuntus animation cycle

    bot.wait(0.5)  # pause between major phases

    # find ghost disciple (not Necrovarus)
    # Region 3 (#B3C1AB) covers BOTH the ghost disciple and Necrovarus.
    # Region 2 sits exactly where the last letter of "disciple" lands, which only
    # "Talk-To Ghost disciple" reaches. Hover the B3C1AB target FIRST, check region 2
    # for yellow tooltip text, and only proceed if confirmed.
    # If the hit was Necrovarus, re-search until we find the real disciple.
    found_disciple = False
    while not found_disciple:
        hover_pos = bot.find_color(hex_color='#B3C1AB', region_index=3, tolerance=10)
        while not hover_pos:
            bot.wait(0.1)
            hover_pos = bot.find_color(hex_color='#B3C1AB', region_index=3, tolerance=10)

        abs_x, abs_y = hover_pos
        bot.move_mouse(abs_x, abs_y, human_like=False)
        bot.wait(0.15)  # let the tooltip render before sampling region 2
        if bot.find_color(hex_color='#FFFF00', region_index=2, tolerance=10):
            found_disciple = True
    bot.click(x=abs_x, y=abs_y, button='left', modifiers=[], human_like=False)
    
    bot.wait(1.0)  # Wait for the player to reach the ghost before checking for dialogue

    # Wait indefinitely until the color #0000FF is found and click it (Region 4)
    while not bot.find_and_click_color(hex_color='#0000FF', region_index=4, tolerance=10, button='left', modifiers=[], human_like=True):
        bot.wait(0.1)

    bot.wait(0.5)  # pause between major phases

    # pray again (keep trying each click until it finds the color)
    for i in range(6):
        while not bot.find_and_click_color(hex_color='#8CC787', region_index=3, tolerance=10, button='left', modifiers=[], human_like=False):
            bot.wait(0.1)
        bot.wait(0.6)  # let the ectofuntus animation cycle

    bot.wait(0.5)  # pause between major phases

    # talk to ghost disciple again
    found_disciple = False
    while not found_disciple:
        hover_pos = bot.find_color(hex_color='#B3C1AB', region_index=3, tolerance=10)
        while not hover_pos:
            bot.wait(0.1)
            hover_pos = bot.find_color(hex_color='#B3C1AB', region_index=3, tolerance=10)

        abs_x, abs_y = hover_pos
        bot.move_mouse(abs_x, abs_y, human_like=False)
        bot.wait(0.15)  # let the tooltip render before sampling region 2
        if bot.find_color(hex_color='#FFFF00', region_index=2, tolerance=10):
            found_disciple = True
    bot.click(x=abs_x, y=abs_y, button='left', modifiers=[], human_like=False)
    
    bot.wait(1.0)  # Wait for the player to reach the ghost before checking for dialogue

    # Wait indefinitely until the color #0000FF is found and click it (Region 4)
    while not bot.find_and_click_color(hex_color='#0000FF', region_index=4, tolerance=10, button='left', modifiers=[], human_like=True):
        bot.wait(0.1)

    bot.wait(0.5)  # pause between major phases

    bot.wait(0.5)  # pause between major phases

    # walk to gate
    found_gate = False
    while not found_gate:
        # Try to find the gate on the main screen (Region 5) using either known color
        hover_pos = bot.find_color(hex_color='#86A782', region_index=5, tolerance=15)
        if not hover_pos:
            hover_pos = bot.find_color(hex_color='#7F9E7C', region_index=5, tolerance=15)
        
        # If we didn't find the gate on the main screen, click the southern city wall on the minimap (Region 8) to walk south
        if not hover_pos:
            bot.log("Gate not found on screen. Clicking southern city wall on minimap...")
            if bot.find_and_click_color(hex_color='#3E353B', region_index=8, tolerance=0, button='left', modifiers=[], human_like=True):
                bot.wait(4.5)  # Let the player fully stop moving and the camera settle
            continue
            
        abs_x, abs_y = hover_pos
        bot.move_mouse(abs_x, abs_y, human_like=False)
        bot.wait(0.15)  # let the tooltip render before sampling region 6
        
        # Check Region 6 for #00FFFF (cyan tooltip)
        if bot.find_color(hex_color='#00FFFF', region_index=6, tolerance=10):
            found_gate = True
            bot.log("Gate verified via tooltip!")
        else:
            bot.log("Found gate color, but tooltip did not match. Clicking southern city wall to adjust position...")
            if bot.find_and_click_color(hex_color='#3E353B', region_index=8, tolerance=0, button='left', modifiers=[], human_like=True):
                bot.wait(4.5)

    # Right click the gate
    bot.click(x=abs_x, y=abs_y, button='right', modifiers=[], human_like=True)
    bot.wait(0.15)
    
    # Left click 50 pixels below that right click
    bot.click(x=abs_x, y=abs_y + 50, button='left', modifiers=[], human_like=True)
    bot.wait(5.10)
    bot.click(x=1812, y=179, button='left', modifiers=[], human_like=True)
    bot.wait(5)
    bot.click(x=1835, y=161, button='left', modifiers=[], human_like=True)
    bot.wait(4.5)
    bot.click(x=1871, y=132, button='left', modifiers=[], human_like=True)
    bot.wait(8)
    # find banker
    # Walk to bank on minimap
    while not bot.find_and_click_color(hex_color='#FFDE5F', region_index=7, tolerance=0, button='left', modifiers=[], human_like=True):
        bot.wait(0.1)
    bot.wait(3.0)

    # Hover and verify banker
    found_banker = False
    while not found_banker:
        hover_pos = bot.find_color(hex_color='#7A8065', region_index=3, tolerance=0)
        
        if not hover_pos:
            bot.wait(0.1)
            continue
            
        abs_x, abs_y = hover_pos
        bot.move_mouse(abs_x, abs_y, human_like=False)
        bot.wait(0.15)  # let the tooltip render before sampling region 6
        
        # Check Region 6 for #00FFFF
        if bot.find_color(hex_color='#00FFFF', region_index=6, tolerance=10):
            found_banker = True
        else:
            bot.wait(0.1)

    # Right click the banker
    bot.click(x=abs_x, y=abs_y, button='right', modifiers=[], human_like=True)
    bot.wait(0.15)
    
    # Left click 50 pixels below that right click
    bot.click(x=abs_x, y=abs_y + 50, button='left', modifiers=[], human_like=True)
    bot.wait(4.18)
    # deposit
    bot.click(x=1080, y=623, button='left', modifiers=[], human_like=True)
    bot.click(x=1081, y=623, button='left', modifiers=[], human_like=True)
    bot.wait(0.05)
# ============ EMBEDDED REGIONS ============
# Auto-generated region definitions
# Created: 2026-06-25 22:39:49
# Window: Vidyaplace 8.4.8

bot.gui.regions = [
    {'x': 954, 'y': 393, 'width': 122, 'height': 216, 'color': '#8CC787'},
    {'x': 855, 'y': 310, 'width': 311, 'height': 139, 'color': '#B3C1AB'},
    {'x': 140, 'y': 6, 'width': 11, 'height': 11, 'color': '#B3C1AB'},
    {'x': 505, 'y': 336, 'width': 1044, 'height': 493, 'color': '#FFFFFF'},
    {'x': 200, 'y': 985, 'width': 40, 'height': 40, 'color': '#0000FF'},
    {'x': 784, 'y': 479, 'width': 550, 'height': 466, 'color': '#3E353B'},
    {'x': 75, 'y': 3, 'width': 44, 'height': 15, 'color': '#00FFFF'},
    {'x': 1797, 'y': 34, 'width': 57, 'height': 104, 'color': '#7A8065'},
    {'x': 1795, 'y': 115, 'width': 35, 'height': 55, 'color': '#3E353B'}
]
bot.gui.update_region_selector()
bot.log('Loaded embedded regions')
# ============ END EMBEDDED REGIONS ============







