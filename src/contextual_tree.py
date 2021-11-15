from collections import defaultdict
from anytree import Node, RenderTree, NodeMixin
from anytree.exporter import DotExporter
from twee_utils import *


class ContextualTweeTree(NodeMixin):
    # AnyTree Docs: https://anytree.readthedocs.io/en/2.8.0/
    def __init__(self, passage, context=[], title=None, parent=None):
        self.lines = split_lines(passage)
        self.passage = passage
        self.passage_text = passage_to_text(passage)
        self.title = title if title else get_title(self.lines)
        # the context is all relevant story details along the path from the root to the current node
        self.context = context
        self.name = title_to_text(self.title)  # + " context: " + str(context)
        self.parent = parent
        self._links = None

    def __str__(self):
        return f'<ContextualTweeTree {self.name}>'

    def render(self):
        print(RenderTree(self).by_attr('name'))

    def render_root(self):
        node = self
        parent = node.parent
        while parent is not None:
            temp = parent
            parent = node.parent
            node = temp
        print(node.render())

    def get_links(self):
        return self._links if self._links else get_links(self.passage)

    def extract_narrative_elements(self):
        """
        Run the NLP pipeline to extract from the current passage, all interesting story items.
        """
        return {'name': self.name}

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
        ContextualTweeTree._traverse_and_create_context(root, [], passage_dict)
        return root

    @staticmethod
    def _traverse_and_create_context(node, context, passage_dict):
        """
        Helper method for tree creation.
        Add children to a twee tree by recursively iterating over the links in each twee passage,
        keeping track of the context you've seen before.
        :param node: the current root node to expand
        :param context: the context (including the parent)
        :param passage_dict: a mapping from link (title text) to passage
        """
        for link in node.get_links():
            childs_context = context + [node.extract_narrative_elements()]
            passage = passage_dict.get(link)
            if passage:
                # create the child and add it to the parent
                child_node = ContextualTweeTree(passage, title=make_title(link), context=childs_context, parent=node)
                ContextualTweeTree._traverse_and_create_context(child_node, childs_context, passage_dict)
            else:
                print(f"passage {link} does not exist")


if __name__ == '__main__':
    game = './generated_games/the_garden_2.tw'
    print(f'game {game}')
    with open(game) as f:
        twee_str = f.read()
        print(f'tree for {game}:')
        tree = ContextualTweeTree.create(twee=twee_str)
        # dot = DotExporter(tree, nodenamefunc=lambda n: f'{n.name} context {n.context}')
        dot = DotExporter(tree, nodenamefunc=lambda n: f'{n.name}')
        dot.to_picture("./tree.png")
        tree.render()