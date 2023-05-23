# This code sample shows how to continuously send Requests for Quotes,
# then use fetched prices to pass LIMFOK orders over RESTAPI.

import http.client
import json
import time
import random
from pprint import pprint

EXTP_REST = "staging-extp.enigma-securities.io"
API_TOKEN = '<YOUR_API_TOKEN>'

sleep_time = 3
conn = http.client.HTTPSConnection(EXTP_REST)

headers = {
    'X-API-KEY': API_TOKEN,
    'Content-Type': 'application/json',
}

inst_list = ["BTC-USD", "ETH-USD", "LTC-USD"]
qty_list = [0.01, 0.1, 0.5, 1]


def rfq(rfq_params):
    conn.request("POST", "/api/v1/rfq", json.dumps(rfq_params), headers)
    res = conn.getresponse()
    jrfq = json.loads(res.read().decode('utf-8'))
    try:
        return jrfq["response"]["quote_price"]
    except:
        return 0


def order(params):

    conn.request("POST", "/api/v1/order", json.dumps(params), headers)
    res = conn.getresponse()
    data = res.read().decode('utf-8')
    jres = json.loads(data)
    return jres


for x in range(100):

    inst = random.choice(inst_list)
    qty = random.choice(qty_list)

    rfq_params = {
        "instrument": inst,
        "quantity": qty,
        "side": "buy"
    }

    order_params = {
        "order_type": "limit",
        "tif": "FOK",
        "side": "buy",
        "quantity": qty,
        "instrument": inst,
        "limit_price": 0.0
    }

    order_params["limit_price"] = rfq(rfq_params)
    if order_params["limit_price"] != 0:
        res = order(order_params)
        pprint(res)

    rfq_params = {
        "instrument": inst,
        "quantity": qty,
        "side": "sell"
    }

    order_params = {
        "order_type": "limit",
        "tif": "FOK",
        "side": "sell",
        "quantity": qty,
        "instrument": inst,
        "limit_price": 0.0
    }

    order_params["limit_price"] = rfq(rfq_params)
    if order_params["limit_price"] != 0:

        res = order(order_params)
        pprint(res)

    time.sleep(sleep_time)
