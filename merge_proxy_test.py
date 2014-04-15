__author__ = 'gyp'

import unittest
import urllib.parse, json
from merge_proxy import *

class SSBAPITests(unittest.TestCase):
    USERNAME = "foo"
    PASSWORD = "bar"
    LOGSPACE_NAME = "apple"

    def test_login_calls_one_request(self):
        requests = self._do_a_login_and_get_requests()
        self.assertEqual(len(requests), 1)

    def _do_a_login_and_get_requests(self):
        (connection, api) = self._get_connection_api_pair()
        api.login(self.USERNAME, self.PASSWORD)
        return connection.get_requests()

    def _get_connection_api_pair(self):
        connection = MockHTTPConnection()
        api = SSBAPI(connection)
        return connection, api

    def test_login_calls_a_post_to_the_login_point_in_the_api(self):
        (method, url, body, headers) = self._do_a_login_and_get_first_request()
        self.assertEqual("POST", method)
        self.assertEqual("/api/1/login", url)

    def _do_a_login_and_get_first_request(self):
        requests = self._do_a_login_and_get_requests()
        return requests[0]

    def test_login_calls_a_post_with_the_user_and_pass(self):
        (method, url, body, headers) = self._do_a_login_and_get_first_request()
        expected_body =  urllib.parse.urlencode({'username': self.USERNAME, 'password': self.PASSWORD})
        self.assertEqual(expected_body, body)

    def test_list_logspaces_proxies_list_logspaces(self):
        self._test_object_call_proxies_api_call(
            object_func="list_logspaces",
            api_url="/api/1/search/logspace/list_logspaces",
            response_value=["logspace1", "foo", "bar", "logspace4"]
        )

    def _test_object_call_proxies_api_call(self, object_func, api_url, args=(), response_value=None):
        (connection, api) = self._get_connection_api_pair()
        if response_value is not None:
            # the first one is for the login which we don't want to care about here
            connection.set_responses([None, self._generate_successful_response(response_value)])
        api.login(self.USERNAME, self.PASSWORD)

        func_to_call = getattr(api, object_func)
        result = func_to_call(*args)

        requests = connection.get_requests()
        self.assertEqual(len(requests), 2)  # again, the first one was the login
        (method, url, body, headers) = requests[1]
        self.assertEqual("GET", method)
        self._assertURLEqual(api_url, url)
        if response_value is not None:
            self.assertEqual(response_value, result)

    def _assertURLEqual(self, expected, actual):
        expected_parsed = urllib.parse.urlparse(expected)
        actual_parsed = urllib.parse.urlparse(actual)

        # these fields need to match char-by-char
        for field in ('scheme', 'netloc', 'path'):
            self.assertEqual(getattr(expected_parsed, field), getattr(actual_parsed, field))

        # but the sequence is not important in the query
        expected_query = urllib.parse.parse_qs(expected_parsed.query)
        actual_query = urllib.parse.parse_qs(actual_parsed.query)
        self.assertDictEqual(expected_query, actual_query)



    def _generate_successful_response(self, object_to_return):
        return "{\"result\": %s}" % json.dumps(object_to_return)

    def test_logout_is_proxied_to_logout(self):
        self._test_object_call_proxies_api_call(
            object_func="logout",
            api_url="/api/1/logout",
        )

    def test_filter_proxies_filter(self):
        self._test_filter_type_command("filter", "filter",
                                       [{"logmsg1": "logvalue1"}, {"logmsg2": "logvalue2"}], True)

    def _test_filter_type_command(self, object_func, api_command_in_url, return_value, add_limit_offset):
        test_from = 123
        test_to = 456
        test_expression = "search_expression"
        test_offset = 222
        test_limit = 333

        expected_params = {'from': test_from, 'to': test_to, 'search_expression': test_expression}
        if add_limit_offset:
            expected_params["offset"] = test_offset
            expected_params["limit"] = test_limit

        expected_params = urllib.parse.urlencode(expected_params)

        self._test_object_call_proxies_api_call(
            object_func=object_func,
            args=(self.LOGSPACE_NAME, test_from, test_to, test_expression, test_offset, test_limit),
            api_url="/api/1/search/logspace/%s/%s?%s" % (api_command_in_url, self.LOGSPACE_NAME, expected_params),
            response_value=return_value
        )

    def test_number_of_messages_proxies_number_of_messages(self):
        self._test_filter_type_command("number_of_messages", "number_of_messages", 999, False)

    def test_auth_token_is_included_in_later_calls_after_login(self):
        (connection, api) = self._get_connection_api_pair()
        AUTH_TOKEN = "asdfasdfaqwerqwerqewr"

        connection.set_responses([
            self._generate_successful_response(AUTH_TOKEN),  # login
            self._generate_successful_response("fake_logspace"),  # list_logspaces
            self._generate_successful_response("[]"),  # filter
            self._generate_successful_response("[]"),  # number_of_messages
            None  # logout
        ])

        api.login(self.USERNAME, self.PASSWORD)
        api.list_logspaces()
        api.filter("fake_logspace", 123, 456)
        api.number_of_messages("fake_logspace", 123, 456)
        api.logout()

        requests = connection.get_requests()
        self.assertEqual(5, len(requests))  # just playing safe, we've tested this above
        for i in range(1, 5):
            (method, url, body, headers) = requests[i]
            self.assertTrue("Cookie" in headers)
            cookies = urllib.parse.unquote(headers['Cookie'])
            self.assertEqual("AUTHENTICATION_TOKEN=%s" % AUTH_TOKEN, headers['Cookie'])


class MockHTTPConnection:
    def __init__(self):
        self.requests = []
        self.responses = []

    # utility funcs for testing

    def set_responses(self, responses):
        self.responses = responses

    def get_requests(self):
        return self.requests

    # mock HTTPConnection interface

    def request(self, method, url, body=None, headers={}):
        self.requests.append((method, url, body, headers))

    def getresponse(self):
        if len(self.responses) > 0:
            response_data = self.responses.pop(0)

        if response_data is None:
            response_data = ""

        return MockHTTPResponse(200, response_data)


class MockHTTPResponse:
    def __init__(self, status, data):
        self.status = status
        self.data = str.encode(data)

    def read(self):
        return self.data

    def readall(self):
        return self.read()


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
        self.assertEqual(MAGIC, merger.next())

    def test_first_next_returns_the_first_from_10(self):
        fetchers = []
        for i in range(10):
            fetchers.append(MockFetcher([i]).next)
        merger = KWayMerger(tuple(fetchers))
        self.assertEqual(0, merger.next())

    def test_two_elements_are_sorted_well(self):
        merger = KWayMerger((MockFetcher([2]).next, MockFetcher([1]).next))

        self.assertEqual(1, merger.next())
        self.assertEqual(2, merger.next())

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
            self.assertEqual(i, merger.next())


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
