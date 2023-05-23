# This code sample shows to to connect to EXTP websocket,
# subscribe to market data and then use streamed prices to
# pass lim FOK orders, this time over RESTAPI.
#
# In the main loop, a buy order for 0.001 BTC-USD is sent,
# then we wait 3s, then a sell order for 0.001 BTC-USD is sent.

import json
import asyncio
import websockets
import ssl
from enum import IntEnum
from pprint import pprint
import http.client

EXTP_WSS = "wss://staging-extp.enigma-securities.io/ws"
EXTP_REST = "staging-extp.enigma-securities.io"

API_TOKEN = '<YOUR_API_TOKEN>'

# these values are static, for the sake of example.
ORDER_QTY = 0.001
ORDER_INST = "BTC-USD"

websocket = None


class WS_ACTION (IntEnum):
    SUBSCRIBE = 1,
    UNSUBSCRIBE = 2,
    ORDER = 3,
    AUTH = 4


class WS_ORDER_TYPE (IntEnum):
    MARKET = 1,
    MARKET_NOMINAL = 2,
    LIMIT = 3,


class WS_TIF_TYPE (IntEnum):
    FOK = 1


class WS_ORDER_SIDE (IntEnum):
    BUY = 1,
    SELL = 2


class WS_SUB_TYPE (IntEnum):
    MARKET_DATA = 1,
    ORDER_UPDATES = 2


pricebook = {}


async def subscribe_order_updates(ws):
    """
    function that sends order-updates subscription payload to WSS
    """

    subs = [{'type': WS_SUB_TYPE.ORDER_UPDATES}]
    await ws.send(json.dumps({'type': WS_ACTION.SUBSCRIBE, 'subscriptions': subs}))


async def subscribe_mdata(ws, instruments=[]):
    """
    function that sends MD subscription payload to WSS
    """

    subs = [{'type': WS_SUB_TYPE.MARKET_DATA, 'instrument': inst}
            for inst in instruments]
    await ws.send(json.dumps({'type': WS_ACTION.SUBSCRIBE, 'subscriptions': subs}))


# Function that sends order over REST
def limfok_rest(instrument, side, qty, limit_price):

    conn = http.client.HTTPSConnection(EXTP_REST)
    headers = {
        'X-API-KEY': API_TOKEN,
        'content-type': 'application/json'
    }

    order_params = {
        "order_type": "market",
        "side": side,
        "quantity": qty,
        "instrument": instrument,
        "limit_price": limit_price
    }

    conn.request("POST", "/api/v1/order", json.dumps(order_params), headers)
    res = conn.getresponse()
    data = res.read()
    jresp = json.loads(data)
    pprint(jresp)


async def authorize(ws):
    print("authenticating..")
    await ws.send(json.dumps({'type': WS_ACTION.AUTH, 'auth_token':  API_TOKEN}))


async def ws_run():
    """
    Websocket Run Function
    """

    global websocket

    ssl_context = ssl.SSLContext()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    websocket = await websockets.connect(EXTP_WSS)

    # First we authenticate on websocket.
    await authorize(websocket)

    # Then we subscribe to some instrument market data
    await subscribe_mdata(websocket, [ORDER_INST])

    # Then we subscribe to the order-updates channel.
    await subscribe_order_updates(websocket)

    # Then we process incoming WS stream coming from EXTP
    while True:
        jresp = await websocket.recv()
        payload = json.loads(jresp)

        if payload['type'] == 'client-streamquotes':

            # we received market data update, so we update related pricebook entry accordingly
            pricebook[payload['symbol']] = payload['data']

        elif payload['type'] == 'order-dispatch-ack':
            if payload['status'] == 0:
                print("Order Request Passed!")
            elif payload['status'] < 0:
                print("Order early Rejectected!")

        elif payload['type'] == 'order-updates':
            pprint(payload)


async def main():

    global websocket

    ws = asyncio.create_task(ws_run())
    await asyncio.sleep(2)

    # main loop: at each iteration we try to pass a BUY order, then wait 3s,
    # then try to pass a SELL order, then wait 3s.
    while True:

        # We pick correct price/side from uptodate pricebook,
        # which is next level from ORDER_QTY (2)
        limit_price = [dot["price"] for dot in pricebook[ORDER_INST]
                       ['ask'] if dot["qty"] == 2][0]

        # We add 1bps of slippage to limit_price in order to make exec smoother.
        limit_price *= 1 + 1 / 10000

        limfok_rest(ORDER_INST, "buy", ORDER_QTY, limit_price)
        await asyncio.sleep(3)

        # We pick correct price/side from uptodate pricebook,
        # which is next level from ORDER_QTY (2)
        limit_price = limit_price = [dot["price"] for dot in pricebook[ORDER_INST]
                                     ['bid'] if dot["qty"] == 2][0]

        # We add 1bps of slippage to limit_price in order to make exec smoother.
        limit_price *= 1 - 1 / 10000

        limfok_rest(ORDER_INST, "sell", ORDER_QTY, limit_price)
        await asyncio.sleep(3)

asyncio.run(main())
