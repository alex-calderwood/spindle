from collections import defaultdict
from anytree import Node, RenderTree, NodeMixin
from anytree.exporter import DotExporter
from twee_utils import *
from analysis import make_context_components, write_context_text


class ContextualTweeTree(NodeMixin):
    # TODO need to turn it into a tree
    # AnyTree Docs: https://anytree.readthedocs.io/en/2.8.0/
    def __init__(self, passage, title=None, parent=None, raw_passage=None, compute_context=True):
        """
        A contextualized node in a Twine tree, ie, a single passage.
        :param compute_context: whether or not to add context to the contextual nodes (can be slow)
        """
        self.lines = split_lines(passage)
        self.passage = passage
        self.passage_text = passage_to_text('\n'.join(self.lines[1:])) if not raw_passage else passage_to_text('\n'.join(raw_passage.split('\n')[1:]))
        self.title = title if title else get_title(self.lines)
        self.parent = parent
        self._links = None
        self.narrative_elements = self._extract_narrative_elements()
        # the context is all relevant story details along the path from the root to the current node
        self.full_context = (parent.full_context + [parent.narrative_elements]) if (parent and compute_context) else []
        self.context_text = write_context_text(self.full_context)
        self.name = self.title  #+ ': ' + str(self.context_text)  # + " context: " + str(self.context)

    def __str__(self):
        return f'<ContextualTweeTree {self.name}>'

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
        return make_context_components(self.passage_text)

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
        root = ContextualTweeTree(start)
        ContextualTweeTree._traverse_and_create_context(root, passage_dict, defaultdict(bool))
        return root, passage_dict

    @staticmethod
    def _traverse_and_create_context(node, passage_dict, visited):
        """
        Helper method for tree creation.
        Add children to a twee tree by recursively iterating over the links in each twee passage,
        keeping track of the context you've seen before.
        :param node: the current root node to expand
        :param context: the context (including the parent)
        :param passage_dict: a mapping from link (title text) to passage
        """
        for link in node.get_links():
            if visited[link]:
                continue
            passage = passage_dict.get(link)
            if passage:
                # create the child and add it to the parent
                child_node = ContextualTweeTree(passage, title=make_title(link), parent=node)
                visited[link] = True
                ContextualTweeTree._traverse_and_create_context(child_node, passage_dict, visited)
            else:
                print(f"passage {link} does not exist")


if __name__ == '__main__':
    # TODO need to check whether name [1] should link to name or not
    game = './generated_games/the_garden_3.tw'
    print(f'game {game}')
    with open(game) as f:
        twee_str = f.read()
        print(f'tree for {game}:')
        tree, _ = ContextualTweeTree.create(twee=twee_str)
        # dot = DotExporter(tree, nodenamefunc=lambda n: f'{n.name} context {n.context}')
        dot = DotExporter(tree, nodenamefunc=lambda n: f'{n.name}')
        dot.to_picture("./tree.png")
        tree.render()