from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline
import os
from collections import defaultdict
import threading, time, sys, itertools


def _animate(text, finished='Loaded model.'):
    # ['|', '/', '-', '\\']
    spaces = ' ' * len(text)
    text_all = [text[:i+1] for i in range(len(text))]
    for c in itertools.cycle(text_all): #['.   ', '..  ', '... ', '....']
        if done:
            break
        # sys.stdout.write(f'\r{text}' + c)
        sys.stdout.write(f'-{c}                                    \r')
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write(f'\r{finished}                \r')


text = 'Loading English...'
done = False
t = threading.Thread(target=_animate, args=(text,))
t.start()
os.environ["TOKENIZERS_PARALLELISM"] = "true"
tokenizer = AutoTokenizer.from_pretrained("dslim/bert-base-NER")
model = AutoModelForTokenClassification.from_pretrained("dslim/bert-base-NER")
ner_pipline = pipeline("ner", model=model, tokenizer=tokenizer)
done = True
t.join()


def ner(text):
    ner_results = ner_pipline(text)

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
