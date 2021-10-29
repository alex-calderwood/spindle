from parameterized import parameterized, parameterized_class # https://github.com/wolever/parameterized
import unittest
from twee_utils import *


class TestValidTwee(unittest.TestCase):

    def setUp(self):
        pass

    @parameterized.expand([
        ["::lick\nsends jolts up your [[spine]].", (True, True)],  # Valid
        [":lick\nsends jolts up your [[spine]].", (False, True)],  # Only one :
        ["::lick\nsends jolts up your [[spine].", (True, False)],   # Only one ]
    ])
    def test_is_valid_passage(self, passage, is_valid):
        self.assertEqual(
            tuple(valid_passage_indicators(passage).values()),
            is_valid
        )

    def is_valid_twee(self, twee, is_valid):
        self.assertEqual(
            tuple(valid_passage_indicators(twee).values()),
            is_valid
        )


class TestTweeParsing(unittest.TestCase):

    @parameterized.expand([
        ["::lick\nsends <<macro>> jolts up your [[spine]].", ['macro']],
        ["::lick\nsends <<macro1>> jolts <<macro2>> <<set macro3 = something>>up your [[spine]].", ['macro1', 'macro2', 'set macro3 = something']]
    ])
    def test_get_macros(self, passage, macros):
        self.assertEqual(
            get_macros(passage),
            macros
        )

    @parameterized.expand([
        ["::lick\nsends <<macro>> jolts up your [[spine]].", True],
        ["::lick\nsends <<macro1>> jolts <<macro2>> <<set macro3 = something>>up your [[spine]].", True],
        ["::lick\nsends jolts up your [[spine]].", False],
    ])
    def test_get_macros_bool(self, passage, macros):
        self.assertEqual(
            bool(get_macros(passage)),
            macros
        )

    @parameterized.expand([
        ["::lick\nsends <<macro>> jolts up your [[spine]].", "::lick\nsends jolts up your [[spine]]."],
        # ["::lick\nsends <<macro1>> jolts <<macro2>> <<set macro3 = something>>up your [[spine]].", ['macro1', 'macro2', 'set macro3 = something']]
    ])
    def test_replace_macros(self, passage, twee):
        self.assertEqual(
            replace_macros(passage),
            twee
        )

    @parameterized.expand([
        ["::title\n[>img[killer]]\nThings Happen", "::title\n\nThings Happen"],
        ["::title\n[>img[killer]]\nThings Happen[[Other|link]]", "::title\n\nThings Happen[[Other|link]]"],
    ])
    def test_clean_images(self, passage, twee):
        self.assertEqual(
            clean_images(passage),
            twee
        )

    @parameterized.expand([
        ["::untitled passage", True],
        ["::untitled passage ", True],
        [" ", True],
        ["", True],
        [":: a thing", False],
    ])
    def test_is_empty_passage(self, passage, empty):
        self.assertEqual(
            is_empty_passage(passage),
            empty
        )

    @parameterized.expand([
        ["Things Happen[[Other|link]]", ['link']],
        ["Things Happen[]", []],
        ["Things Happen", []],
        ["Things Happen [[with link]] [[another|link]]", ['with link', 'link']],
        ["Things Happen [[first link]] [[second link]] [[another|first link]]", ['first link', 'second link']],
    ])
    def test_get_links(self, passage, link):
        self.assertEqual(
            get_links(passage),
            link
        )
