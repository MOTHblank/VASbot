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

    # close bank, use ectofuntus
    bot.click(x=1092, y=344, button='left', modifiers=[], human_like=True)
    bot.wait(0.6)
    bot.click(x=1752, y=806, button='left', modifiers=[], human_like=True)
    bot.wait(3)

    # pray (keep trying each click until it finds the color)
    for i in range(40):
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
        # else: it was Necrovarus, loop back and try finding B3C1AB again

    bot.click(x=abs_x, y=abs_y, button='left', modifiers=[], human_like=False)
    bot.wait(3)
    bot.click(x=220, y=1035, button='left', modifiers=[], human_like=True)

    bot.wait(0.5)  # pause between major phases

    # pray again (keep trying each click until it finds the color)
    for i in range(20):
        while not bot.find_and_click_color(hex_color='#8CC787', region_index=3, tolerance=10, button='left', modifiers=[], human_like=False):
            bot.wait(0.1)
        bot.wait(0.6)  # let the ectofuntus animation cycle

    bot.wait(0.5)  # pause between major phases

    # walk to gate
    bot.click(x=1812, y=143, button='left', modifiers=[], human_like=True)
    bot.wait(5)
    # find gate
    bot.click(x=919, y=573, button='right', modifiers=[], human_like=True)
    bot.click(x=928, y=616, button='left', modifiers=[], human_like=True)
    bot.wait(2.10)
    bot.click(x=1812, y=179, button='left', modifiers=[], human_like=True)
    bot.wait(4.73)
    bot.click(x=1835, y=161, button='left', modifiers=[], human_like=True)
    bot.wait(3.39)
    bot.click(x=1871, y=132, button='left', modifiers=[], human_like=True)
    bot.wait(9.48)
    # find banker
    bot.click(x=1172, y=857, button='right', modifiers=[], human_like=True)
    bot.click(x=1171, y=900, button='left', modifiers=[], human_like=True)
    bot.wait(4.18)
    # deposit
    bot.click(x=1080, y=623, button='left', modifiers=[], human_like=True)
    bot.click(x=1081, y=623, button='left', modifiers=[], human_like=True)
    bot.wait(0.05)
# ============ EMBEDDED REGIONS ============
# Auto-generated region definitions
# Created: 2026-06-25 12:50:35
# Window: Vidyaplace 8.4.8

bot.gui.regions = [
    {'x': 954, 'y': 393, 'width': 122, 'height': 216, 'color': '#8CC787'},
    {'x': 855, 'y': 310, 'width': 311, 'height': 139, 'color': '#B3C1AB'},
    {'x': 140, 'y': 6, 'width': 11, 'height': 11, 'color': '#B3C1AB'},
    {'x': 505, 'y': 336, 'width': 1044, 'height': 493, 'color': '#FFFFFF'}
]
bot.gui.update_region_selector()
bot.log('Loaded embedded regions')
# ============ END EMBEDDED REGIONS ============