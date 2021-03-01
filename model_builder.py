import pandas as pd
import numpy as np

import feature_list
import statsmodels.api as sm
from scipy import stats
from patsy import ModelDesc
from patsy import highlevel
from sklearn import linear_model
from sklearn.linear_model import Lasso, lasso_path
import matplotlib.pyplot as plt

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
            df_temp = self.calculate_features(df_temp)
            dfs.append(df_temp)

        if len(dfs) == 0:
            print(f'no training data for {date}')
            return

        df_trn = pd.concat(dfs)
        feature_cols = [c for c in df_trn.columns if 'feature' in c]
        target_col = [c for c in df_trn.columns if 'target' in c][-1]
        print(f"Formula: {target_col} ~ {' + '.join(feature_cols)}\n")

       # clean data - remove inf/nan values from training
        df_trn.replace([np.inf, -np.inf], np.nan, inplace=True)
        df_trn = df_trn[['date', 'ones', target_col] + feature_cols].dropna()

        df_train_info = df_trn.groupby('date')['ones'].sum().reset_index()
        df_train_info.rename(columns={'ones': 'train_count'}, inplace=True)
        print(df_train_info)
        print('\n')

        # train model
        X = df_trn[feature_cols]
        y = df_trn[target_col]
        model = Lasso(alpha=1.0,
                      fit_intercept=True,
                      normalize=False,
                      max_iter=1000,
                      positive=False,
                      random_state=42)
        model.fit(X, y)

        coef_df = pd.concat([pd.DataFrame(X.columns), pd.DataFrame(np.transpose(model.coef_))], axis=1, ignore_index=True)
        coef_df.rename(columns={coef_df.columns[0]: 'feature', coef_df.columns[1]: 'coefficient'}, inplace=True)
        coef_df = coef_df[coef_df['coefficient'] != 0.]
        coef_dict = dict(zip(coef_df['feature'], coef_df['coefficient']))
        intercept = model.intercept_

        print(f'total features: {X.shape[1]}')
        print(f'selected features: {coef_dict.keys()}\n')
        print(coef_df)
        # score model manually assuming no interactions and no categorical features
        df['predicted'] = 0
        for feature, coefficient in coef_dict.items():
            df['predicted'] += df[feature] * coefficient

        df['predicted'] = df['predicted'] + intercept


        return df

    def run(self, date):
        df = self._get_input_data(date)
        if df is None:
            return

        # calculate_features
        df = self.calculate_features(df)

        # build lasso regression
        df = self.build_regression_model(df, date, num_train_dates=1)
        return df


if __name__ == '__main__':
    dmb = DataModelBuilder()
    date = '20190611'
    df = dmb.run(date=date)

    df.predicted.plot(figsize=(12,5), title=f'Predictions for {date}')
    plt.show()

    target_sum = df['target_px_delta100'].sum()
    target_sum_on_pos_predictions = df[df.predicted > 0]['target_px_delta100'].sum()
    pct_improvement = round(((target_sum_on_pos_predictions - target_sum) / abs(target_sum)), 2) * 100

    print(f'Lasso model outperforms by {pct_improvement}%')
