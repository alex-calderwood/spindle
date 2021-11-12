from parameterized import parameterized, parameterized_class # https://github.com/wolever/parameterized
import unittest
from ..twee_utils import *


class TestValidTwee(unittest.TestCase):

    def setUp(self):
        pass

    @parameterized.expand([
        ["::lick\nsends jolts up your [[spine]].", (True, True)],  # Valid
        [":lick\nsends jolts up your [[spine]].", (False, True)],  # Only one :
        ["::lick\nsends jolts up your [[spine].", (True, False)],   # Only one ]
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


class TestIsStartIntegration(unittest.TestCase):

    @parameterized.expand([
        ["::lick", False],
        ["::start", True],
        ["::Start", True],
        [":: Start", True],
        [":: Start [-]", False],  # I think these two should be false
        [":: Start [4]", False],
    ])
    def test_is_start_and_get_title_integration(self, passage, actual):
        self.assertEqual(
            is_start(passage),
            actual
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

    @parameterized.expand([
        ["Things Happen[[Other|Link]]", "Things Happen[[Other|link]]"],
        ["Things Happen[[lower|lower]]", "Things Happen[[lower|lower]]"],
        ["[[UPPER]]", "[[upper]]"],
        ["[[Mix|cAse]] a [[mix|case]] [[CASE]]", "[[Mix|case]] a [[mix|case]] [[case]]"],
        ["[[bad|Format", "[[bad|Format"],
        ["[[]]", "[[]]"],
    ])
    def test_lower_case_links(self, passage, lowered_link_passage):
        self.assertEqual(
            lower_case_links(passage),
            lowered_link_passage
        )

    @parameterized.expand([
        ["good_link", None],
        ["bad|link", "badlink"],
        ["previous()", "previous"],
        ["spi[ne", "spine"],
        ["<spine,>", "spine"],
        ["<weird html stuff>", "weird html stuff"],
    ])
    def test_validate_link_text(self, link_text, validated):
        self.assertEqual(
            validate_link_text(link_text),
            validated
        )


