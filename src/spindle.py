import os, re
import twee_utils as utils
from display import make_selection, clear, italic, bold, italic_start, italic_end
from external_model import get_completion
from contextual_tree import ContextualTweeTree

spinning = ['\\', '|', '/', '-']

verbose = False

MAX_GEN_COUNT = 16

data_dir = './generated_games/'

TWEE_DIRS = ['../twee/', './twee/']


def generate(original_title):
    print('generating for title: ' + original_title)

    title_to_save = utils.make_title(original_title, process=False)  # readable by twee
    processed_title = utils.make_title(original_title, process=True)  # ready for GPT-3
    prompt = utils.make_prompt(processed_title)

    if verbose:
        print(f'title {processed_title}')
        print(f'prompt {prompt}')

    completion = get_completion(prompt)

    # Process the generated completion back into plain twee
    twee_passage = title_to_save + '\n' + utils.gen_to_twee_format_3(completion)
    return twee_passage


def get_command(title):
    do_gen = 'starting'
    while not do_gen or do_gen not in 'wgvfq':
        do_gen = input(
            f'(w) to write {italic(title)} yourself\n'
            f'(g) to generate {italic(title)}\n'
            f'(v) to view the written passages.\n'
            f'(f) to generate all remaining passages.\n'
            f'(q) to terminate writing with unwritten passages.\n'
            f'(W/g/f/v/q): '
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
    message = 'To Do List - (Arrow Keys + Enter to Select)'
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


def retrospective(raw_passage, passages, title, links_to_do, links_done, link_to_parent, compute_context=True):
    """
    Post processing of a generated passage
        - Check the validity of the passage, append back to links to do if invalid
        - Extract the outgoing links from the passage and add to the links to do
        - Process the links in each passage (GPT-3 is trained on lower case page titles)

    :param link_to_parent: a dict mapping link to parent node
    :param compute_context: whether or not to add context to the contextual nodes (can be slow)
    """

    # Even the raw passage should have invalid characters removed for use in the linguistic analysis
    raw_passage = passage = utils.remove_invalid_chars_from_passage(raw_passage)

    if utils.is_valid_passage(raw_passage):
        passage = utils.lower_case_links(raw_passage)
        links = utils.get_links(passage)
        passage, links = utils.clean_link_text(passage, links)

        passages.append(passage)
        links_done.add(title)

        were_was = 'were' if len(links) > 1 else 'was'
        print(
            f"There {were_was} {len(links)} outgoing links in the completed passage{': ' + str(links) if links else ''}"
        )
        links_to_do += links
        links_to_do = utils.dedupe_in_order(links_to_do, links_done)

        parent = link_to_parent[title]
        node = ContextualTweeTree(
            passage,
            raw_passage=raw_passage,
            title=utils.make_title(title),
            parent=parent,
            compute_context=compute_context
        )
        for link in links:
            link_to_parent[link] = node

        node.render_root()
    else:
        print('Invalid twee! Must try again.')
        links_to_do.append(title)  # put it back

    return passage, passages, links_to_do, links_done, link_to_parent


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

    did_twee, did_open = False, False
    for t in TWEE_DIRS:
        try:
            twee, error = utils.twee(filename, t)
            with open(html_file, 'wb') as f:
                f.write(twee)
                print(f"Wrote game to {html_file}")
                did_twee
        except Exception as e:
            print(f"Unable to Twee {filename} {e}")

        try:
            utils.open_file(html_file)
            did_open = True
        except Exception as e:
            print(f"Unable to open {html_file} {e}")
        if did_twee and did_open:
            continue


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
    start = 'Start'
    links_to_do = [start]
    links_done = set()
    link_to_parent = {start: None}
    while links_to_do:
        print('To Do List:', links_to_do)
        if len(links_to_do) == 1:
            passage_title = links_to_do.pop()
        else:
            passage_title = select_passage(links_to_do)
            links_to_do.remove(passage_title)

        command = get_command(passage_title)

        # Single title commands
        if command == 'g':
            passage = generate(passage_title)
            print(f'completed passage: {italic(passage)} \n')
        elif command == 'w':
            clear(f'{bold(passage_title)}\n')
            passage = human_writes(passage_title)
        # Commands not utilizing the popped title
        elif command == 'v':
            display_passages(passages)
            links_to_do.append(passage_title)  # put it back
            input('continue')
            continue
        elif command == 'f':
            passages, links_to_do, links_done, link_to_parent = generate_all(passages, passage_title, links_to_do, links_done, link_to_parent)
            continue
        elif command == 'q':
            passages, links_to_do, links_done, link_to_parent = done(passages, passage_title, links_to_do, links_done, link_to_parent)
            continue
        else:
            raise NotImplemented(f"No command {command}. How did you get here?")

        # If we get to this point, we assume we've selected a passage
        passage, passages, links_to_do, links_done, link_to_parent = retrospective(
            passage, passages, passage_title, links_to_do, links_done, link_to_parent
        )

    print('Done!')
    make_and_run_twee(story_title, by, passages)


def generate_all(passages, passage_title, links_to_do, links_done, link_to_parent):
    num_generated = 0
    links_to_do.append(passage_title)  # We've already popped one but we want to generate it too
    while links_to_do and num_generated < MAX_GEN_COUNT:
        passage_title = links_to_do.pop(0)
        passage = generate(passage_title)
        _, passages, links_to_do, links_done, link_to_parent = retrospective(
            passage, passages, passage_title, links_to_do, links_done, link_to_parent
        )
        num_generated += 1
    hit_max = f'(hit maximum of {MAX_GEN_COUNT})' if num_generated == MAX_GEN_COUNT else ''
    input(f"done generating {num_generated} passages {hit_max}")
    return passages, links_to_do, links_done, link_to_parent


def done(passages, passage_title, links_to_do, links_done, link_to_parent):
    links_to_do.append(passage_title)  # We've already popped one but we want to generate it too
    while links_to_do:
        passage_title = links_to_do.pop(0)
        passage = utils.make_title(passage_title) + "\nWhat a lazy writer. Didn\'t even get to this yet."
        print("done", passage)
        passage, passages, links_to_do, links_done, link_to_parent = \
            retrospective(passage, passages, passage_title, links_to_do, links_done, link_to_parent, compute_context=False)
    return passages, links_to_do, links_done, link_to_parent


def display_passages(passages):
    if passages:
        for p in passages:
            print(f'{p}\n')
    else:
        print('No passages written yet.')


if __name__ == '__main__':
    interactive()
