import os, re, logging
from sys import argv
import twee_utils as utils
from display import make_selection, clear, italic, bold, italic_start, italic_end
from external_model import TwineGenerator
from contextual_tree import PassageTree
from narrative_reader import BasicVersionedReader

VERBOSE = False

GEN_COUNT = 16
DEFAULT_GEN_COUNT = 16
MAX_GEN_COUNT = 99

DATA_DIR = './generated_games/'
TWEE_DIRS = ['../twee/', './twee/']

PRESET_CONFIGS = [
    # (twine generator, narrative element version, use_context)
    ("naive", 1.1, False),   
    ("context", 1.2, True),
    ("events", 1.3, True), 
] 

# Select your configuration by changing this number
# 1 - no context
# 2 - LOC and PER NER elements, pronouns
# 3 - All NER elements, pronouns, bulleted events
CONFIG = PRESET_CONFIGS[int(argv[1]) - 1] if len(argv) > 1 else PRESET_CONFIGS[2]

# Construct a contextual GPT-3 engine
generator = TwineGenerator(CONFIG[0])
# Decide which version of narrative extraction to use
PassageTree.reader = BasicVersionedReader(CONFIG[1])
USE_CONTEXT = CONFIG[2]

STORY_TITLE, BY = (None, None)

def generate(original_title, context=''):
    print('generating for title: ' + original_title)

    title_to_save = utils.make_title(original_title, process=False)  # readable by twee
    processed_title = utils.make_title(original_title, process=True)  # ready for GPT-3
    prompt = utils.make_prompt(processed_title, context=context)

    if VERBOSE:
        print(f'title {processed_title}')
        print(f'prompt {prompt}')

    completion = generator.get_completion(prompt)

    # Process the generated completion back into plain twee
    twee_passage = title_to_save + '\n' + utils.gen_to_twee_format_3(completion)
    return twee_passage


def get_command(title):
    cmd = 'starting'
    args = []
    while not cmd or cmd not in 'wgvfq':
        user_in = input(
            f'(w) to write {italic(title)} yourself\n'
            f'(g) to generate {italic(title)}\n'
            f'(v) to view the written passages.\n'
            f'(f) to generate all remaining passages.\n'
            f'(q) to terminate writing with unwritten passages.\n'
            f'(W/g/f/v/q): '
        ).lower()

        split = user_in.split()
        cmd = split[0] if split else 'nope'
        args = split[1:] if split else []

    return cmd, args


def select_passage(passages_todo):
    """
    Call curses to have the user select a passage to write next
    """
    message = 'To Do List - (Arrow Keys + Enter to Select)'
    selection, i = make_selection(passages_todo, message=message)
    return passages_todo[i]


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
        node = PassageTree(
            passage,
            raw_passage=raw_passage,
            title=utils.make_title(title),
            parent=parent,
            compute_context=compute_context
        )
        for link in links:
            link_to_parent[link] = node
        
        # Do some logging
        logging.info(f"Title\t\t{node.title}")
        logging.info(f"Passage\t\t{node.passage}")
        logging.info(f"Narrative Elements\t{str(node.narrative_elements)}\n")
        logging.info(f"Context\t\t{str(node.context_text)}" )

        node.render_root()
    else:
        print('Invalid twee! Must try again.')
        links_to_do.append(title)  # put it back
    
    try: # Save an intermediate twee file
        make_twee_text_file(STORY_TITLE, BY, passages)
    except Exception as e:
        print(f"Could not save twee file. {e}")

    return passage, passages, links_to_do, links_done, link_to_parent


def make_twee_text_file(story_title, by, passages):
    print(f'making twee...', end='\r')
    twee_text = utils.init_twee(story_title, by)
    for passage in passages:
        twee_text += passage + "\n\n"
    twee_text = re.sub(r'::\s+start', ':: Start', twee_text)

    filename = make_file_base_name(story_title)
    with open(filename, 'w') as f:
        f.write(twee_text)
    print(f'Wrote twee to {filename}')

    return filename


def make_file_base_name(story_title, extension='tw'):
    file_base = story_title.replace(' ', '_')
    file_base = os.path.join(DATA_DIR, f'{file_base}.{extension}')
    return file_base


def run_twee_file(filename):
    html_file = os.path.basename(filename).split('.')[0] + '.html'
    html_file = os.path.join(DATA_DIR, html_file)

    did_twee, did_open = False, False
    for i, twee_exec in enumerate(TWEE_DIRS):
        try:
            twee, error = utils.twee(filename, twee_exec)
            with open(html_file, 'wb') as f:
                f.write(twee)
                print(f"Wrote game to {html_file}")
                did_twee = True
        except Exception as e:
            print(f"Unable to Twee {filename} {e}")
            if i < len(twee_exec) - 1:
                print("Retrying with a new twee executable path.")

        try:
            utils.open_file(html_file)
            did_open = True
        except Exception as e:
            print(f"Unable to open {html_file} {e}")
        if did_twee and did_open:
            continue


def make_context_for_interaction(passage_title, link_to_parent):
    parent = link_to_parent[passage_title]
    context_components = PassageTree.construct_context(parent)
    context = PassageTree.reader.write_context_text(context_components)
    return context


def interactive():
    """
    Write a twine story interactively
    """

    # Get the story title and author
    STORY_TITLE = None
    while not STORY_TITLE:
        STORY_TITLE = input('enter your story title: ')
    BY = input('by: ')
    _and = ' and GPT-3'
    BY = BY + _and if BY else 'alex' + _and

    # Intialize a .log file
    logging.basicConfig(filename=make_file_base_name(STORY_TITLE, 'log'), level=logging.INFO)

    # Begin the interactive logic
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

        command, args = get_command(passage_title)
        context = make_context_for_interaction(passage_title, link_to_parent)

        # Single title commands
        if command == 'g':
            passage = generate(passage_title, context=context)
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
            gen_num = parse_gen_num(args)
            if gen_num is None:
                gen_num = len(links_to_do)
            print('gen', gen_num)
            passages, links_to_do, links_done, link_to_parent = generate_n(passages, passage_title, links_to_do, links_done, link_to_parent, n=gen_num)
            continue
        elif command == 'q':
            passages, links_to_do, links_done, link_to_parent = done(passages, passage_title, links_to_do, links_done, link_to_parent)
            continue
        else:
            raise NotImplemented(f"No command {command}. How did you get here?")

        # If we get to this point, we assume we've selected a passage
        _, passages, links_to_do, links_done, link_to_parent = retrospective(
            passage, passages, passage_title, links_to_do, links_done, link_to_parent, compute_context=USE_CONTEXT
        )

    print('Done!')
    twee_file = make_twee_text_file(STORY_TITLE, BY, passages)
    run_twee_file(twee_file)


def generate_n(passages, passage_title, links_to_do, links_done, link_to_parent, n=DEFAULT_GEN_COUNT):
    """
    Generate n passages using the defined generator.
    """
    num_generated = 0
    links_to_do.append(passage_title)  # We've already popped one but we want to generate it too
    n = min(n, MAX_GEN_COUNT)
    while links_to_do and num_generated < n:
        passage_title = links_to_do.pop(0)
        context = make_context_for_interaction(passage_title, link_to_parent)
        passage = generate(passage_title, context=context)
        _, passages, links_to_do, links_done, link_to_parent = retrospective(
            passage, passages, passage_title, links_to_do, links_done, link_to_parent, compute_context=USE_CONTEXT,
        )
        num_generated += 1
    hit_max = f'(hit maximum of {n})' if num_generated == n else ''
    input(f"done generating {num_generated} passages {hit_max}")
    return passages, links_to_do, links_done, link_to_parent


def done(passages, passage_title, links_to_do, links_done, link_to_parent):
    """
    Fill each remaining passage with nothing text.
    """
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


def parse_gen_num(args):
    if not args:
        return None
    try:
        return int(args[0])
    except ValueError as e:
        return None


if __name__ == '__main__':
    interactive()
