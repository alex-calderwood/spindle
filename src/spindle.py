import os, re
import twee_utils as utils
from display import make_selection

from src.external_model import get_completion

spinning = ['\\', '|', '/', '-']

verbose = False

italic_start, italic_end = ('\x1B[3m', '\x1B[0m')
bold_start, bold_end = ('\033[1m', '\033[0m')

MAX_GEN_COUNT = 16

data_dir = '../'


## Terminal Utilities ##
def clear(msg=None):
    os.system('cls' if os.name == 'nt' else 'clear')
    if msg:
        print(msg)


def italic(text):
    return f'{italic_start}{text}{italic_end}'

def bold(text):
    return f'{bold_start}{text}{bold_end}'
## End Terminal Utilities ##


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

#
# def ask_do_gen(title):
#     options = [
#         (f'write {title} yourself', 'w'),
#         (f'generate {title}', 'g'),
#         (f'view the written passages.','v'),
#         (f'generate all remaining passages.','g'),
#     ]
#
#     selection, i = make_selection([c[0] for c in options])
#
#     return options[i][1]


def select_passage(passages_todo):
    """
    Call curses to have the user select a passage to write next
    """
    message = 'To Do List (Remaining passages to write)'
    selection, i = make_selection(passages_todo, message=message)
    return selection


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
    Post processing of a generated passage
        - Check the validity of the passage, append back to links to do if invalid
        - Extract the outgoing links from the passage and add to the links to do
        - Process the links in each passage (GPT-3 is trained on lower case page titles)
    """
    if utils.is_valid_passage(passage):
        passage = utils.lower_case_links(passage)
        links = utils.get_links(passage)

        passages.append(passage)
        links_done.add(title)

        were_was = 'were' if len(links) > 1 else 'was'
        print(
            f"There {were_was} {len(links)} outgoing links in the completed passage{': ' + str(links) if links else ''}")
        links_to_do += links
        links_to_do = utils.dedupe_in_order(links_to_do, links_done)
    else:
        print('Invalid twee! Must try again.')
        links_to_do.append(title)  # put it back

    return passage, passages, links_to_do, links_done


def make_and_run_twee(story_title, by, passages):
    print('making twee...', end='\r')
    twee = utils.init_twee(story_title, by)
    for passage in passages:
        twee += passage + "\n\n"
    twee = re.sub(r'::\s+start', ':: Start', twee)

    filename = os.path.join(data_dir, 'my_story.tw')
    with open(filename, 'w') as f:
        f.write(twee)
    print(f'Wrote twee to {filename}')

    html_file = os.path.basename(filename).split('.')[0] + '.html'
    html_file = os.path.join(data_dir, html_file)

    try:
        twee, error = utils.twee(filename)
        with open(html_file, 'wb') as f:
            f.write(twee)
            print(f"Wrote game to {html_file}")
    except Exception as e:
        print(f"Unable to Twee {filename} {e}")

    try:
        utils.open_file(html_file)
    except Exception as e:
        print(f"Unable to open {html_file} {e}")


def interactive():
    """
    Write a twine story interactively
    """
    story_title = None
    while not story_title:
        story_title = input('enter your story title: ')

    by = input('by: ')
    _and = ' and GPT-3'
    by = by + _and if by else 'alex' + _and

    passages = []
    links_to_do = ['Start']
    links_done = set()
    while links_to_do:
        print('todo', links_to_do)
        if len(links_to_do) == 1:
            passage_title = links_to_do.pop()
        else:
            passage_title = select_passage(links_to_do)
            links_to_do.remove(passage_title)

        do_gen = ask_do_gen(passage_title)

        if do_gen == 'g':
            passage = generate(passage_title)
            print(f'completed passage: {italic(passage)} \n')
        elif do_gen == 'w':
            clear(f'{bold(passage_title)}\n')
            passage = human_writes(passage_title)
        elif do_gen == 'v':
            if passages:
                for p in passages:
                    print(f'{p}\n')
            else:
                print('No passages written yet.')
            links_to_do.append(passage_title)  # put it back
            input('continue')
            continue
        else:  # f
            counter = 0
            while links_to_do and counter < MAX_GEN_COUNT:
                passage = generate(links_to_do.pop(0))
                passage, passages, links_to_do, links_done = retrospective(passage, passages, passage_title, links_to_do, links_done)
                counter += 1
            if counter == MAX_GEN_COUNT:
                print(f'generated max number of pages ({MAX_GEN_COUNT})')
            input('continue')
            continue

        # If we get to this point, we assume we've selected a passage
        passage, passages, links_to_do, links_done = retrospective(passage, passages, passage_title, links_to_do, links_done)

    print('Done!')
    make_and_run_twee(story_title, by, passages)


if __name__ == '__main__':
    interactive()
