import os
import time
import logging
from enum import Enum
from typing import Optional
from urllib3.util.retry import Retry

import requests
import pandas as pd
from requests.adapters import HTTPAdapter

logger = logging.getLogger("rcdb_datastore")
retries = Retry(total=5, backoff_factor=0.2, status_forcelist=[502, 503, 504], raise_on_status=False)


class DataException(Exception):
    pass


class DataType(Enum):
    ohlcv = 'ohlcv'
    kalman = 'kalman'
    bot_performance = 'bot_performance'
    price_index = 'price_index'
    account_trades = 'account_trades'
    rebates = 'rebates'
    report = 'report'
    bid_ask = 'bid_ask'
    balance = 'balance'
    transfers = 'transfers'
    bswap_quote = 'bswap_quote'
    orderbook = 'orderbook'
    kalman_log = 'kalman_log'


class DataStore:
    data_type = DataType

    def __init__(self, api_url, token, cache_path=None):
        self.api_url = api_url
        self.session = requests.Session()
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.headers.update({'Authorization': f'Bearer {token}'})
        self.cache_path = cache_path

    @staticmethod
    def __get_data_type(df: pd.DataFrame) -> Optional[DataType]:
        cols = set(df.columns)
        if "high" in cols:
            return DataType.ohlcv
        if "s1_x" in cols:
            return DataType.kalman
        if "balance_base" in cols:
            return DataType.bot_performance
        if "trades_count_buy" in cols:
            return DataType.account_trades
        if {"timestamp", "timestamp_received", "account_type", "symbol", "rebate", "name", "rebate_usd"} == cols:
            return DataType.rebates
        if "bid" in cols and "ask" in cols:
            return DataType.bid_ask
        if "amount_usd" in cols and "interest_usd" in cols:
            return DataType.balance
        if {"timestamp", "symbol", "name", "transfer_type", "amount", "amount_usd", "is_sub_account_transfer"} == cols:
            return DataType.transfers
        if {"timestamp", "symbol", "price", "slippage", "fee"} == cols:
            return DataType.bswap_quote
        if {"timestamp", "ts_l", "channel", "b", "a", "b_a", "a_a"} == cols:
            return DataType.orderbook
        if {"timestamp", "channel", "art", "brt"} == cols:
            return DataType.kalman_log
        return None

    def __send_data(self, data_type: DataType, rows):
        logger.debug(f"sending {len(rows)} rows to `{data_type}`")
        r = self.session.post(
            f"{self.api_url}/log/",
            json=rows,
            params={"type": data_type.value},
            timeout=100
        )
        if r.status_code != 200:
            raise requests.exceptions.RequestException(
                f'Send data error {r.status_code} type: {data_type.value} {r.text}'
            )

    def __get_data(self, data_type, query) -> Optional[pd.DataFrame]:
        logger.debug(f"loading `{data_type}` with query={query}")
        query = {
            k: (v.upper() if k in {'exchange', 'symbol', 'instrument'} else v)
            for k, v in query.items()
        }
        if data_type == DataType.report:
            r = self.session.post(
                f"{self.api_url}/report/",
                json=query,
                timeout=300
            )
        else:
            r = self.session.get(
                f"{self.api_url}/latest/",
                params={**query, "type": data_type.value},
                timeout=100
            )
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 404:
            return None
        else:
            raise DataException(r.text)

    def append(self, df: pd.DataFrame):
        data_type = self.__get_data_type(df)

        if not data_type:
            raise ValueError(f'Unsupported data_type of {df}')

        rows = df.to_dict(orient="records")
        self.__send_data(data_type, rows)

    def read(self, data_type: DataType, query_params):
        rows = self.__get_data(data_type, query_params)
        if rows is not None:
            df = pd.DataFrame(rows)
        else:
            df = pd.DataFrame()

        if df.shape[0] > 0:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index("timestamp")
        return df

    def get_data(
        self,
        data_type: DataType,
        start: str,
        end: str,
        params=None,
        force_reload=False,
        verbose=True,
        sleep=0.5,
        tail=100_000
    ):
        if self.cache_path is None:
            raise Exception('Provide cache_path')

        params = params or {}

        def _get_data_ohlcv(params):
            params = {**params, 'tail': tail}

            cache_dir = os.path.join(self.cache_path, 'market_data')
            os.makedirs(cache_dir, exist_ok=True)
            cache_path = os.path.join(
                cache_dir,
                f'{params["exchange"]}__{params["symbol"]}__{params["instrument"]}.hdf'.replace('/', '_').lower()
            )

            if not os.path.exists(cache_path) or force_reload:
                res_df = None
                latest_date = None
                if verbose:
                    print('No cache', cache_path)
            else:
                res_df = pd.read_hdf(cache_path, key='table')
                latest_date = res_df.index.max()
                if verbose:
                    print('Cache exists', cache_path, 'latest_date', latest_date)

            while True:
                df = self.read(DataType.ohlcv, params)

                if latest_date:
                    df = df[df.index > latest_date]

                if df.empty:
                    res_df.sort_index(ascending=False, inplace=True)
                    res_df.to_hdf(cache_path, key='table', mode='w')
                    if len(res_df):
                        res_df = res_df.drop('account_type', 1)
                    return res_df

                if res_df is None:
                    res_df = df
                else:
                    res_df = pd.concat([res_df, df])

                params['date_end'] = df.index.min().isoformat()
                if verbose:
                    print(params)
                time.sleep(sleep)

        def _get_bidask_swap(p, date_start, date_end, cache_path):
            if os.path.exists(cache_path) and not force_reload:
                if verbose:
                    print('cache hit', cache_path)
                return pd.read_hdf(cache_path, key='table')

            res_df = pd.DataFrame([])
            while True:
                df = self.read(data_type, {**p, 'tail': tail, 'date_start': date_start, 'date_end': date_end})
                df = df[df.index > start]

                res_df = pd.concat([res_df, df])

                if len(df) < tail:
                    res_df.sort_index(ascending=False, inplace=True)
                    res_df.to_hdf(cache_path, key='table')
                    return res_df

                date_end = df.index.min().isoformat()
                if verbose:
                    print('loading...', params, 'from', date_start, 'to', date_end, len(df), len(res_df))
                time.sleep(sleep)

        if data_type == DataType.bid_ask:
            cache_dir = os.path.join(self.cache_path, 'spreads')
            os.makedirs(cache_dir, exist_ok=True)
            cache_path = os.path.join(
                cache_dir,
                (
                    f'{params["exchange"]}_{params["symbol"]}_{params["account_type"]}_{start}_{end}.hdf'
                ).replace('/', '_').lower()
            )
            return _get_bidask_swap(params, start, end, cache_path)
        elif data_type == DataType.bswap_quote:
            cache_dir = os.path.join(self.cache_path, 'bswap')
            os.makedirs(cache_dir, exist_ok=True)
            cache_path = os.path.join(cache_dir, f'{params["symbol"]}_{start}_{end}.hdf'.replace('/', '_').lower())
            return _get_bidask_swap({'symbol': params['symbol']}, start, end, cache_path)
        elif data_type == DataType.ohlcv:
            df = _get_data_ohlcv(params)
            return df[(df.index < end) & (df.index >= start)]
        elif data_type == DataType.kalman_log:
            cache_dir = os.path.join(self.cache_path, 'kalman_log_zmq')
            os.makedirs(cache_dir, exist_ok=True)
            cache_path = os.path.join(cache_dir, f'{params["channel"]}_{start}_{end}.hdf'.replace('/', '_').lower())
            return _get_bidask_swap({'channel': params['channel']}, start, end, cache_path)
        elif data_type == DataType.orderbook:
            cache_dir = os.path.join(self.cache_path, 'orderbook_zmq')
            os.makedirs(cache_dir, exist_ok=True)
            cache_path = os.path.join(cache_dir, f'{params["channel"]}_{start}_{end}.hdf'.replace('/', '_').lower())
            return _get_bidask_swap({'channel': params['channel']}, start, end, cache_path)
        else:
            raise ValueError(f'Unsupported type {data_type}')
