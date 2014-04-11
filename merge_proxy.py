__author__ = 'gyp'

class MergeProxy:
    pass

class KWayMerger:
    def __init__(self, fetch_functions):
        self._fetch_functions = fetch_functions
        self._next_values = []
        for i in range(len(fetch_functions)):
            self._next_values.append(None)

    def next(self):
        self._fill_up_empty_next_value_slots()
        return self._return_and_drop_smallest_from_next_values()

    def _fill_up_empty_next_value_slots(self):
        fetcher_count = 0
        for fetch_func in self._fetch_functions:
            if self._next_values[fetcher_count] is None:
                self._next_values[fetcher_count] = fetch_func()
            fetcher_count += 1

    def _return_and_drop_smallest_from_next_values(self):
        (smallest_key, smallest) = self._find_smallest(self._next_values)
        self._next_values[smallest_key] = None
        return smallest

    @staticmethod
    def _find_smallest(list_to_search_in):
        smallest = None
        smallest_key = None
        for i in range(len(list_to_search_in)):
            current = list_to_search_in[i]
            if smallest is None or (current is not None and current < smallest):
                smallest = current
                smallest_key = i

        return smallest_key, smallest


if __name__ == '__main__':
    print("Hello World!")