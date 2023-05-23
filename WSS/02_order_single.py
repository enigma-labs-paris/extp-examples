# This code sample shows how to connect to Enigma Websocket,
# send an order over it and wait for result.

import json
import asyncio
import websockets
import ssl
from enum import IntEnum
from pprint import pprint

EXTP_WSS = "wss://staging-extp.enigma-securities.io/ws"
API_TOKEN = '<YOUR_API_TOKEN>'

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
    GTC = 2


class WS_ORDER_SIDE (IntEnum):
    BUY = 1,
    SELL = 2


class WS_SUB_TYPE (IntEnum):
    MARKET_DATA = 1,
    ORDER_UPDATES = 2


async def subscribe_order_updates(ws):
    subs = [{'type': WS_SUB_TYPE.ORDER_UPDATES}]
    await ws.send(json.dumps({'type': WS_ACTION.SUBSCRIBE, 'subscriptions': subs}))


async def place_order(ws, order_type, instrument, side, size, tif=None, limit_price=None, client_order_id=None):
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

    if (client_order_id != None):
        payload["client_order_id"] = client_order_id

    print("executing order: {}".format(payload))
    await ws.send(json.dumps({'type': WS_ACTION.ORDER, 'data': {'order': payload}}))


async def authorize(ws):
    print("authenticating..")
    await ws.send(json.dumps({'type': WS_ACTION.AUTH, 'auth_token':  API_TOKEN}))


async def ws_run():

    global websocket

    ssl_context = ssl.SSLContext()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    websocket = await websockets.connect(EXTP_WSS, ssl=ssl_context)

    # First we authenticate on websocket.
    await authorize(websocket)

    # Then we subscribe to the order-updates channel.
    await subscribe_order_updates(websocket)

    # Then we wait for result to be received and display the output on stdout.
    while True:
        jresp = await websocket.recv()
        payload = json.loads(jresp)
        if payload['type'] == 'order-updates':
            pprint(payload)


async def main():

    global websocket
    global total_orders
    global filled_orders
    global unvalidated_orders

    ws = asyncio.create_task(ws_run())
    await asyncio.sleep(2)
    # Places BUY order on BTC-USD for 0.01
    await place_order(websocket, WS_ORDER_TYPE.MARKET, "BTC-USD", WS_ORDER_SIDE.BUY, size=0.01)
    await ws

asyncio.run(main())
