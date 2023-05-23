# This code sample shows to to connect to EXTP websocket,
# subscribe to market data and then use streamed prices to
# pass lim FOK orders also over WSS.
#
# In the main loop, a buy order for 0.001 BTC-USD is sent,
# then we wait 3s, then a sell order for 0.001 BTC-USD is sent.

import json
import asyncio
import websockets
import ssl
from enum import IntEnum
from pprint import pprint

EXTP_WSS = "wss://staging-extp.enigma-securities.io/ws"
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


# Function that sends order payload to WSS
async def place_order(ws, order_type, instrument, side, size, tif=None, limit_price=None):
    """
    place_order function: sends and order payload to connected WS.
    :param client_order_id: id of order specified by client, in order to remap with order updates. 
    :param order_type: Type of order, can be either WS_ORDER_TYPE.MARKET (1),  WS_ORDER_TYPE.MARKET_NOMINAL(2)  , or  WS_ORDER_TYPE.LIMIT (3).
    :param instrument: Symbol of intrument that we want to trade, eg: 'BTC-USD'.
    :param side: side of order, can be either 1 (WS_ORDER_SIDE.BUY) or 2 (WS_ORDER_SIDE.SELL)
    :param size: order's quantity, must be a > 0 number.
    :param tif: Time in Force, only if order is of type 'limit'. vlaues can be 'FOK' (fill or kill) or 'GTC' (good til cancelled).
    :param limit_price: price at which to buy/sell, only appliable if order_type is 'limit'.
    """

    payload = {'type': order_type, 'side': side,
               'size': size, 'instrument': instrument}
    if (tif != None):
        payload['tif'] = tif
    if (limit_price != None):
        payload['limit_price'] = limit_price

    print("Sending order {}".format(payload))
    await ws.send(json.dumps({'type': WS_ACTION.ORDER, 'data': {'order': payload}}))


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
            pprint(payload)
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

        # We add .5bps of slippage to limit_price in order to make exec smoother.
        limit_price *= 1 + 0.5 / 10000

        await place_order(websocket, WS_ORDER_TYPE.LIMIT, ORDER_INST, WS_ORDER_SIDE.BUY, ORDER_QTY, WS_TIF_TYPE.FOK, limit_price)
        await asyncio.sleep(3)

        # We pick correct price/side from uptodate pricebook,
        # which is next level from ORDER_QTY (2)
        limit_price = limit_price = [dot["price"] for dot in pricebook[ORDER_INST]
                                     ['bid'] if dot["qty"] == 2][0]

        # We add .5bps of slippage to limit_price in order to make exec smoother.
        limit_price *= 1 - 0.5 / 10000

        await place_order(websocket, WS_ORDER_TYPE.LIMIT, ORDER_INST, WS_ORDER_SIDE.SELL, ORDER_QTY, WS_TIF_TYPE.FOK, limit_price)
        await asyncio.sleep(3)

asyncio.run(main())
