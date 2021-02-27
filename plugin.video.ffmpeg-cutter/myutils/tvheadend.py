# coding=utf-8

import json
import http.client
import urllib.parse
from myutils import kodiutils

def _requestHttp(url):

    parse = urllib.parse.urlparse(url)
    if parse.scheme == "https":
        conn = http.client.HTTPSConnection(parse.netloc)
    else:
        conn = http.client.HTTPConnection(parse.netloc)

    # headers = {'user-agent': "Mozilla/5.0"}
    conn.request("GET", parse.path + (("?" + parse.query)
                                      if parse.query != "" else ""))
    res = conn.getresponse()
    data = res.read()
    return data.decode("utf-8")


def query_hts_finished_recordings(host, http_port, username, password):

    url = "http://%s:%s/api/dvr/entry/grid_finished?limit=%i" % (
        host, http_port, 999999)

    response = _requestHttp(url)

    return json.loads(response)