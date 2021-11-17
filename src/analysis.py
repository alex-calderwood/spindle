from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline
from collections import defaultdict, Counter
import threading, time, sys, itertools, random, os
import spacy
from twee_utils import dedupe_in_order
import numpy as np

PRONOUN_STOP_LIST = {'what', 'there', 'anything', 'nothing', 'it', 'something'}


def load_nlp_modules():
    def _animate(text, finished='Loaded model.'):
        # ['|', '/', '-', '\\']
        spaces = ' ' * len(text)
        text_all = [text[:i + 1] for i in range(len(text))]
        for c in itertools.cycle(text_all):  # ['.   ', '..  ', '... ', '....']
            if done:
                break
            # sys.stdout.write(f'\r{text}' + c)
            sys.stdout.write(f'-{c}                                          \r')
            sys.stdout.flush()
            time.sleep(random.uniform(0.02, 0.2))
        sys.stdout.write(f'\r{finished}                                         \r')

    text = 'Loading English... Reticulating Splines... etc...'
    done = False
    t = threading.Thread(target=_animate, args=(text,))
    t.start()
    os.environ["TOKENIZERS_PARALLELISM"] = "true"
    nlp = spacy.load('en_core_web_lg')
    tokenizer = AutoTokenizer.from_pretrained("./dslim/bert-base-NER")
    model = AutoModelForTokenClassification.from_pretrained("./dslim/bert-base-NER")
    ner_pipline = pipeline("ner", model=model, tokenizer=tokenizer)
    done = True
    t.join()
    return ner_pipline, nlp


ner_pipeline, nlp = load_nlp_modules()


def ner(text):
    """
    Extract Named Entities from a text, return a dictionary.

    :rtype dict: eg
        {
        "B-PER": ["Anna", "Alex"]
        }
    """
    ner_results = ner_pipeline(text)
    # Not checking that the internal entity type in each word part matches, but should...
    # same_ent_type = lambda x, y: x.split('-')[-1] == y.split('-')[-1]
    entities = []
    prev_beg = {}
    for i, entity in enumerate(ner_results):
        # print(entity['word'], entity['entity'])
        if entity['entity'].startswith('B'):
            prev_beg = entity
            entities.append(prev_beg)
        elif entity['entity'].startswith('I'):
            if entity['word'].startswith('##'):
                word = entity['word'][2:]
            else:
                word = ' ' + entity['word']
            prev_beg['word'] += word
        else:
            raise Exception("How?")

    processed_entities = defaultdict(list)
    for e in entities:
        e_type = e['entity']
        text = e['word']
        processed_entities[e_type].append(text)

    return dict(processed_entities)


def parse(passage_text):
    doc = nlp(passage_text)
    pronouns = []
    for token in doc:
        if token.pos_ == 'PRON':
            pronouns.append(token.text.lower())

    return dedupe_in_order(pronouns, dont_add=PRONOUN_STOP_LIST)


def comma_sep(list_of):
    if not list_of:
        return ''
    elif len(list_of) == 1:
        return list_of[0]
    elif len(list_of) == 2:
        return list_of[0] + ' and ' + list_of[1]
    else:
        return ', '.join(list_of[:-1]) + ', and ' + list_of[-1]


def entity_context_component(entities):
    characters = list(np.array([v for k, v in entities.items() if k.endswith('PER')]).flatten())
    locations = list(np.array([v for k, v in entities.items() if k.endswith('LOC')]).flatten())

    return character_context_component(characters) + " " + \
        loc_context_component(locations)


def character_context_component(characters):
    return f"Previously mentioned characters: {comma_sep(characters) if characters else 'None'}."


def loc_context_component(locations):
    if not locations:
        locations = 'None'
    else:
        locations = comma_sep(locations)
    return f"Prior locations: {locations}."


def pronouns_context_component(pronouns):
    return f"Pronouns referenced: {comma_sep(pronouns) if pronouns else 'None'}."


def make_context_components(passage_text):
    return {
        'v': 1.1,  # Context version (I expect to go through a few iterations)
        'entities': ner(passage_text),
        'pronouns': parse(passage_text),
    }


def join_context_components(context, topk=8):
    """
    Turn a list of context components (dicts) into a single dict of the most relevant context components

    TODO: this is horrible and needs to be rewritten
    """
    if not context:
        return {}

    joined = {
        'pronouns': [],
        'entities': defaultdict(list),
    }
    for cc in context:
        joined['pronouns'] += cc['pronouns']
        for k, v in cc['entities'].items():
            joined['entities'][k] += v

    counted = {
        'pronouns': Counter(joined['pronouns']),
        'entities': {}
    }
    for ent_type, entities in joined['entities'].items():
        counted['entities'][ent_type] = Counter(entities)

    top_context_components = {}
    top_context_components['pronouns'] = [p for p, count in counted['pronouns'].most_common(topk)]
    top_context_components['entities'] = {
        ent_type: entities.most_common(topk) for ent_type, entities in counted['entities'].items()
    }
    for ent_type, entities in top_context_components['entities'].items():
        top_context_components['entities'][ent_type] = [e for (e, count) in entities]

    return top_context_components


# map from context component to a function that writes text specific to that component type
CONTEXT_COMPONENT_FUNC = {
    "entities": entity_context_component,
    "pronouns": pronouns_context_component,
    "summary": lambda x: x,
}
DEFAULT_COMPONENT_FUNC = lambda x: str(x)


def write_context_text(components):
    """
    Turn a dict of context information into a paragraph of text describing the passage's context
    """

    # count up top components
    top_context_components = join_context_components(components)

    context_text = ""
    for k, component in top_context_components.items():
        f = CONTEXT_COMPONENT_FUNC.get(k, DEFAULT_COMPONENT_FUNC)
        context_text += f(component) + " "
    return context_text
