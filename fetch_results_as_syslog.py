#!/usr/bin/python

import urllib
import urllib2
import json
import datetime
import sys
import urlparse

# FIXME: this is NASTY, dangerous and prone to parsing errors....
config_infos = {}
execfile("ssb_credentials", config_infos)
ssb_ip = config_infos['SSB_IP']
username = config_infos['USERNAME']
password = config_infos['PASSWORD']

auth_token = None

def call_rpc(method, command, arguments):
    url = 'https://%s/api/1/%s' % (ssb_ip, command)
    data = urllib.urlencode(arguments)

    if method == 'post':
        request = urllib2.Request(url, data)
    if method == 'get':
        request = urllib2.Request('%s?%s' % (url, data))
        request.add_header('Cookie', 'AUTHENTICATION_TOKEN=%s;' % auth_token)

    response = urllib2.urlopen(request).read()
    return json.loads(response)

def login():
    global auth_token

    response = call_rpc('post', 'login', {'username': username, 'password': password})
    auth_token = response['result']

def call_filter(logspace_name, from_timestamp, to_timestamp, search_expression, offset):
    return call_rpc('get', 'search/logspace/filter/%s' % logspace_name, {'from': from_timestamp,
                                                                         'to': to_timestamp,
                                                                         'search_expression': search_expression,
                                                                         'offset': offset,
                                                                         'limit': 1000})

def print_log(log):
    log['date'] = datetime.datetime.fromtimestamp(int(log['timestamp'])).strftime('%Y-%m-%dT%H:%M:%S')

    print ('%(date)s %(host)s %(program)s[%(pid)s]: %(message)s' % log).encode('utf-8')

def parse_query_url(query_url):
    parsed = urlparse.urlparse(query_url)
    params = urlparse.parse_qs(parsed.fragment)
    return {'logspace': params['logspace_name'][0],
            'from': params['from'][0],
            'to': params['to'][0],
            'search_expression':
                params['search_expression'][0] if 'search_expression' in params else ""}

def main():
    login()
    query = parse_query_url(sys.argv[1])
    offset = 0
    while True:
        logs = call_filter(query['logspace'], query['from'], query['to'], query['search_expression'], offset)['result']
        if len(logs) == 0:
            return 0
        for log in logs:
            print_log(log)
        offset += len(logs)

if __name__ == '__main__':
    main()
