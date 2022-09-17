import unittest

import wordart

ROCK_EMOJI = "\U0001FAA8"

class TestWordart(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        wordart.load_wa_alphabet()

    def testRock(self):
        # This was failing on the rock emoji because of an old version of the
        # emoji library.

        self.assertTrue(
            not wordart.handle_wordart_request(
                ROCK_EMOJI + " rock", ""
            ).startswith("Sorry")
        )
