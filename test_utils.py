import unittest
import logging
from utils import str_to_bool, str_to_list

class TestUtils(unittest.TestCase):
    def test_str_to_bool(self):
        self.assertTrue(str_to_bool("True"))
        self.assertTrue(str_to_bool("true"))
        self.assertFalse(str_to_bool("False"))
        self.assertFalse(str_to_bool("false"))
        self.assertIsNone(str_to_bool("invalid"))

    def test_str_to_list(self):
        self.assertIsNone(str_to_list("None"))
        self.assertEqual(str_to_list("a, b"), ["a", "b"])
        self.assertEqual(str_to_list("a,b"), ["a", "b"])
        self.assertEqual(str_to_list("a"), ["a"])
        self.assertIsNone(str_to_list("a b")) # Inconsistent formatting

if __name__ == '__main__':
    unittest.main()
