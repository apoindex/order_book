import pandas as pd
import numpy as np

import enum
import queue
from collections import defaultdict


class Side(enum.Enum):
    BUY = 1
    SELL = 0


class Order:
    def __init__(self, timestamp, action, price, side, qty, oid):
        """
        Single Order object
        timestamp: time of the order
        price: price
        side: 1=buy, 0=sell
        qty: order quantity
        oid: order id
        """
        self.timestamp = timestamp
        self.action = action
        self.price = price
        self.side = side
        self.qty = qty
        self.oid = oid


@staticmethod
def price_doesnt_match(order, price):
    if order.side == Side.BUY:
        return order.price < price
    else:
        return order.price > price


class OrderBook():
    def __init__(self, price_levels: int, verbose: bool = False):
        '''
        Order book data object for 3Red codetest
        '''
        self.data = defaultdict(list)
        self.price_levels = price_levels

        self.bids = defaultdict(list)
        self.asks = defaultdict(list)
        self.order_queue = queue.Queue()
        self.bid_prices = []
        self.ask_prices = []
        self.bid_qtys = []
        self.ask_qtys = []

        self.verbose = verbose

    @property
    def best_bid(self):
        if self.bids:
            return max(self.bids.keys())
        else:
            return 0.

    @property
    def best_ask(self):
        if self.asks:
            return min(self.asks.keys())
        else:
            return float('inf')

    def process_order(self, incoming_order):
        """ Main order processing function. Handle order book behavior for add, modify, delete"""
        if incoming_order.action == 'a':
            if incoming_order.side == Side.BUY:
                self.bids[incoming_order.price].append(incoming_order)
            else:
                self.asks[incoming_order.price].append(incoming_order)
            self.output_order(incoming_order)

        elif incoming_order.action == 'm':
        # TODO(andrew): Respect order_modify rules. should rule move to front of queue if px level changes / if quantity changes?
                if incoming_order.side == Side.BUY:
                    for i, existing_order in enumerate(self.bids[incoming_order.price]):
                        if existing_order.oid == incoming_order.oid:
                            if self.verbose:
                                print(f'modifying oid {existing_order.oid}')
                                print(f'existing_order: timestamp:{existing_order.timestamp} - action:{existing_order.action} - price:{existing_order.price} - side:{existing_order.side} - qty:{existing_order.qty}')
                                print(f'modified_order: timestamp:{incoming_order.timestamp} - action:{incoming_order.action} - price:{incoming_order.price} - side:{incoming_order.side} - qty:{incoming_order.qty}')
                            self.bids[incoming_order.price][i] = incoming_order
                            self.output_order(incoming_order)
                            break
                else:
                    for i, existing_order in enumerate(self.asks[incoming_order.price]):
                        if existing_order.oid == incoming_order.oid:
                            if self.verbose:
                                print(f'modifying oid {existing_order.oid}')
                                print(f'existing_order: timestamp:{existing_order.timestamp} - action:{existing_order.action} - price:{existing_order.price} - side:{existing_order.side} - qty:{existing_order.qty}')
                                print(f'modified_order: timestamp:{incoming_order.timestamp} - action:{incoming_order.action} - price:{incoming_order.price} - side:{incoming_order.side} - qty:{incoming_order.qty}')
                            self.asks[incoming_order.price][i] = incoming_order
                            self.output_order(incoming_order)
                            break

        elif incoming_order.action == 'd':
            if self.verbose:
                print(f'delete oid {incoming_order.oid} from px level {incoming_order.price}')
            if incoming_order.side == Side.BUY:  # remove order from px_level
                self.bids[incoming_order.price] = [o for o in self.bids[incoming_order.price] if o.oid != incoming_order.oid]
                if len(self.bids[incoming_order.price]) == 0:
                    self.bids.pop(incoming_order.price)
            else:
                self.asks[incoming_order.price] = [o for o in self.asks[incoming_order.price] if o.oid != incoming_order.oid]
                if len(self.asks[incoming_order.price]) == 0:
                    self.asks.pop(incoming_order.price)
            self.output_order(incoming_order)
        else:
            print('not a valid action type')
            return

    def output_order(self, incoming_order):
        '''
        Create a view of the current order book with every given order update
        this will eventually be the final dataframe / csv of the order book
        '''
        self.bid_prices = sorted(self.bids.keys(), reverse=True)
        self.ask_prices = sorted(self.asks.keys())
        self.bid_qtys = [sum(o.qty for o in self.bids[p]) for p in self.bid_prices]
        self.ask_qtys = [sum(o.qty for o in self.asks[p]) for p in self.ask_prices]

        self.data['timestamp'].append(incoming_order.timestamp)
        self.data['oid'].append(incoming_order.oid)
        self.data['action'].append(incoming_order.action)
        self.data['price'].append(incoming_order.price)
        self.data['side'].append(incoming_order.side.value)
        self.data['qty'].append(incoming_order.qty)

        # establish best bid price levels. two separate loops for column organization
        for lvl in reversed(range(self.price_levels)):
            if lvl == 0:
                self.data['bq0'].append(self.bid_qtys[0] if self.bid_qtys else 0)
                self.data['bp0'].append(self.best_bid)
            else:
                self.data[f'bq{lvl}'].append(self.bid_qtys[lvl] if len(self.bid_qtys) > lvl else 0)
                self.data[f'bp{lvl}'].append(self.bid_prices[lvl] if len(self.bid_prices) > lvl else np.nan)

        # establish ask price levels
        for lvl in range(self.price_levels):
            if lvl == 0:
                self.data['ap0'].append(self.best_ask)
                self.data['aq0'].append(self.ask_qtys[0] if self.ask_qtys else 0)
            else:
                self.data[f'ap{lvl}'].append(self.ask_prices[lvl] if len(self.ask_prices) > lvl else np.nan)
                self.data[f'aq{lvl}'].append(self.ask_qtys[lvl] if len(self.ask_qtys) > lvl else 0)

    def show_book(self):
        print('Sell side:')
        if len(self.ask_prices) == 0:
            print('EMPTY')
        for i, price in reversed(list(enumerate(self.ask_prices))):
            print('{0}) Price={1}, Total units={2}'.format(i+1, self.ask_prices[i], self.ask_sizes[i]))
        print('Buy side:')
        if len(self.bid_prices) == 0:
            print('EMPTY')
        for i, price in enumerate(self.bid_prices):
            print('{0}) Price={1}, Total units={2}'.format(i+1, self.bid_prices[i], self.bid_sizes[i]))
        print()

    def build_book_df(self):
        df = pd.DataFrame.from_dict(self.data, orient="index").T
        return df


def print_order(order):
    print(order.timestamp, order.oid, order.action, order.price, order.side, order.qty)


if __name__ == '__main__':
    df_in = pd.read_csv("C:/Users/Andrew/Downloads/3rqtest/codetest/res_20190610.csv")
    # testing
#    df_in = df_in.head(1000)

    ob = OrderBook(price_levels=5, verbose=False)
    for i in range(len(df_in)):
        timestamp = df_in['timestamp'][i]
        side =  Side(1) if (df_in['side'][i]) == 'b' else Side(0)
        action = df_in['action'][i]
        oid = df_in['id'][i]
        price = df_in['price'][i]
        qty = df_in['quantity'][i]

        new_order = Order(timestamp, action, price, side, qty, oid)
        ob.order_queue.put(new_order)
        while not ob.order_queue.empty():
            ob.process_order(ob.order_queue.get())

        df_out = ob.build_book_df()

