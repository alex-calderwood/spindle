from collections import defaultdict
from anytree import RenderTree, NodeMixin, PreOrderIter
from anytree.exporter import DotExporter
from twee_utils import *
from narrative_reader import BasicVersionedReader, predicates_author


class PassageTree(NodeMixin):
    # Static reader version
    reader = None
    def __init__(self, passage, title=None, parent=None, raw_passage=None, compute_context=True):
        """
        A contextualized node in a Twine tree, ie, a single passage.
        :param compute_context: whether or not to add context to the contextual nodes (can be slow)

        AnyTree Docs: https://anytree.readthedocs.io/en/2.8.0/
        """
        self.lines = split_lines(passage)
        self.passage = passage
        self.cleaned_passage_text = passage_to_text('\n'.join(self.lines[1:])) if not raw_passage else passage_to_text('\n'.join(raw_passage.split('\n')[1:]))
        self.title = title if title else get_title(self.lines)
        self.name = self.title
        self.parent = parent
        self._links = None
        self.narrative_elements = self._extract_narrative_elements()
        # the context is all relevant story details along the path from the root to the current node
        self.full_context = self.construct_context(parent) if (parent and compute_context) else []
        self.context_text = PassageTree.get_reader().write_context_text(self.full_context)

    def __str__(self):
        return f'<PassageTree {self.name} v{self.reader.extraction_version}>'

    def render(self):
        print(RenderTree(self).by_attr('name'))

    def render_root(self):
        print(self.get_root().render())

    def get_root(self):
        node = self
        parent = node.parent
        while parent is not None:
            temp = parent
            parent = node.parent
            node = temp
        return node

    def get_links(self):
        return self._links if self._links else get_links(self.passage)

    def _extract_narrative_elements(self):
        """
        Run the NLP pipeline to extract from the current passage, all interesting story items.
        """
        return PassageTree.get_reader().make_context_components(self.cleaned_passage_text)

    def convert_events_to_fake_token(self):
        """
        spacy doesn't support the pickling of individual tokens
        this was my attempt to work around that
        """
        for n in PreOrderIter(self):
            new_events = []
            for triple in n.narrative_elements['events']:
                fake_triple = []
                for component in triple:
                    fake_triple.append([BespokeToken(token) for token in component])
                new_events.append(fake_triple)

            n.narrative_elements['events'] = new_events

        for n in PreOrderIter(self):
            print(n.narrative_elements['events'])

    @staticmethod
    def get_reader(version=1.3):
        """
        Return the singleton reader class or initialize one to the provided version number 
        if the reader does not exist.
        """

        if PassageTree.reader is None:
            PassageTree.reader = BasicVersionedReader(version)

        return PassageTree.reader

    @staticmethod
    def construct_context(parent):
        """
        Returns a list of context components / narrative elements.
        Each are dictionaries of the form:
            {narrative element type: value ...}
        """
        if parent is None:
            return []

        return parent.full_context + [parent.narrative_elements]

    @staticmethod
    def create(twee=None, passages=None):
        """
        Create a contextual tree from some twee passages.

        You must specify one of:
            :param twee: the full document
            :param passages: the split passages
        """
        if bool(twee) == bool(passages):
            raise SyntaxError("should call with either twee or passages defined")
        if twee:
            passages = [p for p in split_passages(twee)]
        start = get_start(passages)
        if not start:
            raise RuntimeError("No Start node found")

        # Make a dictionary mapping title_text: full_passage
        passage_dict = make_passage_dict(passages)

        # Create a contextual tree
        root = PassageTree(start)
        PassageTree._traverse_and_create_context(root, passage_dict, defaultdict(bool))
        return root, passage_dict

    @staticmethod
    def _traverse_and_create_context(node, passage_dict, visited):
        """
        Helper method for tree creation.
        Add children to a twee tree by recursively iterating over the links in each twee passage,
        keeping track of the context you've seen before.
        :param node: the current root node to expand
        :param passage_dict: a mapping from link (title text) to passage
        :param visited: a dict mapping link -> a bool of whether its been visited. should have been a set of
        """
        for link in node.get_links():
            if visited[link]:
                continue
            passage = passage_dict.get(link)
            if passage:
                # create the child and add it to the parent
                child_node = PassageTree(passage, title=make_title(link), parent=node)
                visited[link] = True
                PassageTree._traverse_and_create_context(child_node, passage_dict, visited)
            else:
                print(f"passage {link} does not exist")


class BespokeToken:
    def __init__(self, token):
        self.text = token.text
        self.lemma_ = token.lemma_

    def __repr__(self):
        return f"~{self.text}"

    def __str__(self):
        return self.text


if __name__ == '__main__':
    # TODO need to check whether 'name [1]' should link to 'name' or not
    game = './generated_games/context_1.tw'
    print(f'game {game}')
    with open(game) as f:
        twee_str = f.read()
        print(f'tree for {game}:')
        PassageTree.reader = BasicVersionedReader(1.3)
        tree, _ = PassageTree.create(twee=twee_str)
        tree.convert_events_to_fake_token()
        for n in PreOrderIter(tree):
            print(n, predicates_author(n.narrative_elements['events']))

        dot = DotExporter(tree, nodenamefunc=lambda n: f'{n.name}')
        dot.to_picture("./tree.png")
        tree.render()