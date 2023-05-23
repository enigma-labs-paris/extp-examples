# This sample shows how to connect to EXTP WSS,
# subscribe to market data and receive price updates.

import json
from pprint import pprint
import websockets
import asyncio
from enum import IntEnum
import ssl

EXTP_WSS = 'wss://staging-extp.enigma-securities.io/ws'
API_TOKEN = '<YOUR_API_TOKEN>'

DEFAULT_SUBSCRIPTIONS = ["BTC-USD", "ETH-USD", "LTC-USD"]


class WS_ACTION (IntEnum):
    SUBSCRIBE = 1,
    UNSUBSCRIBE = 2,
    ORDER = 3,
    AUTH = 4


class WS_ORDER_TYPE (IntEnum):
    MARKET = 1,
    MARKET_NOMINAL = 2,
    LIMIT = 3,


class WS_ORDER_SIDE (IntEnum):
    BUY = 1,
    SELL = 2


class WS_SUB_TYPE (IntEnum):
    MARKET_DATA = 1,
    ORDER_UPDATES = 2


async def authorize(ws):
    print("authenticating..")
    await ws.send(json.dumps({'type': WS_ACTION.AUTH, 'auth_token': API_TOKEN}))


async def subscribe_mdata(ws, instruments=[]):
    subs = [{'type': WS_SUB_TYPE.MARKET_DATA, 'instrument': inst, "provider": "aggregated"}
            for inst in instruments]
    await ws.send(json.dumps({"type": 1, "subscriptions": subs}))


## websocket callbacks ##

async def ws_run():

    ssl_context = ssl.SSLContext()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async with websockets.connect(EXTP_WSS) as websocket:
        # First we authenticate on websocket.
        await authorize(websocket)

        # Then we subscribe to some instruments (DEFAULT_SUBSCRIPTIONS list)
        await subscribe_mdata(websocket, DEFAULT_SUBSCRIPTIONS)

        # Finally we receive the stream and display the output on stdout.
        while True:
            jresp = await websocket.recv()
            payload = json.loads(jresp)
            pprint(payload)

if __name__ == "__main__":

    asyncio.get_event_loop().run_until_complete(ws_run())
