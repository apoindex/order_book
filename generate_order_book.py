import pandas as pd
import numpy as np

import enum
import queue
from collections import defaultdict


#class Side(enum.Enum):
#    BUY = 0
#    SELL = 1
#

def print_order(order):
    print(order.timestamp, order.oid, order.action, order.price, order.side, order.qty)


class Side(enum.Enum):
    BUY = 'b'
    SELL = 'a'


# order object
class Order:
    def __init__(self, timestamp, action, price, side, qty, oid):
        """
        Class representing a single order
        timestamp: time of the order
        price: price in ticks
        side: 0=buy, 1=sell
        qty: order quantity
        order_id: order ID
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
    def __init__(self):
        '''
        Order book data object for 3Red codetest
        '''
        self.bids = defaultdict(list)
        self.asks = defaultdict(list)
        self.order_queue = queue.Queue()
        self.bid_prices = []
        self.ask_prices = []
        self.bid_qtys = []
        self.ask_qtys = []

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
        """ Main order processing function."""
        if incoming_order.action == 'a':
            print('handle order add')
            if incoming_order.side == Side.BUY:
                if incoming_order.price >= self.best_ask and self.asks:
                    self.match_order(incoming_order)
                else:
                    self.bids[incoming_order.price].append(incoming_order)
            else:
                if incoming_order.price <= self.best_bid and self.bids:
                    self.match_order(incoming_order)
                else:
                    self.asks[incoming_order.price].append(incoming_order)

        elif incoming_order.action == 'm':
                print('handle order modify')
                if incoming_order.side == Side.BUY:
                    for i, existing_order in enumerate(self.bids[incoming_order.price]):
                        if existing_order.oid == incoming_order.oid:
                            print(f'modifying oid {existing_order.oid}')
#                            print(f'existing_order: timestamp:{existing_order.timestamp} - action:{existing_order.action} - price:{existing_order.price} - side:{existing_order.side} - qty:{existing_order.qty}')
#                            print(f'modified_order: timestamp:{incoming_order.timestamp} - action:{incoming_order.action} - price:{incoming_order.price} - side:{incoming_order.side} - qty:{incoming_order.qty}')
                            self.bids[incoming_order.price][i] = incoming_order
                            break
                else:
                    for i, existing_order in enumerate(self.asks[incoming_order.price]):
                        if existing_order.oid == incoming_order.oid:
                            print(f'modifying oid {existing_order.oid}')
#                            print(f'existing_order: timestamp:{existing_order.timestamp} - action:{existing_order.action} - price:{existing_order.price} - side:{existing_order.side} - qty:{existing_order.qty}')
#                            print(f'modified_order: timestamp:{incoming_order.timestamp} - action:{incoming_order.action} - price:{incoming_order.price} - side:{incoming_order.side} - qty:{incoming_order.qty}')
                            self.asks[incoming_order.price][i] = incoming_order
                            break

        elif incoming_order.action == 'd':
            print('handle order delete')
#            print(f'delete oid {incoming_order.oid} from px level {incoming_order.price}')
            if incoming_order.side == Side.BUY:  # remove order from px_level
                self.bids[incoming_order.price] = [o for o in self.bids[incoming_order.price] if o.oid != incoming_order.oid]
                if len(self.bids[incoming_order.price]) == 0:
                    self.bids.pop(incoming_order.price)
            else:
                self.asks[incoming_order.price] = [o for o in self.asks[incoming_order.price] if o.oid != incoming_order.oid]
                if len(self.asks[incoming_order.price]) == 0:
                    self.asks.pop(incoming_order.price)

        else:
            print('not a valid action type')
            return

    def match_order(self, incoming_order):
        """ Match an incoming order against orders on the other side of the book, in price-time priority."""
        # get the prices to match incoming_order against
        print('matching order')
        levels = self.bids if incoming_order.side == Side.SELL else self.offers
        reverse_px_list = True if incoming_order.side == Side.SELL else False
        prices = sorted(levels.keys(), reverse=reverse_px_list)

        # iterate over the prices to match the incoming order
        for (i, price) in enumerate(prices):
            if (incoming_order.qty == 0) or (price_doesnt_match(incoming_order, price)):
                break
            orders_at_level = levels[price]
            for (j, book_order) in enumerate(orders_at_level):
                if incoming_order.qty == 0:
                    break
                trade = self.execute_match(incoming_order, book_order)
                incoming_order.qty = max(0, incoming_order.qty - trade.qty)
                book_order.qty = max(0, book_order.qty - trade.qty)
                self.trades.put(trade)
            levels[price] = [o for o in orders_at_level if o.qty > 0]
            if len(levels[price]) == 0:
                levels.pop(price)
        # If the incoming order has not been completely matched, add the remainder to the order book
        if incoming_order.qty > 0:
            same_side = self.bids if incoming_order.side == Side.BUY else self.offers
            same_side[incoming_order.price].append(incoming_order)

    def book_summary(self):
        self.bid_prices = sorted(self.bids.keys(), reverse=True)
        self.ask_prices = sorted(self.asks.keys())
        self.bid_sizes = [sum(o.qty for o in self.bids[p]) for p in self.bid_prices]
        self.ask_sizes = [sum(o.qty for o in self.asks[p]) for p in self.ask_prices]

    def show_book(self):
        self.book_summary()
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

#    def build_book(self):
#        self.book_summary()
#        dfs = []
#        df_order = pd.DataFrame(index=[0], columns=['timestamp', 'price', 'side', 'bq1', 'bp1', 'bq0', 'bp0', 'ap0', 'aq0', 'ap1', 'aq1'])
#        # build sell side
#        if len(self.ask_prices) > 0:
#
#
#        for i, price in reversed(list(enumerate(self.ask_prices))):
#            print('{0}) Price={1}, Total units={2}'.format(i+1, self.ask_prices[i], self.ask_sizes[i]))
#        print('Buy side:')
#        if len(self.bid_prices) == 0:
#            print('EMPTY')
#        for i, price in enumerate(self.bid_prices):
#            print('{0}) Price={1}, Total units={2}'.format(i+1, self.bid_prices[i], self.bid_sizes[i]))
#        print()



if __name__ == '__main__':
    df = pd.read_csv("C:/Users/Andrew/Downloads/3rqtest/codetest/res_20190610.csv")
    # testing
#    df = df.head(10000)
    ob = OrderBook()

    for i in range(len(df)):
        timestamp = df['timestamp'][i]
        side = Side(df['side'][i])
        action = df['action'][i]
        oid = df['id'][i]
        price = df['price'][i]
        qty = df['quantity'][i]

        new_order = Order(timestamp, action, price, side, qty, oid)
        ob.order_queue.put(new_order)
        while not ob.order_queue.empty():
            ob.process_order(ob.order_queue.get())

