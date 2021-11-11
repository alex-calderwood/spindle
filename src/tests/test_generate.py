from parameterized import parameterized, parameterized_class  # https://github.com/wolever/parameterized
import unittest
from ..spindle import *


class TestValidTwee(unittest.TestCase):

    def setUp(self):
        pass

    @parameterized.expand([
        ["::lick\nsends jolts up your [[spine]].", (True, True)],
    ])
    def todo(self, passage, is_valid):
        self.assertEqual(
            True,
            True
        )

