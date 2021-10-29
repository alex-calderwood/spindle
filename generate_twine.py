import twee_utils as utils
from multiprocessing import Process
import sys, time
from queue import Queue
import subprocess
import re

generator = None
spinning = ['\\', '|', '/', '-']

verbose = False


def italic(text):
    return f'\x1B[3m{text}\x1B[0m'


def mock_generate(prompt):
    time.sleep(1)
    result = {}
    result['completion'] = """\"You don't have to answer, I've seen it a million times." She pulls out a wallet and hands you a business card.<newline>DR. CHAE YEON-SEOK<newline>SPECIALIST<newline>[["Specialist?"|specialist]]<newline>[["..."|dotdotdot]]<|end|>"""
    return result


def call_gpt_3(prompt):
    raise NotImplementedError
    result = {
        'completion': ""
    }

    return result



def generate(title):
    print('generating for title: ' + title)

    title = utils.make_title(title, with_num=False)
    prompt = utils.make_prompt(title)

    if verbose:
        print(f'title {title}')
        print(f'prompt {prompt}')

    # TODO make a spinning thing here
    if not generator:
        get_completion = mock_generate
    else:
        get_completion = call_gpt_3
    #
    # p = Process(target=mock_generate, args=(prompt, ))
    # p.start()
    # i = 0
    # while result['completion'] is None:
    #     sym = spinning[i % len(spinning)]
    #     print(sym, end='\r')
    #     time.sleep(.1)
    #     i += 1
    # p.join()
    result = get_completion(prompt)

    # Process the generated completion back into plain twee
    twee_passage = title + '\n' + utils.gen_to_twee_format_2(result['completion'])
    return twee_passage


def ask_do_gen(title):
    do_gen = 'starting'
    while not do_gen or do_gen not in 'wgrv':
        do_gen = input(
            f'(w) to write {italic(title)} yourself\n'
            f'(g) to generate {italic(title)}\n'
            f'(v) to view the written passages.\n'
            f'(f) to finish all remaining passages.\n'
            f'(W/g/f/v): '
        ).lower()
    return do_gen


def get_written_passage(title):
    """
    Have the user write a passage.
    """
    print(f':: {title}')
    passage = ''
    while True:
        dummy = input() + '\n'
        if dummy == '\n':
            break
        passage += dummy
    return utils.make_title(title) + '\n' + passage


def interactive():
    title = None
    while not title:
        title = input('enter your story title: ')

    by = input('by: ')
    by = by if by else 'alex'

    passages = []
    links_to_do = ['Start']
    links_done = set()
    while links_to_do:
        print(f'Passages to write: {links_to_do}')
        title = links_to_do.pop()
        links_done.add(title)
        do_gen = ask_do_gen(title)

        if do_gen == 'g':
            passage = generate(title)
            print(f'completed passage: {italic(passage)} \n')
        elif do_gen == 'w':
            passage = get_written_passage(title)
        elif do_gen == 'v':
            if passages:
                for p in passages:
                    print(f'{p}\n')
            else:
                print('No passages written yet.')
            links_to_do.append(title)
            links_done.remove(title)
            continue
        else:
            print('TODO')
            links_to_do.append(title)
            continue
            # finish_all()

        if utils.is_valid_passage(passage):
            passages.append(passage)
        else:
            print('Invalid twee! Must try again.')
            links_to_do.append(title)  # put it back
            links_done.remove(title)

        links = utils.get_links(passage)
        were_was = 'were' if len(links) > 1 else 'was'
        print(f"There {were_was} {len(links)} outgoing links in the completed passage{': ' + str(links) if links else ''}")
        links_to_do += links
        links_to_do = utils.dedupe_in_order(links_to_do, links_done)

    print('Done!')
    print('making twee...', end='\r')
    twee = utils.init_twee(title, by)
    for passage in passages:
        twee += passage + "\n"
    twee = re.sub(r'::\s+start', ':: Start', twee)

    filename = 'my_story.tw'
    with open(filename, 'w') as f:
        f.write(twee)
    print(f'Wrote twee to {filename}')

    html_file = filename.split('.')[0] + '.html'
    try:
        twee, error = utils.twee(filename)
        with open(html_file, 'wb') as f:
            f.write(twee)
            print(f"Wrote game to {html_file}")
    except Exception as e:
        print(f"Unable to Twee {filename} {e}")

    try:
        utils.open(html_file)
    except Exception as e:
        print(f"Unable to open {html_file} {e}")


# import curses

# classes = ["The sneaky thief", "The smarty wizard", "The proletariat"]

# def character(stdscr):
#     attributes = {}
#     curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
#     attributes['normal'] = curses.color_pair(1)
#
#     curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
#     attributes['highlighted'] = curses.color_pair(2)
#
#     c = 0  # last character read
#     option = 0  # the current option that is marked
#     while c != 10:  # Enter in ascii
#         stdscr.erase()
#         stdscr.addstr("What is your class?\n", curses.A_UNDERLINE)
#         for i in range(len(classes)):
#             if i == option:
#                 attr = attributes['highlighted']
#             else:
#                 attr = attributes['normal']
#             stdscr.addstr("{0}. ".format(i + 1))
#             stdscr.addstr(classes[i] + '\n', attr)
#         c = stdscr.getch()
#         if c == curses.KEY_UP and option > 0:
#             option -= 1
#         elif c == curses.KEY_DOWN and option < len(classes) - 1:
#             option += 1
#
#     stdscr.addstr("You chose {0}".format(classes[option]))
#     stdscr.getch()

if __name__ == '__main__':
    interactive()
