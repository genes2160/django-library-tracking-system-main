import unittest
import random


class CoreSkillsTests(unittest.TestCase):
    def test_random_list_and_filters(self):
        random.seed(123)
        rand_list = [random.randint(1, 20) for _ in range(10)]
        self.assertEqual(len(rand_list), 10)
        self.assertTrue(all(1 <= n <= 20 for n in rand_list))

        below_10_lc = [n for n in rand_list if n < 10]
        below_10_filter = list(filter(lambda x: x < 10, rand_list))
        self.assertEqual(below_10_lc, below_10_filter)