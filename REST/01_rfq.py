# The following code sample shows how to send a Request
# for Quote over Enigma REST API and prints result.

import http.client
import json
from pprint import pprint

EXTP_REST = 'staging-extp.enigma-securities.io'
API_TOKEN = '<YOUR_API_TOKEN>'

conn = http.client.HTTPSConnection(EXTP_REST)
headers = {
    'X-API-KEY': API_TOKEN,
    'content-type': 'application/json'
}

payload = json.dumps({"instrument": "BTC-USD", "quantity": 0.5, "side": "buy"})
conn.request("POST", "/api/v1/rfq", payload, headers)
res = conn.getresponse()
data = res.read()
jresp = json.loads(data)

pprint(jresp)
