import pandas as pd
import numpy as np

import feature_list
import statsmodels.apy as sm

class DataModelBuilder():
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.available_dates_list = ['20190610', '20190611', '20190612', '20190613', '20190614']

    def _get_input_data(self, date):
        df = pd.read_csv(f"C:/Users/Andrew/Documents/Python Scripts/order_book/data/output_{date}.csv")
        if df is None:
            print(f'Error: No data for {date}')
            return

        # add some extra columns
        df['date'] = date
        df['ones'] = 1
        return df

    def calculate_features(self, df):
        df = feature_list.calculate_rolling_oside(df, window=100)
        df = feature_list.calculate_qty_ratio(df, levels=1)
        df = feature_list.calculate_inside_spread(df)

        # calculate prediction target
        df = feature_list.calculate_price_delta(df, window=100)
        return df

    def build_regression_model(self, df, date, num_train_dates=1):
        train_dates = [d for d in self.available_dates_list if d < date][-num_train_dates:]
        dfs = []
        for dt in train_dates:
            df_temp = self._get_input_data(dt)
            if df_temp is None:
                continue
            dfs.append(df_temp)

        if len(dfs) == 0:
            print(f'no training data for {date}')
            return

        df = pd.concat(dfs)
        df_train_info = df.groupby('date')['ones'].sum().reset_index()
        print(df_train_info)


        return df

    def run(self, date):
        df = self._get_input_data(date)
        if df is None:
            return



        # calculate_features
        df = self.calculate_features(df)

        # build lasso regression

        return df


if __name__ == '__main__':
    dmb = DataModelBuilder()
    date = '20190614'
    df = dmb.run(date=date)