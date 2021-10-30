import twee_utils as utils
from multiprocessing import Process
import sys, time
from queue import Queue
import subprocess
import re
import openai
import os

openai.api_key = os.getenv("OPENAI_KEY")

spinning = ['\\', '|', '/', '-']

verbose = False

italic_start, italic_end = ('\x1B[3m', '\x1B[0m')

MAX_GEN_COUNT = 10

def italic(text):
    return f'{italic_start}{text}{italic_end}'


def mock_generate(link_name):
    time.sleep(1)
    result = {}
    result['completion'] = """\"You don't have to answer, I've seen it a million times." She pulls out a wallet and hands you a business card.<newline>DR. CHAE YEON-SEOK<newline>SPECIALIST<newline>[["Specialist?"|specialist]]<newline>[["..."|dotdotdot]]<|end|>"""
    return result


def call_gpt_3(prompt):

    response = openai.Completion.create(
        model='curie:ft-user-wmco7qacght9seweh8jgp4ib-2021-10-28-04-55-18',
        prompt=prompt,
        temperature=0.7,
        max_tokens=1000,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        stop=utils.END,
    )

    return response['choices'][0]['text']


# Decide which generator to use (GPT-3 or mock)
get_completion = call_gpt_3


def generate(original_title):
    print('generating for title: ' + original_title)

    title_to_save = utils.make_title(original_title, with_num=False, process=False)   # readable by twee
    processed_title = utils.make_title(original_title, with_num=False, process=True)  # ready for GPT-3
    prompt = utils.make_prompt(processed_title)

    if verbose:
        print(f'title {processed_title}')
        print(f'prompt {prompt}')

    completion = get_completion(prompt)

    # Process the generated completion back into plain twee
    twee_passage = title_to_save + '\n' + utils.gen_to_twee_format_2(completion)
    return twee_passage


def ask_do_gen(title):
    do_gen = 'starting'
    while not do_gen or do_gen not in 'wgvf':
        do_gen = input(
            f'(w) to write {italic(title)} yourself\n'
            f'(g) to generate {italic(title)}\n'
            f'(v) to view the written passages.\n'
            f'(f) to finish all remaining passages.\n'
            f'(W/g/f/v): '
        ).lower()
    return do_gen


def human_writes(title):
    """
    Have the user write a passage.
    """
    passage = ''
    while True:
        dummy = input(italic_start) + '\n'
        if dummy == '\n':
            print(italic_end, end='')
            break
        passage += dummy
    return utils.make_title(title) + '\n' + passage


def retrospective(passage, passages, title, links_to_do, links_done):
    """
    TODO: Describe
    """
    if utils.is_valid_passage(passage):
        passages.append(passage)
        links_done.add(title)
    else:
        print('Invalid twee! Must try again.')
        links_to_do.append(title)  # put it back

    links = utils.get_links(passage)
    were_was = 'were' if len(links) > 1 else 'was'
    print(f"There {were_was} {len(links)} outgoing links in the completed passage{': ' + str(links) if links else ''}")
    links_to_do += links
    links_to_do = utils.dedupe_in_order(links_to_do, links_done)

    return passages, links_to_do, links_done


def interactive():
    title = None
    while not title:
        title = input('enter your story title: ')

    by = input('by: ')
    by = by + ' and gpt-3' if by else 'alex and gpt-3'

    passages = []
    links_to_do = ['Start']
    links_done = set()
    while links_to_do:
        print(f'Passages to write: {links_to_do}')
        title = links_to_do.pop()
        do_gen = ask_do_gen(title)

        if do_gen == 'g':
            passage = generate(title)
            print(f'completed passage: {italic(passage)} \n')
            passages, links_to_do, links_done = retrospective(passage, passages, title, links_to_do, links_done)
        elif do_gen == 'w':
            passage = human_writes(title)
            passages, links_to_do, links_done = retrospective(passage, passages, title, links_to_do, links_done)
        elif do_gen == 'v':
            if passages:
                for p in passages:
                    print(f'{p}\n')
            else:
                print('No passages written yet.')
            links_to_do.append(title)
        else:  # f
            counter = 0
            while links_to_do and counter < MAX_GEN_COUNT:
                passage = generate(links_to_do.pop())
                passages, links_to_do, links_done = retrospective(passage, passages, title, links_to_do, links_done)
                counter += 1
            if counter == MAX_GEN_COUNT:
                print(f'generated max number of pages ({MAX_GEN_COUNT})')


    print('Done!')
    print('making twee...', end='\r')
    twee = utils.init_twee(title, by)
    for passage in passages:
        twee += passage + "\n\n"
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
