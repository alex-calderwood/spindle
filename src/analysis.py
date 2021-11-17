from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline
import os
from collections import defaultdict
import threading, time, sys, itertools


def load_ner():
    def _animate(text, finished='Loaded model.'):
        # ['|', '/', '-', '\\']
        spaces = ' ' * len(text)
        text_all = [text[:i + 1] for i in range(len(text))]
        for c in itertools.cycle(text_all):  # ['.   ', '..  ', '... ', '....']
            if done:
                break
            # sys.stdout.write(f'\r{text}' + c)
            sys.stdout.write(f'-{c}                                                 \r')
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write(f'\r{finished}                \r')
    text = 'Loading English... Reticulating Splines... etc...'
    done = False
    t = threading.Thread(target=_animate, args=(text,))
    t.start()
    os.environ["TOKENIZERS_PARALLELISM"] = "true"
    tokenizer = AutoTokenizer.from_pretrained("dslim/bert-base-NER")
    model = AutoModelForTokenClassification.from_pretrained("dslim/bert-base-NER")
    ner_pipline = pipeline("ner", model=model, tokenizer=tokenizer)
    done = True
    t.join()
    return ner_pipline


ner_pipeline = load_ner()


def ner(text):
    """
    Extract Named Entities from a text, return a dictionary.
    """
    ner_results = ner_pipeline(text)
    is_same_ent = lambda x, y: x.split('-')[-1] == y.split('-')[-1]
    entities = []
    for i, entity in enumerate(ner_results):
        prev_entity = ner_results[i - 1] if i > 0 else {}
        if (entity['index'] == prev_entity.get('index', -2) + 1) \
                and is_same_ent(entity['entity'], prev_entity.get('entity', 'nope')):
            # print(entity, prev_entity)
            prev_entity['word'] = prev_entity.get('word', '') + ' ' + entity['word']
        else:
            entities.append(entity)
    processed_entities = defaultdict(list)
    for e in entities:
        e_type = e['entity']
        text = e['word']
        processed_entities[e_type].append(text)

    return dict(processed_entities)


def _make_context_components(passage_text):
    return {
        'v': 1.0,  # Context version (I expect to go through a few iterations)
        'entities': ner(passage_text),
    }


def comma_sep(list_of):
    if not list_of:
        return ''
    elif len(list_of) == 1:
        return list_of[0]
    else:
        return ', '.join(list_of[:-1]) + ', and ' + list_of[-1]


def entity_context_compoenent(entities):
    return character_context_component(entities)
    # TODO others


def character_context_component(enttites):
    characters = [v.endswith('PER') for v in enttites.values()]
    return f"Previously mentioned characters: {comma_sep(characters)}."


def loc_context_component(enttites):
    locations = [v.endswith('LOC') for v in enttites.values()]
    return f"Locations mentioned: {comma_sep(locations)}."


def make_context(passage_text):
    components = _make_context_components(passage_text)

    # map from context component to a function that writes text based on the component
    context_component_function = {
        "entities": entity_context_compoenent,
        "summary": lambda x: x,
    }

    context_text = ""
    for k, component in components.items():
        f = context_component_function.get(k, lambda x: str(x))
        context_text += f(component) + "\n"
    return context_text
