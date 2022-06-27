import os
from abc import ABC, abstractmethod
from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline
from collections import defaultdict, Counter
import threading, time, sys, itertools, random, os
import spacy, textacy
from twee_utils import dedupe_in_order, passage_to_text, split_lines, unsplit_lines

PRONOUN_STOP_LIST = {'what', 'there', 'anything', 'nothing', 'it', 'something', 'everything', 'all', 'some'}

# BERT NER LIST
# O Outside of a named entity
# B-MIS	Beginning of a miscellaneous entity right after another miscellaneous entity
# I-MIS	Miscellaneous entity
# B-PER	Beginning of a person’s name right after another person’s name
# I-PER	Person’s name
# B-ORG	Beginning of an organization right after another organization
# I-ORG	organization
# B-LOC	Beginning of a location right after another location
# I-LOC	Location
TAG_TO_PLURAL_DESC = {
    "LOC": "locations",
    "PER": "people",
    "MISC": "other entities",
    "ORG": "organizations",
    # SPACY NER LIST https://github.com/explosion/spaCy/blob/master/spacy/glossary.py
    # "CARDINAL": "numerals",
    # "DATE": "dates",
    # "EVENT": "named events",
    # "FAC": "facilities",
    # "GPE": "political bodies",
    # "LANGUAGE": "languages",
    # "LAW": "documents",
    # "MONEY": "monetary values",
    # "NORP": "nationalities",
    # "ORDINAL": "ordinals",
    # "PERCENT": "percentages",
    # "PRODUCT": "products",
    # "QUANTITY": "measurments",
    # "TIME": "times",
    # "WORK_OF_ART": "artworks",
    # 'PRON': 'pronouns',
}

# We always want to mention how many locations, people there are in the context, even if there are 0
ENTS_TO_ALWAYS_INCLUDE = ['LOC', 'PER']

# Whether to force a BERT download
REDOWNLOAD_BERT = True
DONE = False
MAX_EVENTS_LENGTH = 16
DEFAULT_COMPONENT_FUNC = lambda x: str(x)


class NarrativeReader(ABC):
    @abstractmethod
    def write_context_text(self, full_context):
        """
        Turn a list of narrative elements into a string describing the context.
        Our implementation of X from [TODO reference paper]

        :param full_context: a list, each item (a dict) corresponding to all the narrative elements in that passage
        :rtype: str
        """
        pass


    def make_context_components(self, passage_text):
        """
        Produce a narrative reading from the passage text, ie a set of context components s
        uch as entities and characters referenced in the passage text.
        
        Our implementation of R from [TODO reference paper]

        :param passage_text: the text from a single passage
        :return: a dict containing all narrative elements in the passage
        """
        pass

 

class BasicVersionedReader(NarrativeReader):
    # AnyTree Docs: https://anytree.readthedocs.io/en/2.8.0/
    def __init__(self, v):
        self.set_extraction_version(v)
        self.author_functions = self._get_author_functions(self.extraction_version)

    def __str__(self):
        return f'<BasicVersionedReader v{self.extraction_version}>'

    def set_extraction_version(self, v):
        assert(1.1 <= v <= 1.3)
        print(f"Narrative extraction set to v{v}")
        self.extraction_version = v

    def _get_author_functions(self, extraction_version):
        # map from context component to a function that writes text specific to that component type
        if extraction_version == 1.1:
            return {}
        return {
            "entities": basic_entity_author if extraction_version == 1.2 else all_entities_author,
            "pronouns": pronouns_author,
            "events": list_triples_author,  # predicates_author,
            "summary": lambda x: x,
        }

    def write_context_text(self, full_context):
        """
        Turn a list of narrative elements into a string describing the context.

        :param full_context: a list, each item (a dict) corresponding to all the narrative elements in that passage
        :rtype: str
        """

        # count up top components
        top_context_components = self.trim_context_components(full_context)

        context_text = ""
        for k, component in top_context_components.items():
            f = self.author_functions.get(k, DEFAULT_COMPONENT_FUNC)
            context_text += f(component) + " "
        return context_text

    def make_context_components(self, passage_text):
        """
        :param passage_text: the text from a single passage
        :return: a dict containing all narrative elements in the passage
        """

        doc = nlp(passage_text)

        context_components = {
            'v': self.extraction_version,
        }

        if self.extraction_version >= 1.2:
            context_components['pronouns'] = extract_pronouns(doc)
            context_components['entities'] = ner(passage_text)

        if self.extraction_version >= 1.3:
            context_components['events'] = extract_events(doc)

        return context_components

    def flatten_context(self, full_context):
        """
        Take a list of dicts, each representing the narrative elements in one passage, and return a single dict containing
        all narrative elements across all passages.
        """

        joined = {}
        if self.extraction_version >= 1.2:
            joined = {
                'pronouns': [],
                'entities': defaultdict(list),
            }
        if self.extraction_version >= 1.3:
            joined['events'] = []

        for passage_components in full_context:
            if passage_components.get('pronouns'):
                joined['pronouns'] += passage_components['pronouns']
            if passage_components.get('entities'):
                for k, v in passage_components['entities'].items():
                    joined['entities'][k] += v
            if passage_components.get('events'):
                joined['events'] += passage_components['events']

        return joined

    def trim_context_components(self, full_context, topk=8):
        """
        Takes a list of context components (dicts), each corresponding to all narrative elements in a passage.

        Then, counts the occurrences of each element across all passages. Returns the most common narrative elements across
        all passages, with their counts

        :param full_context: a list, each item (a dict) corresponding to all the narrative elements in that passage
        :returns: a dict of mapping narrative element type -> their counts (for counted elements) or the elements in order (for non-counted elements)
        """
        if not full_context or self.extraction_version <= 1.1:
            return {}

        flattened = self.flatten_context(full_context)

        counted = {
            'pronouns': Counter(flattened['pronouns']),
            'entities': {}
        }
        for ent_type, entities in flattened['entities'].items():
            counted['entities'][ent_type] = Counter(entities)

        top_context_components = {}
        top_context_components['pronouns'] = [p for p, count in counted['pronouns'].most_common(topk)]
        top_context_components['entities'] = {
            ent_type: entities.most_common(topk) for ent_type, entities in counted['entities'].items()
        }
        for ent_type, entities in top_context_components['entities'].items():
            top_context_components['entities'][ent_type] = [e for (e, count) in entities]

        if self.extraction_version >= 1.3:
            top_context_components['events'] = flattened['events']

        return top_context_components


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
    tokenizer = model = None
    try:
        tokenizer = AutoTokenizer.from_pretrained("./dslim/bert-base-NER", force_download=REDOWNLOAD_BERT)
        model = AutoModelForTokenClassification.from_pretrained("./dslim/bert-base-NER", force_download=REDOWNLOAD_BERT)
    except Exception as e:
        print(f"Could not load {'tokenizer' if not tokenizer else 'model'}! Try setting REDOWNLOAD_BERT=True in src/narrative_reader.py")
        os._exit(1)
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


def extract_pronouns(doc):
    pronouns = []
    for token in doc:
        if token.pos_ == 'PRON':
            pronouns.append(token.text.lower())

    return dedupe_in_order(pronouns, dont_add=PRONOUN_STOP_LIST)


def extract_events(doc):
    triples = [svo for svo in textacy.extract.subject_verb_object_triples(doc)]
    return triples


#### --- Begin Author Functions --- ####
## Author functions take a list of context components and write text describing them, interpretable by a language model
## or human
def all_entities_author(entities):
    written_components = []

    def simplify_entity_type(ent_type):
        # Some entity types can be combined
        new_ent = ent_type.replace('GPE', 'LOC')
        return new_ent

    for ent_type in set(entities.keys()) | set(ENTS_TO_ALWAYS_INCLUDE):
        ent_type = simplify_entity_type(ent_type)
        entity_text, exists = write_named_context_component(entities.get(ent_type, {}), ent_type)
        written_components.append(entity_text)

    text = " ".join(written_components)
    return text


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


def predicates_author(triples):
    """
    Convert a textacy.extract.triples.SVOTriple to a predicate style string description.
    """
    text = ''
    #  bomb(Donald Trump, panama)
    for subject, verb, object in triples:
        text += f'{t2s(verb)}({t2s(subject, False)}, {t2s(object, False)}) '
    return text


def list_triples_author(event_triples):
    """
    Convert a textacy.extract.triples.SVOTriple to a list of events.
    """
    while len(event_triples) > MAX_EVENTS_LENGTH:
        # over = len(event_triples) - MAX_EVENTS_LENGTH
        event_triples = event_triples[::2]  # Cut back by half

    text = 'Preceding Events:\n'
    if event_triples:
        for subject, verb, object in event_triples:
            text += f'* {t2s(subject, False)} {t2s(verb, False)} {t2s(object, False)}\n'
    else:
        text += 'None'
    return text

#### --- End Author Functions --- ####


def t2s(tokens, lemma=True):
    # convert a list of spacy tokens into text
    return " ".join([x.lemma_.lower() if lemma else x.text.lower() for x in tokens])

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
        print(f'WARNING: Entity type not found: {ent_type}')
        plural_type_desc = 'other'
    plural_type_desc = plural_type_desc.title()
    formatted_entities = comma_sep(typed_entities) if entities_exist else 'None'
    return f"Mentioned {plural_type_desc}: {formatted_entities}.", entities_exist


if __name__ == '__main__':
    passage = [
        """:: her research
Lara was able to find out that the woman she saw had been killed on that same day, the day before the storm. Hurricane Sandy had apparently knocked out power for days, which had made it even harder to find out more about the victim.
She also found out that the police (including Dr. Bradford) had closed the case, since the mysterious victim turned out to be a local celebrity.
This lead her to believe that the murderer(s) were still in London, and she would need to be extra careful in the future. 
[[She returns her attention to the docks.|the docks]]""",
        """:: her research
        Lara was able to find out that the woman she saw had been killed on that same day, the day before the storm. Hurricane Sandy had apparently knocked out power for days, which had made it even harder to find out more about the victim.
        She also found out that the police (including Dr. Bradford) had closed the case, since the mysterious victim turned out to be a local celebrity.
        This lead her to believe that the murderer(s) were still in London, and she would need to be extra careful in the future. 
        [[She returns her attention to the docks.|the docks]]""",
        """:: her research
        Lara was able to find out that the woman she saw had been killed on that same day, the day before the storm. Hurricane Sandy had apparently knocked out power for days, which had made it even harder to find out more about the victim.
        She also found out that the police (including Dr. Bradford) had closed the case, since the mysterious victim turned out to be a local celebrity.
        This lead her to believe that the murderer(s) were still in London, and she would need to be extra careful in the future. 
        [[She returns her attention to the docks.|the docks]]""",
        """:: her research
        Anna sits in her bed and knits. Someone knocks on the window to say hi. They lock eyes. You observe all of this."""
                ][-1]

    reader = BasicVersionedReader(1.3)

    passage = unsplit_lines(split_lines(passage)[1:])
    cleaned_passage_text = passage_to_text(passage)
    print("passage", cleaned_passage_text)
    context_components = reader.make_context_components(cleaned_passage_text)
    print("context components", context_components)
    print(reader.write_context_text([context_components]))
