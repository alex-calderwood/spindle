import twee_utils as utils

generator = None


def mock_generate(prompt):
    return """\"You don't have to answer, I've seen it a million times." She pulls out a wallet and hands you a business card.<newline>DR. CHAE YEON-SEOK<newline>SPECIALIST<newline>[["Specialist?"|specialist]]<newline>[["..."|specialist]]<|end|>"""


def call_gpt_3(prompt):
    raise NotImplementedError
    return ''


def generate(title):
    print('generating for title: ' + title)

    title = utils.make_title(title, with_num=False)
    prompt = utils.make_prompt(title)

    print(f'title {title}')
    print(f'prompt {prompt}')

    # TODO make a spinning thing here
    if not generator:
        completion = mock_generate(prompt)
    else:
        completion = call_gpt_3(prompt)

    # Process the generated completion back into plain twee
    twee_passage = title + '\n' + utils.gen_to_twee_format_2(completion)
    return twee_passage


def interactive():
    title = None
    while not title:
        title = input('enter a title for your passage: ')

    go = True
    while go:
        passage = generate(title)
        print(f'completed passage: {passage}')
        links = utils.get_links(passage)
        print(f'links {links}')
        go = False


if __name__ == '__main__':
    interactive()