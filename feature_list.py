import pandas as pd
import numpy as np
import bisect


def calculate_rolling_oside(df, window=100):
    '''
    Calculate ratio of order side (buy/sell) over a rolling window
    '''

    df_temp = df.copy()
    df_temp['buys'] = np.where((df_temp['side'] == 1) & (df_temp.action == 'a'), 1, 0)
    df_temp['sells'] = np.where((df_temp['side'] == 0) & (df_temp.action == 'a'), 1, 0)

    df_temp['rolling_buys'] = df_temp['buys'].rolling(window, min_periods=1).sum()
    df_temp['rolling_sells'] = df_temp['sells'].rolling(window, min_periods=1).sum()
    df_temp[f'{window}_period_oside_ratio'] = df_temp['rolling_buys'] / df_temp['rolling_sells']

    df[f'feature_oratio{window}'] = df_temp[f'{window}_period_oside_ratio']
    return df


def calculate_qty_ratio(df, levels=1):
    '''
    Calculate ratio of buy/sell qty across X levels at each order event.
    '''

    aq_cols = [f'aq{lvl}' for lvl in range(levels)]
    bq_cols = [f'bq{lvl}' for lvl in range(levels)]

    df[f'top{levels}_ask_qty'] = df[aq_cols].sum(axis=1)
    df[f'top{levels}_bid_qty'] = df[bq_cols].sum(axis=1)

    df[f'feature_qty_ratio{levels}'] = df[f'top{levels}_bid_qty'] / df[f'top{levels}_ask_qty']
    return df


def calculate_inside_spread(df):
    '''
    Calculate book-spread at each order event.
    Nan until orders are present on both sides
    '''

    df['feature_inside_spread'] = np.where((df['aq0'] > 0) & (df['bq0'] > 0), df['ap0'] - df['bp0'], 0)
    return df


def calculate_px_change(df):
    '''
    Calculate change in price between previous price and new price set by order
    Quantity of previous order must be >0 to account for book being empty at beginning of day
    '''
    df['ask_change'] = np.where(df['aq0'].shift(1) > 0, df['ap0'].diff(), 0)
    df['bid_change'] = np.where(df['bq0'].shift(1) > 0, df['bp0'].diff(), 0)
    df['feature_px_change'] = np.where(df.side == 1, df['bid_change'], df['ask_change'])
    return df


def calculate_vwap(df):
    '''
    Calculate volume weighted average price
    '''
    df_temp = df.copy()
    df_temp['order_px'] = np.where(df_temp['side'] == 1, df_temp['bp0'], df_temp['ap0'])
    df_temp['order_size'] = np.where(df_temp['side'] == 1, df_temp['bq0'], df_temp['aq0'])
    df_temp['vwap'] = (df_temp['order_px'] * df_temp['order_size']).cumsum() / df_temp['order_size'].fillna(0).cumsum()
    df['feature_vwap'] = df_temp['vwap']
    return df


def calculate_midpoint(df):
    '''
    Calculate midpoint of bid/ask spread
    '''
    df['feature_midpoint'] = np.where((df['aq0'] > 0) & (df['bq0'] > 0), (df['ap0'] + df['bp0']) / 2, np.nan)
    return df


def calculate_price_std(df):
    '''
    Calculate ewm of standard deviation of price
    '''
    df_temp = df.copy()
    df_temp['order_px'] = np.where(df_temp['side'] == 1, df_temp['bp0'], df_temp['ap0'])
    df_temp['opx_ewm_std'] = df_temp['order_px'].ewm(alpha=0.01).std().fillna(0)
    df['feature_px_std'] = df_temp['opx_ewm_std']
    return df


def index(a, x, lo):
    '''Locate the leftmost value exactly equal to x'''
    i = bisect.bisect_left(a, x, lo=lo)
    if i != len(a) and a[i] == x:
        return i
    raise ValueError


def find_le(a, x, lo):
    '''Find rightmost value less than or equal to x'''
    i = bisect.bisect_right(a, x, lo=lo)
    if i:
        return a[i-1]
    raise ValueError


################# Forward looking features for prediction
def calculate_price_delta(df, window=100):
    '''
    Forward Looking
    Difference between price on order side now and opposite price at curr_timestamp + window in the future.
    If curr_timestamp + window is greater than end of day, calculate price_delta to last bid/ask of the day
    '''
    N = len(df)
    t_vec = df['timestamp'].values
    bid_vec = df['bp0'].values
    ask_vec = df['ap0'].values
    bidqty_vec = df['bq0'].values
    askqty_vec = df['aq0'].values
    side_vec = df['side'].values
    result_vec = np.zeros(len(df), dtype=np.float64)
    last_idx = t_vec[-1]
    last_bid = np.where(df['side'] == 1)[-1][-1]
    last_ask = np.where(df['side'] == 0)[-1][-1]

    for i in range(N):
        if bidqty_vec[i] == 0 or askqty_vec[i] == 0:
            continue
        endtm = (t_vec[i] + window)
        side1 = side_vec[i]
        opx = bid_vec[i] if side1 == 1 else ask_vec[i]

        search_rng = find_le(t_vec, endtm, i)
        idx2 = index(t_vec, search_rng, i)
        for j in range(idx2, N):
            side2 = side_vec[j]
            result = np.nan

            if t_vec[j] > endtm and side1 != side2:
                opx2 = ask_vec[i] if side1 == 1 else bid_vec[i]
                result = (opx2 - opx)
                break

            if endtm > last_idx and side1 != side2:
                opx2 = ask_vec[last_ask] if side1 == 1 else bid_vec[last_bid]
                result = (opx2 - opx)
                break

        result_vec[i] = result

    df[f'target_px_delta{window}'] = result_vec
    # fill nans with zero
    df[f'target_px_delta{window}'] = df[f'target_px_delta{window}'].fillna(0)
    return df


# testing
if __name__ == '__main__':
    df = pd.read_csv(f"output_20190614.csv")

    window = 100
    df = calculate_price_delta(df, window=window)

    print(f'\nsum px_delta{window}:', df[f'px_delta{window}'].sum())
    print(df[f'px_delta{window}'].describe())
    df[['timestamp', f'px_delta{window}']].set_index('timestamp').plot(figsize=(12,5))

