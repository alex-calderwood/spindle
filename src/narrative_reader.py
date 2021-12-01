from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline
from collections import defaultdict, Counter
import threading, time, sys, itertools, random, os
import spacy
from twee_utils import dedupe_in_order, passage_to_text, split_lines, unsplit_lines

PRONOUN_STOP_LIST = {'what', 'there', 'anything', 'nothing', 'it', 'something'}

# see: https://github.com/explosion/spaCy/blob/master/spacy/glossary.py
TAG_TO_PLURAL_DESC = {
     "CARDINAL": "numerals",
     "DATE": "dates",
     "EVENT": "named events",
     "FAC": "facilities",
     "GPE": "political bodies",  # think about combining with LOC
     "LANGUAGE": "languages",
     "LAW": "documents",
     "LOC": "locations",
     "MONEY": "monetary values",
     "NORP": "nationalities",
     "ORDINAL": "ordinals",
     "ORG": "organizations",
     "PERCENT": "percentages",
     "PERSON": "people",
     "PRODUCT": "products",
     "QUANTITY": "measurments",
     "TIME": "times",
     "WORK_OF_ART": "artworks",
     'PRON': 'pronouns',
}

# Whether to force a BERT download
REDOWNLOAD_BERT = False
DONE = False


def load_nlp_modules():
    global DONE

    def _animate(animate_text, finished='Loaded model.'):
        # ['|', '/', '-', '\\']
        spaces = ' ' * len(animate_text)
        text_all = [animate_text[:i + 1] for i in range(len(animate_text))]
        for c in itertools.cycle(text_all):  # ['.   ', '..  ', '... ', '....']
            if DONE:
                break
            # sys.stdout.write(f'\r{text}' + c)
            sys.stdout.write(f'-{c}                                          \r')
            sys.stdout.flush()
            time.sleep(random.uniform(0.02, 0.2))
        sys.stdout.write(f'\r{finished}                                         \r')

    text = 'Loading English... Reticulating Splines... etc...'
    DONE = False
    t = threading.Thread(target=_animate, args=(text,))
    t.start()
    os.environ["TOKENIZERS_PARALLELISM"] = "true"
    nlp = spacy.load('en_core_web_lg')
    tokenizer = AutoTokenizer.from_pretrained("./dslim/bert-base-NER", force_download=REDOWNLOAD_BERT)
    model = AutoModelForTokenClassification.from_pretrained("./dslim/bert-base-NER", force_download=REDOWNLOAD_BERT)
    ner_pipeline = pipeline("ner", model=model, tokenizer=tokenizer)
    DONE = True
    t.join()
    return ner_pipeline, nlp


ner_pipeline, nlp = load_nlp_modules()


def ner(text, verbose=False):
    """
    Extract Named Entities from a text, return a dictionary.

    :rtype dict: eg
        {
        "PER": ["Anna", "Alex"]
        }
    """
    ner_results = ner_pipeline(text)
    # Not checking that the internal entity type in each word part matches, but should...
    # same_ent_type = lambda x, y: x.split('-')[-1] == y.split('-')[-1]

    # Join multi word-part entities together
    # words at the beginning of an entity are marked B-, others are marked I-
    entities = []
    prev_beg = {}
    for i, entity in enumerate(ner_results):
        # print(prev_beg, entity)
        # print(entity['word'], entity['entity'])
        if entity['entity'].startswith('B'):
            prev_beg = entity
            entities.append(prev_beg)
        elif entity['entity'].startswith('I'):
            # I don't know why I's appear with no B's sometimes. Not sure this is the correct solution
            if not prev_beg:
                prev_beg = entity
                entities.append(prev_beg)
                continue
            # Add the intermediate word to the end of the entity
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
        e_type = ''.join(e_type.split('-')[1:])
        text = e['word']
        processed_entities[e_type].append(text)

    if verbose:
        print(processed_entities)

    return dict(processed_entities)


def parse(passage_text):
    doc = nlp(passage_text)
    pronouns = []
    for token in doc:
        if token.pos_ == 'PRON':
            pronouns.append(token.text.lower())

    return dedupe_in_order(pronouns, dont_add=PRONOUN_STOP_LIST)


#### --- Begin Author Functions --- ####
## Author functions take a list of context components and write text describing them, interpretable by a language model
## or human
def ner_author(entities):
    written_components = []

    def simplify_entity_type(ent_type):
        # Some entity types can be combined
        new_ent = ent_type.replace('GPE', 'LOC')
        return new_ent

    for ent_type in entities.keys():
        ent_type = simplify_entity_type(ent_type)
        if ent_type in TAG_TO_PLURAL_DESC.keys():
            written_components.append(
                write_named_context_component(entities[ent_type], ent_type)
            )

    return written_components


def pronouns_author(pronouns):
    return f"Pronouns referenced: {comma_sep(pronouns) if pronouns else 'None'}."


def basic_entity_author(entities):
    characters = flatten([v for k, v in entities.items() if k == 'PER'])
    locations = flatten([v for k, v in entities.items() if k == 'LOC'])

    return basic_character_author(characters) + " " + \
           basic_loc_author(locations)


def basic_character_author(characters):
    return f"Previously mentioned characters: {comma_sep(characters) if characters else 'None'}."


def basic_loc_author(locations):
    return f"Prior locations: {comma_sep(locations) if locations else 'None'}."
#### --- End Author Functions --- ####


def comma_sep(list_of):
    if not list_of:
        return ''
    elif len(list_of) == 1:
        return list_of[0]
    elif len(list_of) == 2:
        return list_of[0] + ' and ' + list_of[1]
    else:
        return ', '.join(list_of[:-1]) + ', and ' + list_of[-1]


def flatten(t):
    return [item for sublist in t for item in sublist]


def write_named_context_component(typed_entities, ent_type):
    """
    Given a list of entities (and their counts), return a string that explains them to the model.

    :return: (named entity description, entities exist)
    :rtype: (str, bool)
    """
    entities_exist = bool(typed_entities)
    plural_type_desc = TAG_TO_PLURAL_DESC.get(ent_type)
    if not plural_type_desc:
        raise RuntimeError(f'Entity type not found: {ent_type}')
    plural_type_desc = plural_type_desc.title()
    formatted_entities = comma_sep(typed_entities) if entities_exist else 'None'
    return f"Prior {plural_type_desc}: {formatted_entities}", entities_exist


def make_context_components(passage_text):
    """
    :param passage_text: the text from a single passage
    :return: a dict containing all narrative elements in the passage
    """
    return {
        'v': 1.1,  # Context version (I expect to go through a few iterations)
        'entities': ner(passage_text),
        'pronouns': parse(passage_text),
    }


def count_context_components(components, topk=8):
    """
    Turn a list of context components (dicts) into a single dict of the most relevant context components

    TODO: this is horrible and needs to be rewritten
    """
    print('j', components)
    if not components:
        return {}

    joined = {
        'pronouns': [],
        'entities': defaultdict(list),
    }
    for cc in components:
        print('cc', cc)
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
CONTEXT_COMPONENT_AUTHOR_FUNC = {
    # "entities": basic_entity_context_component,
    "entities": basic_entity_author,
    "pronouns": pronouns_author,
    "summary": lambda x: x,
}
DEFAULT_COMPONENT_FUNC = lambda x: str(x)


def write_context_text(full_context):
    """
    Turn a list of narrative elements into a string describing the context.

    :param full_context: a list, each item (a dict) corresponding to all the narrative elements in that passage
    :rtype: str
    """

    # count up top components
    top_context_components = count_context_components(full_context)
    print('top', top_context_components)

    context_text = ""
    for k, component in top_context_components.items():
        f = CONTEXT_COMPONENT_AUTHOR_FUNC.get(k, DEFAULT_COMPONENT_FUNC)
        context_text += f(component) + " "
    return context_text


if __name__ == '__main__':
    passage = """
:: her research
 Lara was able to find out that the woman she saw had been killed on that same day, the day before the storm. The storm had apparently knocked out power for days, which had made it even harder to find out more about the victim.
She also found out that the police (including Dr. Bradford) had closed the case, since the mysterious victim turned out to be a local celebrity.
This lead her to believe that the murderer(s) were still in London, and she would need to be extra careful in the future.
[[She returns her attention to the docks.|the docks]]"""
    passage = unsplit_lines(split_lines(passage)[1:])
    cleaned_passage_text = passage_to_text(passage)
    print("passage", cleaned_passage_text)
    context_components = make_context_components(cleaned_passage_text)
    print("context components", context_components)
    print(write_context_text([context_components]))
