__author__ = 'gyp'
import http.client
import urllib.parse
import json


class MergeProxy:
    pass


class SSBAPI:
    def __init__(self, http_connection):
        self.conn = http_connection
        self.authentication_token = None

    def login(self, username, password):
        params = urllib.parse.urlencode({'username': username, 'password': password})
        headers = {"Content-type": "application/x-www-form-urlencoded",
                  "Accept": "text/plain"}
        self.conn.request("POST", "/api/1/login", params, headers)
        try:
            response = self.conn.getresponse()
            response_body = json.loads(response.readall().decode())
            self.authentication_token = response_body['result']
        except Exception:
            pass  # no error handling for now...

    def list_logspaces(self):
        return self._get_response_for_query("/api/1/search/logspace/list_logspaces")

    def _get_response_for_query(self, get_query):
        self._authenticated_get_query(get_query)
        response = self.conn.getresponse()
        raw_response = response.readall().decode()
        response_body = json.loads(raw_response)
        return response_body['result']

    def _authenticated_get_query(self, get_query):
        self.conn.request("GET", get_query,
                          headers={
                              "Cookie": urllib.parse.urlencode({"AUTHENTICATION_TOKEN": self.authentication_token})
                          })

    def logout(self):
        self._authenticated_get_query("/api/1/logout")

    def filter(self, logspace, from_timestamp=0, to_timestamp=9999999999, search_expression=None, offset=0, limit=10):
        return self._filter_type_command("filter", logspace,
                                         from_timestamp, to_timestamp, search_expression,
                                         offset, limit)

    def _filter_type_command(self, command, logspace, from_timestamp, to_timestamp, search_expression=None, offset=None, limit=None):
        params = {'from': from_timestamp, 'to': to_timestamp}

        if offset is not None:
            params['offset'] = offset
        if limit is not None:
            params['limit'] = limit
        if search_expression is not None:
            params['search_expression'] = search_expression

        params_urlencoded = urllib.parse.urlencode(params)

        return self._get_response_for_query("/api/1/search/logspace/%s/%s?%s" % (command, logspace, params_urlencoded))


    def number_of_messages(self, logspace, from_timestamp=0, to_timestamp=9999999999, search_expression=None, offset=0, limit=10):
        return self._filter_type_command("number_of_messages", logspace,
                                         from_timestamp, to_timestamp, search_expression)

class SSB(SSBAPI):
    def __init__(self, address):
        connection = http.client.HTTPSConnection(address)
        super().__init__(connection)


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
    ssb = SSB('10.120.29.121')
    ssb.login('admin', 'a')
    print(ssb.list_logspaces())
    print(ssb.number_of_messages(logspace = 'local', search_expression='statistics'))