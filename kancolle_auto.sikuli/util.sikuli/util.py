import ConfigParser
from sikuli import *
from random import uniform, randint, choice
from time import sleep as tsleep, strftime
from re import match

Settings.OcrTextRead = True
util_settings = {}

def get_util_config():
    global util_settings
    log_msg("Reading config file")
    # Change paths and read config.ini
    os.chdir(getBundlePath())
    os.chdir('..')
    config = ConfigParser.ConfigParser()
    config.read('config.ini')
    # Set user settings
    # 'General'/misc settings
    util_settings['paranoia'] = 0 if config.getint('General', 'Paranoia') < 0 else config.getint('General', 'Paranoia')
    util_settings['sleep_mod'] = 0 if config.getint('General', 'SleepModifier') < 0 else config.getint('General', 'SleepModifier')

# Custom sleep() function to make the sleep period more variable. Takes base (minimum)
# sleep length and flex sleep length, for a max sleep length of base + flex. If
# the flex sleep length is not defined, the max sleep length is base * 2.
# The lower and upper bounds can be adjusted by the SleepModifier setting.
def sleep(base, flex=-1):
    global util_settings
    if flex == -1:
        tsleep(uniform(base, base * 2) + util_settings['sleep_mod'])
    else:
        tsleep(uniform(base, flex) + util_settings['sleep_mod'])

# Custom function to get timer value of Kancolle (in ##:##:## format). Attempts
# to fix values in case OCR grabs the wrong characters.
def check_timer(kc_window, timer_ref, dir, width):
    ocr_matching = True
    while ocr_matching:
        if isinstance(timer_ref, str):
            if dir == 'r':
                timer = find(timer_ref).right(width).text().encode('utf-8')
            elif dir == 'l':
                timer = find(timer_ref).left(width).text().encode('utf-8')
        elif isinstance(timer_ref, Match):
            if dir == 'r':
                timer = timer_ref.right(width).text().encode('utf-8')
            elif dir == 'l':
                timer = timer_ref.left(width).text().encode('utf-8')
        ocr_matching, timer = ocr_check(timer)
    return timer

# OCR character corrections and check
def ocr_check(timer):
    timer = (
        timer.replace('O', '0').replace('o', '0').replace('D', '0')
        .replace('Q', '0').replace('@', '0').replace('l', '1').replace('I', '1')
        .replace('[', '1').replace(']', '1').replace('|', '1').replace('!', '1')
        .replace('Z', '2').replace('S', '5').replace('s', '5').replace('$', '5')
        .replace('B', '8').replace(':', '8').replace(' ', '')
    )
    if len(timer) == 8:
        timer = list(timer)
        timer[2] = ':'
        timer[5] = ':'
        timer = ''.join(timer)
        m = match(r'^\d{2}:\d{2}:\d{2}$', timer)
        if m:
            ocr_matching = False
            log_msg("Got valid timer (%s)!" % timer)
            return (False, timer)
    else:
        log_warning("Got invalid timer (%s)... trying again!" % timer)
        sleep(1)
        return (True, timer)

# Random Click action. Offsets the mouse into a random point within the
# matching image/pattern before clicking.
def rclick(kc_window, pic, expand=[]):
    reset_mouse = False
    if len(expand) == 0:
        # This slows down the click actions, but it looks for the pattern and
        # finds the size of the image from the resulting Pattern object.
        m = match(r'M\[\d+\,\d+ (\d+)x(\d+)\]', str(find(pic)))
        if m:
            # If a match is found and the x,y sizes can be ascertained, generate
            # the random offsets. Otherwise, just click the damn middle.
            x_width = int(m.group(1)) / 2
            y_height = int(m.group(2)) / 2
            expand = [-x_width, x_width, -y_height, y_height]
    else:
        reset_mouse = True
    if len(expand) == 4:
        if isinstance(pic, str):
            pic = Pattern(pic).targetOffset(int(uniform(expand[0], expand[1])), int(uniform(expand[2], expand[3])))
        elif isinstance(pic, Pattern):
            pic = pic.targetOffset(int(uniform(expand[0], expand[1])), int(uniform(expand[2], expand[3])))
    kc_window.click(pic)
    if reset_mouse:
        kc_window.mouseMove(Location(kc_window.x + 100, kc_window.y + 100))

# Random navigation actions.
def rnavigation(kc_window, destination, max=0):
    global util_settings
    # Look at all the things we can click!
    menu_main_options = ['menu_main_sortie.png', 'menu_main_fleetcomp.png', 'menu_main_resupply.png',
        'menu_main_equip.png', 'menu_main_repair.png', 'menu_main_development.png']
    menu_top_options = ['menu_top_profile.png', 'menu_top_encyclopedia.png', 'menu_top_inventory.png',
        'menu_top_furniture.png', 'menu_top_shop.png', 'menu_top_quests.png']
    menu_side_options = ['menu_side_fleetcomp.png', 'menu_side_resupply.png', 'menu_side_equip.png',
        'menu_side_repair.png', 'menu_side_development.png']
    menu_sortie_options = ['sortie_combat.png', 'sortie_expedition.png', 'sortie_pvp.png']
    menu_sortie_top_options = ['sortie_top_combat.png', 'sortie_top_expedition.png', 'sortie_top_pvp.png']
    # Set max evasion steps
    if max == 0:
        # If max evasion was not defined by the function call, use paranoia
        # setting from config
        max = util_settings['paranoia']
    else:
        if util_settings['paranoia'] < max:
            # If max evasion was defined by the function call, but the paranoia
            # setting from config is shorter, use the paranoia setting
            max = util_settings['paranoia']
    evade_count = randint(0, max)
    # Figure out where we are
    current_location = ''
    if kc_window.exists('menu_main_sortie.png'):
        current_location = 'home'
    elif kc_window.exists('menu_side_home.png'):
        current_location = 'sidemenu'
    elif kc_window.exists('menu_top_home.png'):
        current_location = 'topmenu'
    else:
        current_location = 'other'
    # Random navigations, depending on where we are, and where we want to go
    kc_window.mouseMove(Location(kc_window.x + 100, kc_window.y + 100))
    if current_location == 'home':
        # Starting from home screen
        if destination == 'home':
            # Already at home
            pass
        elif destination == 'refresh_home':
            # Refresh home
            log_msg("Refreshing home with %d or less sidestep(s)!" % (evade_count))
            rchoice = rnavigation_chooser(menu_top_options + menu_main_options, [])
            wait_and_click(kc_window, rchoice)
            sleep(2)
            evade_count -= 1
            if rchoice.startswith('menu_top'):
                # At top menu item; hit the home button until we get home (Akashi/Ooyodo, go away)
                while not kc_window.exists('menu_main_sortie.png'):
                    wait_and_click(kc_window, 'menu_top_home.png', 10)
                    sleep(2)
            elif rchoice.startswith('menu_main'):
                if evade_count == 0:
                    wait_and_click(kc_window, 'menu_side_home.png')
                else:
                    rchoice = rnavigation_chooser(menu_side_options, ['menu_side_' + rchoice[10:]])
                    while evade_count > 0:
                        rchoice = rnavigation_chooser(menu_side_options, [rchoice])
                        wait_and_click(kc_window, rchoice)
                        sleep(2)
                        evade_count -= 1
                    wait_and_click(kc_window, 'menu_side_home.png')
        elif destination in ['combat', 'expedition']:
            # Go to combat and expedition menu
            log_msg("Navigating to %s menu with %d sidestep(s)!" % (destination, evade_count))
            wait_and_click(kc_window, 'menu_main_sortie.png')
            kc_window.mouseMove(Location(kc_window.x + 100, kc_window.y + 100))
            sleep(2)
            if evade_count == 0:
                wait_and_click(kc_window, 'sortie_' + destination + '.png')
            else:
                rchoice = rnavigation_chooser(menu_sortie_options, ['sortie_' + destination + '.png'])
                wait_and_click(kc_window, rchoice)
                kc_window.mouseMove(Location(kc_window.x + 100, kc_window.y + 100))
                evade_count -= 1
                while evade_count > 0:
                    if rchoice.startswith('sortie_top'):
                        rchoice = rnavigation_chooser(menu_sortie_top_options, [rchoice, 'sortie_top_' + destination + '.png'])
                    else:
                        rchoice = rnavigation_chooser(menu_sortie_top_options, ['sortie_top_' + rchoice[7:], 'sortie_top_' + destination + '.png'])
                    wait_and_click(kc_window, rchoice)
                    sleep(2)
                    evade_count -= 1
                wait_and_click(kc_window, 'sortie_top_' + destination + '.png')
        else:
            # Go to and side menu sub screen
            log_msg("Navigating to %s screen with %d sidestep(s)!" % (destination, evade_count))
            if evade_count == 0:
                wait_and_click(kc_window, 'menu_main_' + destination + '.png')
            else:
                rchoice = rnavigation_chooser(menu_main_options, ['menu_main_' + destination + '.png'])
                wait_and_click(kc_window, rchoice)
                evade_count -= 1
                while evade_count > 0:
                    if rchoice.startswith('menu_main'):
                        rchoice = rnavigation_chooser(menu_side_options, ['menu_side_' + rchoice[10:], 'sortie_top_' + destination + '.png'])
                    else:
                        rchoice = rnavigation_chooser(menu_side_options, [rchoice, 'sortie_top_' + destination + '.png'])
                    wait_and_click(kc_window, rchoice)
                    sleep(2)
                    evade_count -= 1
                wait_and_click(kc_window, 'menu_side_' + destination + '.png')
        sleep(2)
    if current_location == 'sidemenu':
        # Starting from a main menu item screen
        if destination == 'home' or destination == 'refresh_home':
            # Go or refresh home
            log_msg("Going home with %d or less sidestep(s)!" % (evade_count))
            if evade_count == 0:
                wait_and_click(kc_window, 'menu_side_home.png')
            else:
                rchoice = rnavigation_chooser(menu_top_options + menu_side_options, [])
                while evade_count > 0:
                    rchoice = rnavigation_chooser(menu_top_options + menu_side_options, [rchoice])
                    wait_and_click(kc_window, rchoice)
                    sleep(2)
                    evade_count -= 1
                    if rchoice.startswith('menu_top'):
                        # At top menu item; hit the home button until we get home (Akashi/Ooyodo, go away)
                        while not kc_window.exists('menu_main_sortie.png'):
                            wait_and_click(kc_window, 'menu_top_home.png', 10)
                            sleep(2)
                        # This takes us back to home immediately, so no more random menus
                        evade_count = 0
                    else:
                        # Still at side menu item, so continue as normal
                        if evade_count == 0:
                            # Unless that was the last random menu item; then go home
                            wait_and_click(kc_window, 'menu_side_home.png')
        else:
            # Go to another main menu item screen
            log_msg("Navigating to %s screen with %d sidestep(s)!" % (destination, evade_count))
            if evade_count == 0:
                wait_and_click(kc_window, 'menu_side_' + destination + '.png')
            else:
                rchoice = rnavigation_chooser(menu_side_options, ['menu_side_' + destination + '.png'])
                while evade_count > 0:
                    rchoice = rnavigation_chooser(menu_side_options, [rchoice, 'menu_side_' + destination + '.png'])
                    wait_and_click(kc_window, rchoice)
                    evade_count -= 1
                    sleep(2)
                wait_and_click(kc_window, 'menu_side_' + destination + '.png')
        sleep(2)
    if current_location == 'topmenu':
        # Starting from top menu item. Theoretically, the script should never
        # attempt to go anywhere but home from here
        if destination in ['home', 'refresh_home']:
            log_msg("Going home!")
            # At top menu item; hit the home button until we get home (Akashi/Ooyodo, go away)
            while not kc_window.exists('menu_main_sortie.png'):
                wait_and_click(kc_window, 'menu_top_home.png', 10)
                sleep(2)
    kc_window.mouseMove(Location(kc_window.x + 100, kc_window.y + 100))

# Helper function for random navigator for choosing random items from an array
def rnavigation_chooser(options, exclude):
    return choice([i for i in options if i not in exclude])

# common Sikuli actions
def check_and_click(kc_window, pic, expand=[]):
    if kc_window.exists(pic):
        rclick(kc_window, pic, expand)
        return True
    return False

def wait_and_click(kc_window, pic, time=5, expand=[]):
    if time:
        kc_window.wait(pic, time)
    else:
        kc_window.wait(pic)
    rclick(kc_window, pic, expand)

# log colors
class color:
    MSG = '\033[94m'
    SUCCESS = '\033[92m'
    WARNING = '\033[93m'
    ERROR = '\033[91m'
    END = '\033[0m'

def format(msg):
    now = strftime("%Y-%m-%d %H:%M:%S")
    return "[%s] %s" % (now, msg)

def log_msg(msg):
    print "%s%s%s" % (color.MSG, format(msg), color.END)

def log_success(msg):
    print "%s%s%s" % (color.SUCCESS, format(msg), color.END)

def log_warning(msg):
    print "%s%s%s" % (color.WARNING, format(msg), color.END)

def log_error(msg):
    print "%s%s%s" % (color.ERROR, format(msg), color.END)
