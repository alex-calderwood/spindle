from collections import defaultdict
from anytree import Node, RenderTree, NodeMixin
from twee_utils import *


class ContextualTweeTree(NodeMixin):
    # AnyTree Docs: https://anytree.readthedocs.io/en/2.8.0/
    def __init__(self, passage, context=[], title=None, parent=None):
        self.passage = passage
        self.lines = split_lines(passage)
        self.name = self.title = title if title else get_title(self.lines)
        self.parent = parent
        self._links = None
        self.context = context

    def get_links(self):
        return self._links if self._links else get_links(self.passage)

    def extract_events(self):
        return self.name

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
            passages = split_passages(twee)

        start = get_start(passages)
        if not start:
            raise RuntimeError("No Start node found found found")

        # Make a dictionary mapping title_text: full_passage
        passage_dict = make_passage_dict(passages)
        print(passage_dict)
        exit(1)

        # Create a contextual tree
        root = ContextualTweeTree(start)
        _traverse_and_create_context(root, [], passage_dict)

        return root


def _traverse_and_create_context(node, context, passage_dict):
    """
    Create a tree by recursively iterating over the links of the tree, keeping track of the context you've seen before.
    In retrospect I should have hand-coded this. I thought bringing in an external tree library would save time. It didn't,
    but now we have some useful functions from anytree so I'm leaving the dependency.
    """
    for link in node.get_links():
        childs_context = context + [node.extract_events()]
        # create the child and add it to the parent
        child = ContextualTweeTree(passage_dict[link], title=link, context=childs_context, parent=node)
        _traverse_and_create_context(child)


if __name__ == '__main__':
    with open('./generated_games/my_story.tw') as f:
        twee_str = f.read()
        ContextualTweeTree.create(twee=twee_str)
