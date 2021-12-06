import curses
import os

## Terminal Utilities ##
italic_start, italic_end = ('\x1B[3m', '\x1B[0m')
bold_start, bold_end = ('\033[1m', '\033[0m')


def clear(msg=None):
    os.system('cls' if os.name == 'nt' else 'clear')
    if msg:
        print(msg)


def italic(text):
    return f'{italic_start}{text}{italic_end}'


def bold(text):
    return f'{bold_start}{text}{bold_end}'
## End Terminal Utilities #


def _make_selection(stdscr, classes, message='(select one)'):
    """
    This function was originally branched from https://stackoverflow.com/a/45577262/5009004

    :return: option, classes index
    :rtype: (str, int)
    """
    attributes = {}
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    attributes['normal'] = curses.color_pair(1)

    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
    attributes['highlighted'] = curses.color_pair(2)

    c = 0  # last character read
    option = 0  # the current option that is marked
    while c != 10:  # Enter in ascii
        stdscr.erase()
        stdscr.addstr(f"{message}\n", curses.A_UNDERLINE)
        for i in range(len(classes)):
            if i == option:
                attr = attributes['highlighted']
            else:
                attr = attributes['normal']
            stdscr.addstr(f"{i + 1}. ")
            stdscr.addstr(classes[i] + '\n', attr)
        c = stdscr.getch()
        if c == curses.KEY_UP and option > 0:
            option -= 1
        elif c == curses.KEY_DOWN and option < len(classes) - 1:
            option += 1

    # stdscr.addstr("You chose {0}".format(classes[option]))
    # stdscr.getch()

    return classes[option], option


def make_selection(classes, *args, **kwargs):
    print('debug classes', classes)
    return curses.wrapper(_make_selection, classes, *args, **kwargs)


if __name__ == '__main__':
    classes = [
        "The sneaky thief", "The smarty wizard", "The proletariat"
    ]

    (selection, i) = make_selection(classes)
    print(selection, i)
