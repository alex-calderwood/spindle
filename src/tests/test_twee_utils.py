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
        [":: Start [-]", True],
        [":: Start [4]", True],
        [":: Started to lick [4]", False],
    ])
    def test_is_start_and_get_title_integration(self, passage, actual):
        self.assertEqual(
            is_start(passage),
            actual
        )


class TestIsSpecialPassage(unittest.TestCase):
    @parameterized.expand([
        ["::lick", False],
        ["::StoryTitle", True],
        ["::StoryTitle", True],
        [":: StoryTitle", True],
        [":: StoryTitle [-]", True],
        [":: storytitle [4]", True],
        [":: Started to lick [4]", False],
        [":: StorySubtitle", True],
        [":: Storymenu", True],
    ])
    def test_is_special(self, passage, actual):
        self.assertEqual(
            is_special_passage(passage),
            actual
        )


# class TestTweeToGenAndBack(unittest.TestCase):
#     @parameterized.expand([
#         ":: lick",
#         ":: lick\nyour shoes",
#     ])
#     def test_is_special(self, twee):
#         gen_prompt, gen_completion = twee_to_gen_format_3(twee)
#         twee2 = gen_to_twee_format_3(gen_prompt, gen_completion)
#         self.assertEqual(
#             twee,
#             twee2
#         )



class TestTweeToGen(unittest.TestCase):
    @parameterized.expand([
        [":: lick", '<|begin|>:: lick<|start|>', ' <|end|>'], # Remember there is a space at the end
        [":: lick\nThe dog", '<|begin|>:: lick<|start|>', ' The dog<|end|>'],
        [":: lick\nThe dog\nsaid hi\nhi", '<|begin|>:: lick<|start|>', ' The dog<newline>said hi<newline>hi<|end|>'],
    ])
    def test_twee_to_gen(self, twee, prompt, completion):
        gen_prompt, gen_completion = twee_to_gen_format_3(twee)
        self.assertEqual(
            gen_prompt,
            prompt
        )
        self.assertEqual(
            gen_completion,
            completion
        )

    @parameterized.expand([
        [":: lick", 'The characters are Bob and Bill.', '<|begin|>The characters are Bob and Bill.<|title|>:: lick<|start|>', ' <|end|>'],  # Remember there is a space at the end
    ])
    def test_twee_to_gen_w_context(self, twee, context, prompt, completion):
        gen_prompt, gen_completion = twee_to_gen_format_3(twee, context=context)
        self.assertEqual(
            gen_prompt,
            prompt
        )
        self.assertEqual(
            gen_completion,
            completion
        )

class TestGenToTwee(unittest.TestCase):
    @parameterized.expand([
        ['<|begin|>:: lick<|start|>', '<|end|>', ":: lick"],  # Not sure this is all correct
        ['<|begin|>:: lick<|start|>', 'The dog<|end|>', ":: lick\nThe dog"],
        ['<|begin|>:: lick<|start|>', 'The dog<newline>said hi<newline>hi<|end|>', ":: lick\nThe dog\nsaid hi\nhi"],
    ])
    def test_is_special(self, gen_prompt, gen_completion, twee):
        twee2 = gen_to_twee_format_3(gen_prompt, gen_completion)
        self.assertEqual(
            twee2,
            twee
        )

class TestTitleToText(unittest.TestCase):
    @parameterized.expand([
        ["::lick", "lick"],
        ["::start", "start"],
        ["::Start", "Start"],
        [":: Start", "Start"],
        [":: Start [-]", "Start"],
        [":: Start [4]", "Start"],
        [":: more than one word [4]", "more than one word"],
        [":: more than one word ", "more than one word"],
        [":: another", "another"]
    ])
    def test_title_to_text(self, passage, actual):
        self.assertEqual(
            title_to_text(passage),
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
        [":: a stylesheet [stylesheet]", True]
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
        ["No links here", "No links here"],
        ["Walk towards the [[forest|forest_link]]", "Walk towards the forest"],
        ["Walk towards the [[forest]]", "Walk towards the forest"],
        ["Take a [[left|left_link]].", "Take a left."],
        ["Take a [[left|left_link]] and [[go|go_right]]", "Take a left and go"],
        ["Take a [[left]] and [[go]]", "Take a left and go"],
        ["Take a [[left|mixed]] and [[go]]", "Take a left and go"],
        ["Take a left <<choice \"thing\">>and [[go]]", "Take a left and go"],
        ["Take a left <<choice \"thing\">> and go", "Take a left and go"],  # duplicate spaces
        ["\n\ntesting  ", "\ntesting "],  # duplicate spaces
    ])
    def test_get_links(self, passage, link):
        self.assertEqual(
            passage_to_text(passage),
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


