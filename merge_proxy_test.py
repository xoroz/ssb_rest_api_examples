__author__ = 'gyp'

import unittest
from merge_proxy import *


class KWayMergeTests(unittest.TestCase):
    def test_next_throws_exception_if_fetch_functions_is_not_iterable(self):
        with self.assertRaises(TypeError):
            merger = KWayMerger(1)
            merger.next()

    def test_next_throws_exception_if_fetch_functions_are_not_callable(self):
        with self.assertRaises(TypeError):
            merger = KWayMerger((1, 2))
            merger.next()

    def test_next_returns_the_single_value_from_a_single_call(self):
        MAGIC = 123456
        simplefetcher = lambda: MAGIC
        merger = KWayMerger((simplefetcher,))
        self.assertEqual(merger.next(), MAGIC)

    def test_first_next_returns_the_first_from_10(self):
        fetchers = []
        for i in range(10):
            fetchers.append(MockFetcher([i]).next)
        merger = KWayMerger(tuple(fetchers))
        self.assertEqual(merger.next(), 0)

    def test_two_elements_are_sorted_well(self):
        merger = KWayMerger((MockFetcher([2]).next, MockFetcher([1]).next))

        self.assertEqual(merger.next(), 1)
        self.assertEqual(merger.next(), 2)

    def test_one_ordered_list_is_returned_as_is(self):
        merger = KWayMerger((MockFetcher(list(range(10))).next,))

        for i in range(10):
            self.assertEqual(merger.next(), i)

    def test_multiple_identical_lists_are_merged_propery(self):
        LIST_LENGTH = 5
        NUMBER_OF_LISTS = 10

        fetchers = []
        for i in range(NUMBER_OF_LISTS):
            fetchers.append(MockFetcher(list(range(LIST_LENGTH))).next)

        merger = KWayMerger(tuple(fetchers))

        for i in range(LIST_LENGTH):
            for j in range(NUMBER_OF_LISTS):
                self.assertEqual(merger.next(), i)

    def test_zipper_merge_works(self):
        LIST_LENGTH = 50
        NUMBER_OF_LISTS = 200

        fetchers = []
        for i in range(NUMBER_OF_LISTS):
            start = i
            step = NUMBER_OF_LISTS
            end = start + NUMBER_OF_LISTS * LIST_LENGTH
            fetchers.append(MockFetcher(list(range(start, end, step))).next)

        merger = KWayMerger(tuple(fetchers))

        for i in range(LIST_LENGTH * NUMBER_OF_LISTS):
            self.assertEqual(merger.next(), i)


class MockFetcher:
    def __init__(self, list_to_return):
        self._list_to_return = list_to_return

    def next(self):
        if len(self._list_to_return) > 0:
            return self._list_to_return.pop(0)
        else:
            return None

    #TODO_fetches_are_not_called_multiple_times

if __name__ == '__main__':
    unittest.main()
