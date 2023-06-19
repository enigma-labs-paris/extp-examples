#!/usr/bin/env python3

import argparse
import datetime
import numpy
import threading
import time
import simplefix
import socket
import ssl
import sys


class fix_client:
    def __init__(self, hostname, port, sender_comp_id, target_comp_id, username, password):
        self.hostname = hostname
        self.port = port

        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id
        self.msg_seq_num = 1

        self.username = username
        self.password = password

        self.market_data_bid = {}
        self.market_data_offer = {}
        self.log_market_data = True

        self.running = False
        self.logged = False

        self.parser = simplefix.FixParser()

    def run(self):
        self.running = True

        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ssock = context.wrap_socket(sock)

        self.ssock.settimeout(5)
        self._log('Connecting on', self.hostname +
                  ':' + str(self.port) + '...')
        self.ssock.connect((self.hostname, self.port))
        self._log('Connected on', self.hostname + ':' + str(self.port))

        self._send_logon()

        while self.running:
            try:
                self._recv_msg()
            except TimeoutError:
                pass

    def stop(self):
        self.running = False

    def send_market_data_request(self, symbols):
        msg = self._msg_header('V')
        msg.append_pair(262, 'MDID0')  # MDReqID
        msg.append_pair(263, 1)  # SubscriptionRequestType
        msg.append_pair(264, 0)  # MarketDepth
        msg.append_pair(265, 0)  # MDUpdateType
        msg.append_pair(267, 2)  # NoMDEntryTypes
        msg.append_pair(269, 0)  # MDEntryType "bid"
        msg.append_pair(269, 1)  # MDEntryType "offer"
        msg.append_pair(146, len(symbols))  # NoRelatedSym
        for symbol in symbols:
            msg.append_pair(55, symbol)  # Symbol
        self._send_msg(msg)

    def get_extp_bid(self, symbol, quantity):
        return fix_client._get_price(self.market_data_bid[symbol], quantity)

    def get_extp_offer(self, symbol, quantity):
        return fix_client._get_price(self.market_data_offer[symbol], quantity)

    def place_order_market_buy(self, id, symbol, quantity):
        msg = self._msg_new_order_single_header(id, symbol, '1', quantity)
        msg.append_pair(40, '1')  # OrdType "market"
        self._send_msg(msg)

    def place_order_market_sell(self, id, symbol, quantity):
        msg = self._msg_new_order_single_header(id, symbol, '2', quantity)
        msg.append_pair(40, '1')  # OrdType "market"
        self._send_msg(msg)

    def place_order_limit_fok_buy(self, id, symbol, quantity, limit_price):
        msg = self._msg_new_order_single_header(id, symbol, '1', quantity)
        msg.append_pair(40, '2')  # OrdType "limit"
        msg.append_pair(44, limit_price)  # Price
        msg.append_pair(59, 4)  # TimeInForce "fill or kill"
        self._send_msg(msg)

    def place_order_limit_fok_sell(self, id, symbol, quantity, limit_price):
        msg = self._msg_new_order_single_header(id, symbol, '2', quantity)
        msg.append_pair(40, '2')  # OrdType "limit"
        msg.append_pair(44, limit_price)  # Price
        msg.append_pair(59, 4)  # TimeInForce "fill or kill"
        self._send_msg(msg)

    def _log(self, *args):
        print('[' + self.target_comp_id + ']', *args)

    def _get_price(quantities_and_prices, quantity):
        return numpy.interp(quantity, quantities_and_prices[0], quantities_and_prices[1], left=None, right=0)

    def _msg_header(self, msg_type):
        msg = simplefix.FixMessage()
        msg.append_pair(8, "FIX.4.4", header=True)  # BeginString
        msg.append_pair(35, msg_type, header=True)  # MsgType
        msg.append_pair(49, self.sender_comp_id, header=True)  # SenderCompID
        msg.append_pair(56, self.target_comp_id, header=True)  # TargetCompID
        msg.append_pair(34, self.msg_seq_num, header=True)  # MsgSeqNum
        msg.append_time(52, header=True)  # SendingTime
        self.msg_seq_num += 1
        return msg

    def _msg_new_order_single_header(self, id, symbol, side, quantity):
        msg = self._msg_header('D')
        msg.append_pair(11, id)  # ClOrdID
        msg.append_pair(55, symbol)  # Symbol
        msg.append_pair(54, side)  # Side
        msg.append_time(60)  # TransactTime
        msg.append_pair(38, quantity)  # OrderQty
        return msg

    def _send_logon(self):
        msg = self._msg_header('A')
        msg.append_pair(98, 0)  # EncryptMethod
        msg.append_pair(108, 60)  # HeartBtInt
        msg.append_pair(141, 'Y')  # ResetSeqNumFlag
        msg.append_pair(553, self.username)  # Username
        msg.append_pair(554, self.password)  # Password
        self._send_msg(msg)

    def _send_msg(self, msg):
        self._log('Sending', msg, '...')
        self.ssock.send(msg.encode())
        self._log('Sent:', msg)

    def _recv_msg(self):
        data = self.ssock.recv()
        self.parser.append_buffer(data)

        while True:
            msg = self.parser.get_message()
            if msg == None:
                break

            if msg.get(35) == b'A':
                self._log('Received Logon:', msg)
                self.logged = True

            elif msg.get(35) == b'W':
                if self.log_market_data:
                    self._log('Received market data:', msg)
                symbol = msg.get(55).decode('utf-8')
                nb_md = int(msg.get(268))
                if self.log_market_data:
                    self._log(nb_md, 'entries for', symbol)
                self.market_data_bid[symbol] = ([], [])
                self.market_data_offer[symbol] = ([], [])
                for i in range(1, nb_md):
                    if msg.get(269, i) == b'0':
                        market_data = self.market_data_bid[symbol]
                    elif msg.get(269, i) == b'1':
                        market_data = self.market_data_offer[symbol]
                    market_data[0].append(float(msg.get(271, i)))
                    market_data[1].append(float(msg.get(270, i)))
                if self.log_market_data:
                    self._log('BID:', self.market_data_bid)
                    self._log('OFFER:', self.market_data_offer)

            elif msg.get(35) == b'8':
                self._log('Received ExecutionReport:', msg)
                self._log('- ClOrdID / OrderID', msg.get(11), '/', msg.get(37))
                if msg.get(39) == b'0':
                    self._log('- OrdStatus NEW')
                elif msg.get(39) == b'8':
                    self._log('- OrdStatus REJECTED')
                    self._log('- Text', msg.get(58))
                elif msg.get(39) == b'2':
                    self._log('- OrdStatus FILLED')
                    self._log('- AvgPx', msg.get(6))
                else:
                    self._log('- OrdStatus UNKNOWN')

            elif msg.get(35) == b'5':
                self._log('Received Logout:', msg)
                self.logged = False

            else:
                self._log('Received unknown message:', msg)


def run_fix_client_in_thread(fix_session):
    thread = threading.Thread(None, lambda: fix_session.run())
    thread.start()
    for i in range(10):
        time.sleep(0.5)
        if fix_session.logged:
            break
    if fix_session.logged == False:
        print('[ERROR] Cannot get a logon from', fix_session.target_comp_id)
        sys.exit(1)
    return thread


if __name__ == "__main__":

    print('EXTP FIX client example:')
    print('This example:')
    print('- tries to be minimal')
    print('- retrieves market data from the market data session')
    print('- places MARKET orders')
    print('- places LIMIT/FOK orders using the market data')
    print('This example DOES NOT:')
    print('- handle possible errors')
    print('- handle all possible FIX messages')
    print('- handle or send Hearbeat and TestRequest messages')
    print()

    parser = argparse.ArgumentParser()
    parser.add_argument('hostname', help='Hostname of the FIX server')
    parser.add_argument('sender_comp_id', help='Sender Comp ID')
    parser.add_argument('target_comp_id_prefix', help='Target Comp ID Prefix')
    parser.add_argument('username', help='Username')
    parser.add_argument('password', help='Password')
    args = parser.parse_args()
    market_data_port = 40001
    market_access_port = 40002

    # Market Data Session
    market_data_session = fix_client(args.hostname, market_data_port, args.sender_comp_id,
                                     args.target_comp_id_prefix + '_MDATA', args.username, args.password)
    run_fix_client_in_thread(market_data_session)

    # Display some market data for few seconds
    market_data_session.send_market_data_request(
        ['BTC-USD', 'ETH-USD', 'LTC-USD'])
    time.sleep(3)
    market_data_session.log_market_data = False
    print()

    # Order Session
    order_session = fix_client(args.hostname, market_access_port, args.sender_comp_id,
                               args.target_comp_id_prefix + '_ORDER', args.username, args.password)
    run_fix_client_in_thread(order_session)

    # Placing Orders
    now = str(datetime.datetime.now().timestamp())
    symbol = 'BTC-USD'
    qty = 0.001
    limit_fok_slippage = 0.0
    sleep_after_order = 1

    order_session.place_order_market_buy(
        now + '-buy-market', symbol, qty)
    time.sleep(sleep_after_order)
    print()

    order_session.place_order_market_sell(
        now + '-sell-market', symbol, qty)
    time.sleep(sleep_after_order)
    print()

    order_session.place_order_limit_fok_buy(
        now + '-buy-limit-fok', symbol, qty, market_data_session.get_extp_offer(symbol, qty) + limit_fok_slippage)
    time.sleep(sleep_after_order)
    print()

    order_session.place_order_limit_fok_sell(
        now + '-sell-limit-fok', symbol, qty, market_data_session.get_extp_bid(symbol, qty) - limit_fok_slippage)
    time.sleep(sleep_after_order)
    print()

    # Waiting for execution reports
    time.sleep(3)

    # Stop
    order_session.stop()
    market_data_session.stop()
    sys.exit(0)
