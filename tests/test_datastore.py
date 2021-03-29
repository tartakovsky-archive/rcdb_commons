import re
import datetime

import pytest
import requests
import pandas as pd

from data_store import DataStore, DataType, DataException


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

    assert 'Send data error 400 err req body' in str(exc)
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
