import re
import datetime

import pytest
import requests
import pandas as pd

from lib.stores import DataStore, DataType, DataException


API_URL = 'http://some.url'
TOKEN = 'token'
DATASTORE = DataStore(api_url=API_URL, token=TOKEN)


def test_init():
    assert DATASTORE.api_url == API_URL
    assert DATASTORE.session.headers['Authorization'] == f'Bearer {TOKEN}'


@pytest.mark.parametrize(
    'df, data_type',
    [
        (pd.DataFrame([{'high': 1}]), DataType.ohlcv),
        (pd.DataFrame([{'s1_x': 1}]), DataType.kalman),
        (pd.DataFrame([{'balance_base': 1}]), DataType.bot_performance),
        (pd.DataFrame([{'trades_count_buy': 1}]), DataType.account_trades),
        # (pd.DataFrame([{'report': 1}]), DataType.report),
        (pd.DataFrame([{"timestamp": 1, "timestamp_received": 1,
                        "account_type": 1, "symbol": 1, "rebate": 1, "name": 1, "rebate_usd": 1}]),
         DataType.rebates),
        (
            pd.DataFrame([
                {"timestamp": 1, "symbol": 1, "name": 1,
                 "transfer_type": 1, "amount": 1, "amount_usd": 1, "is_sub_account_transfer": 1}]),
            DataType.transfers
        ),
        (pd.DataFrame([{'bid': 1, 'ask': 1}]), DataType.bid_ask),
        (pd.DataFrame([{'interest_usd': 1, 'amount_usd': 1}]), DataType.balance),
        (pd.DataFrame([{"timestamp": 1, "symbol": 1, "price": 1, "slippage": 1, "fee": 1}]), DataType.bswap_quote),
        (pd.DataFrame([{"timestamp": 1, "channel": 1, "ts_l": 1, "b": 1, "a": 1, "b_a": 1, "a_a": 1}]),
         DataType.orderbook),
        (pd.DataFrame([{"timestamp": 1, "channel": 1, "art": 1, "brt": 1}]), DataType.kalman_log),
        (pd.DataFrame([{"timestamp": 1, "channel": 1, "p": 1, "q": 1, "bm": 1}]), DataType.tickers),
        (pd.DataFrame([{'some': 1}]), None),
    ]
)
def test_get_data_type(df, data_type):
    assert DataStore._DataStore__get_data_type(df) is data_type


def test_append_unsupported_type():
    with pytest.raises(ValueError) as ex:
        DATASTORE.append(pd.DataFrame([]))

    assert 'Unsupported data_type of ' in str(ex)


def test_append_error_at_server(requests_mock):
    m = requests_mock.post(re.compile(f'{API_URL}/log'), status_code=400, text='err req body')

    with pytest.raises(requests.exceptions.RequestException) as exc:
        DATASTORE.append(pd.DataFrame([{'high': 1}]))

    assert exc.match('Send data error 400 type: ohlcv err req body')
    assert m.called


def test_append(requests_mock):
    df = pd.DataFrame([{'high': 1}])
    m = requests_mock.post(re.compile(f'{API_URL}/log'), status_code=200)
    DATASTORE.append(df)

    r_history = m.request_history[0]
    assert r_history.url == f'{API_URL}/log/?type=ohlcv'
    assert tuple(r_history.json()) == tuple([{'high': 1}])


def test_read(requests_mock):
    dt = datetime.datetime.utcnow()
    df = pd.DataFrame([{'high': 1, 'timestamp': dt.isoformat()}])
    m = requests_mock.get(re.compile(f'{API_URL}/latest'), status_code=200, json=df.to_dict(orient='records'))

    params = {'exchange': 'binance', 'symbol': 'btc/usdt', 'instrument': 'spot'}
    res_data = DATASTORE.read(DataType.ohlcv, params)

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')
    assert res_data.equals(df)
    assert m.request_history[0].url == \
           f'{API_URL}/latest/?exchange=BINANCE&symbol=BTC%2FUSDT&instrument=SPOT&type=ohlcv'


def test_read_data_error(requests_mock):
    error = 'some error'
    m = requests_mock.get(re.compile(f'{API_URL}/latest'), status_code=400, text=error)
    with pytest.raises(DataException) as exc:
        DATASTORE.read(DataType.kalman, {})

    assert error in str(exc)
    assert m.called


def test_read_data_empty(requests_mock):
    m = requests_mock.get(re.compile(f'{API_URL}/latest'), status_code=404)
    df = DATASTORE.read(DataType.kalman, {})

    assert m.called
    assert df.empty
