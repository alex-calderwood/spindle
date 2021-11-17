examples = [
        """Josephine softens. "Yeah, okay. I probably got a little too worked up there."
A bell chimes in the house. 
"Oh, wow. Is it that late? We should be headed to bed if you wanna be up early enough to dig your car out."
"Yeah, I should probably turn in."
"The night's still young. Why don't we stay up a little longer?"
Donald Trump shows up. You realize you've been in simulated White House this whole time.
""",
    "Alex softens. Josephine picks up an apple.",
    "She walks in beauty, like the night. It snows that night. The rain, the rain. You are free.",
    "You decided to meet him on a pub called Le Bon Temps Roule.",
    "The Golden Gate Bridge was painted green by Joe Biden."
    ]

def test_neuralcoref():
    """

    """
    import spacy
    import neuralcoref

    nlp = spacy.load('en')
    neuralcoref.add_to_pipe(nlp)

    doc = nlp('My sister has a dog. She loves him. Angela lives in Boston. She is quite happy in that city.')
    print(f"doc {doc}")
    print(f"coref clusters {doc._.coref_clusters}")
    for ent in doc.ents:
        print(ent._.coref_cluster)


def test_spacy_ner():
    """
    PERSON:      People, including fictional.
    NORP:        Nationalities or religious or political groups.
    FAC:         Buildings, airports, highways, bridges, etc.
    ORG:         Companies, agencies, institutions, etc.
    GPE:         Countries, cities, states.
    LOC:         Non-GPE locations, mountain ranges, bodies of water.
    PRODUCT:     Objects, vehicles, foods, etc. (Not services.)
    EVENT:       Named hurricanes, battles, wars, sports events, etc.
    WORK_OF_ART: Titles of books, songs, etc.
    LAW:         Named documents made into laws.
    LANGUAGE:    Any named language.
    DATE:        Absolute or relative dates or periods.
    TIME:        Times smaller than a day.
    PERCENT:     Percentage, including ”%“.
    MONEY:       Monetary values, including unit.
    QUANTITY:    Measurements, as of weight or distance.
    ORDINAL:     “first”, “second”, etc.
    CARDINAL:    Numerals that do not fall under another type.
    """
    import spacy
    nlp = spacy.load('en_core_web_lg')

    text = examples[-1]
    doc = nlp(text)
    print(doc.text)
    # for token in doc:
    #     print(token.text, token.pos_, token.dep_, token.ent_type_)
    # print('entities')
    # for entity in doc.ents:
    #     start, end = entity.start, entity.end
    #     for token in doc[start:end]:
    #         print(token.text, token.ent_type_)

    # for token in doc:
    #     print(token.text, token.pos_, token.dep_, token.ent_type_)
    print('pos_')
    pronouns = []
    for token in doc:
        print(token, token.pos_)

# test_spacy_ner()


def test_bert_huggingface_ner():
    from transformers import AutoTokenizer, AutoModelForTokenClassification
    from transformers import pipeline

    tokenizer = AutoTokenizer.from_pretrained("dslim/bert-base-NER")
    model = AutoModelForTokenClassification.from_pretrained("dslim/bert-base-NER")
    nlp = pipeline("ner", model=model, tokenizer=tokenizer)

    tokens = nlp.tokenizer.tokenize(examples[-1])
    print(type(tokens), type(tokens[0]))
    print(tokens)

    example = examples[-2]
    print(example)
    ner_results = nlp(example)
    print(ner_results)

    same_ent_type = lambda x, y: x.split('-')[-1] == y.split('-')[-1]
    entities = []
    prev_beg = {}
    for i, entity in enumerate(ner_results):
        prev_entity = ner_results[i - 1] if i > 0 else {}
        print(entity['word'], entity['entity'])
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

    print([e for e in entities]


test_bert_huggingface_ner()

# from stanza.server import CoreNLPClient
# stanza.download('en')
# # nlp = stanza.Pipeline('en')
# #
# # doc =
# #
# # for sentence in doc.sentences:
# #     print(sentence.ents)
# #     print(sentence.dependencies)
#
#
# text = \
#     """It's been a while since you've been here, but you quickly find your way. Even after all these years, the path is still a little too familiar to be completely trustworthy. The door creaks open, and you slowly creep inside. You have a slight feeling of deja-vu, as if you've been here before."""
#
# # with CoreNLPClient(annotators=["tokenize","ssplit","pos","lemma","depparse","natlog","openie"], be_quiet=False) as client:
# with CoreNLPClient(annotators=["openie"], be_quiet=False) as client:
#     ann = client.annotate(text)
#     # print(ann)
#     for sentence in ann.sentence:
#         for triple in sentence.openieTriple:
#             print(triple)