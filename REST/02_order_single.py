# This code sample shows how to send a single, market order over REST API

import http.client
import json
from pprint import pprint

EXTP_REST = "staging-extp.enigma-securities.io"
API_TOKEN = '<YOUR_API_TOKEN>'

conn = http.client.HTTPSConnection(EXTP_REST)

headers = {
    'X-API-KEY': API_TOKEN,
    'content-type': 'application/json'
}

order_params = {
    "order_type": "market",
    "side": "buy",
    "quantity": 0.01,
    "instrument": "BTC-USD",
}

conn.request("POST", "/api/v1/order", json.dumps(order_params), headers)
res = conn.getresponse()
data = res.read()
jresp = json.loads(data)
pprint(jresp)
