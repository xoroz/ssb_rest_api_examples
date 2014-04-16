__author__ = 'gyp@balabit.com'
import http.client
import urllib.parse
import json
import datetime
import cherrypy


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
        return set(self._get_response_for_query("/api/1/search/logspace/list_logspaces"))

    def _get_response_for_query(self, get_query):
        self._authenticated_get_query(get_query)
        response = self.conn.getresponse()
        raw_response = response.readall().decode()
        response_body = json.loads(raw_response)
        self.conn.close()
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


class MergeProxy(SSBAPI):
    # FIXME: the logspace should be the unit here, not the SSB
    def __init__(self, ssbs):
        self.ssbs = ssbs

    # TODO: it could be a nice shortcut to do it simultaneously for all SSBs
    def login(self, username, password):
        raise NotImplementedError

    # TODO: it could be a nice shortcut to do it simultaneously for all SSBs
    def logout(self):
        raise NotImplementedError

    def list_logspaces(self):
        # FIXME: this is not parallel!!! it HAS to be unless it will be very-very slow
        logspaces = set()
        for ssb_instance in self.ssbs:
            logspaces |= ssb_instance.list_logspaces()
        return logspaces

    def number_of_messages(self, logspace, from_timestamp=0, to_timestamp=9999999999, search_expression=None):
        # FIXME: this is not parallel!!! it HAS to be unless it will be very-very slow
        # FIXME: logspace has to be the same, it could easily be separate...
        merged_number = 0
        for ssb_instance in self.ssbs:
            merged_number += ssb_instance.number_of_messages(logspace, from_timestamp, to_timestamp, search_expression)
        return merged_number

    def filter(self, logspace, from_timestamp=0, to_timestamp=9999999999, search_expression=None, offset=0, limit=10):
        # FIXME: this is not parallel!!! it HAS to be unless it will be very-very slow
        if (offset > 0):
            raise NotImplementedError  # TODO: this would really be needed but that needs the k-way merge

        logs = []
        for ssb_instance in self.ssbs:
            logs += ssb_instance.filter(logspace, from_timestamp, to_timestamp, search_expression,
                                        offset=0, limit=limit)

        logs = sorted(logs, key=lambda log: log['processed_timestamp'])
        logs = logs[:int(limit)]
        return(logs)


class MergeProxyServer:
    # FIXME: all the results should be wrapped into the required base structure
    def __init__(self, merge_proxy: MergeProxy):
        self.merge_proxy = merge_proxy

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def list_logspaces(self):
        return self._json_safe_object(self.merge_proxy.list_logspaces())

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def filter(self, logspace, **kwargs):
        result = self.merge_proxy.filter(logspace, **kwargs)
        return self._json_safe_object(result)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def number_of_messages(self, logspace, **kwargs):
        result = self.merge_proxy.number_of_messages(logspace, **kwargs)
        return self._json_safe_object(result)

    def _json_safe_object(self, object_to_convert):
        if type(object_to_convert) == type(set()):
            object_to_convert = list(object_to_convert)
        return object_to_convert


def print_logs(list_of_logs):
    for log in list_of_logs:
        pretty_date = datetime.datetime.fromtimestamp(log['processed_timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        print("%s %s %s: %s" % (pretty_date, log['host'], log['program'], log['message']))

if __name__ == '__main__':
    # FIXME: move this out to a configfile
    ssb1 = SSB('10.120.29.121')
    ssb2 = SSB('10.120.29.122')
    ssb1.login('admin', 'a')
    ssb2.login('admin', 'a')

    merge_proxy = MergeProxy((ssb1, ssb2))
    server = MergeProxyServer(merge_proxy)

    cherrypy.tree.mount(
        server, '/api/1/search/logspace'
    )
    cherrypy.server.ssl_module = 'builtin'
    cherrypy.server.ssl_certificate = "merge_proxy.pem"
    cherrypy.server.ssl_private_key = "merge_proxy.pem"
    cherrypy.engine.start()
    cherrypy.engine.block()





