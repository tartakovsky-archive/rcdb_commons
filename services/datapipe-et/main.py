import asyncio
import json
import logging
import shutil
import time
import os

import requests
import sentry_sdk
from datetime import datetime, timedelta

import pandas as pd
from questdb.ingress import Sender

SENTRY_DSN = os.environ.get('SENTRY_DSN')
QUESTDB_HOST = os.environ['QUESTDB_HOST']
QUESTDB_PORT = int(os.environ['QUESTDB_PORT'])
DASHBOARD_TOKEN = os.environ['DASHBOARD_TOKEN']

if SENTRY_DSN:
    sentry_sdk.init(SENTRY_DSN)

logging.basicConfig(
    format='%(asctime)s %(levelname)-5s %(message)s',
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.Formatter.converter = time.gmtime

BASE_DIR = os.path.dirname(__file__)


def read_accounts_data(data_dir) -> pd.DataFrame:
    if os.path.exists(data_dir):
        dfs = []
        for account_name in os.listdir(data_dir):
            account_path = os.path.join(data_dir, account_name)
            for pair_gz in os.listdir(account_path):
                df = pd.read_csv(os.path.join(account_path, pair_gz))
                df['account_name'] = account_name
                dfs.append(df)
        if dfs:
            df = pd.concat(dfs)
            if 'Unnamed: 0' in df.columns:
                df.drop('Unnamed: 0', axis=1, inplace=True)

            df.rename(columns={'ts': 'timestamp', 'dt': 'ts'}, inplace=True)
            return df
    return pd.DataFrame([])


def read_swap_trades(base_dir, *args) -> pd.DataFrame:
    return read_accounts_data(os.path.join(base_dir, 'swap_trades'))


def read_spot_trades(base_dir, *args) -> pd.DataFrame:
    return read_accounts_data(os.path.join(base_dir, 'spot_trades'))


def read_spot_klines(base_dir, *args) -> pd.DataFrame:
    df = read_accounts_data(os.path.join(base_dir, 'spot_klines'))
    df.rename(columns={'dt_open': 'ts'}, inplace=True)
    return df


def read_quote_prices(base_dir, dt) -> pd.DataFrame:
    path = os.path.join(base_dir, 'aux', 'quote_prices.json')
    df = pd.DataFrame([{'asset': k, 'price': v} for k, v in json.load(open(path)).items()])
    df['ts'] = dt
    return df


def read_spot_fees(base_dir, dt) -> pd.DataFrame:
    df = pd.read_csv(os.path.join(base_dir, 'aux', 'spot_fees.csv'))
    df.rename(columns={'index': 'pair'}, inplace=True)
    df['ts'] = dt
    return df


def read_swap_fees(base_dir, dt) -> pd.DataFrame:
    df = pd.read_csv(os.path.join(base_dir, 'aux', 'swap_fees.csv'))
    df.rename(columns={'Unnamed: 0': 'pair'}, inplace=True)
    df['ts'] = dt
    return df


def read_swap_rewards(base_dir, *args) -> pd.DataFrame:
    df = pd.read_csv(os.path.join(base_dir, 'aux', 'swap_rewards.csv'))
    df.drop('Unnamed: 0', inplace=True, axis=1)
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    return df


def read_trades(base_dir, *args):
    return pd.concat(
        [
            read_spot_trades(base_dir),
            read_swap_trades(base_dir)
        ]
    )


def read_fees(base_dir, dt):
    return pd.concat(
        [
            read_swap_fees(base_dir, dt),
            read_spot_fees(base_dir, dt)
        ]
    )


tables_conf = {
    'et_trades': {
        'categorical': ['exchange', 'account_type', 'symbol', 'base', 'quote', 'side', 'order_type', 'spent_asset',
                        'received_asset', 'account_name', 'fee_asset'],
        'func': read_trades
    },
    'et_klines': {
        'categorical': ['exchange', 'account_type', 'symbol', 'base', 'quote', 'interval', 'account_name'],
        'func': read_spot_klines
    },
    'et_quote_prices': {
        'categorical': ['asset'],
        'func': read_quote_prices
    },
    'et_fees': {
        'categorical': ['pair', 'exchange', 'account_type', 'symbol', 'base', 'quote'],
        'func': read_fees
    },
    'et_swap_rewards': {
        'categorical': ['exchange', 'account_type', 'symbol', 'base', 'quote'],
        'func': read_swap_rewards
    }
}

def str_to_dt(s):
    return datetime.strptime(s, "%Y-%m-%d, %H:%M")


def dt_to_str(dt: datetime):
    return dt.strftime("%Y-%m-%d, %H:%M")

def load_acc_map() -> dict:
    r = requests.get('https://dash.3jane.com/api/exchange-credentials', headers={'Authorization': f'Bearer {DASHBOARD_TOKEN}'})
    r.raise_for_status()
    accounts = r.json()

    res = {}

    for cred in accounts:
        name = cred['name'].replace('@3jane.com', '')
        if 'markets' in (cred['meta'] or {}) and cred['account_type'] == 'SPOT':
            res[name] = []
            for market in cred['meta']['markets']:
                base, quote = market.split('/')
                res[name].append(
                    {
                        'account_name': name,
                        'base': base,
                        'quote': quote
                    }
                )
    return res


def gen_data():
    from src.data_loader import backup_inputs, load_aux_files, load_dataset
    from src.data_loader import DatasetDirStructure, ReportDirStructure

    json.dump(load_acc_map(), open('./inputs/accounts_to_deploy.json', 'w+'))

    ds_dirs = DatasetDirStructure(
        acc_map_file='accounts_to_deploy.json'
    )

    backup_inputs(ds_dirs)

    async def _main():
        await load_aux_files(ds_dirs)
        await load_dataset(ds_dirs)

    asyncio.run(_main())


def export_data_params(params):
    logging.info(f'Report parameters: {params}')
    base_dir = os.path.join(BASE_DIR, 'data', f"{params['start']} – {params['end']}")
    report_start_dt = str_to_dt(params['start'])
    report_end_dt = str_to_dt(params['end'])

    with Sender(QUESTDB_HOST, QUESTDB_PORT) as sender:
        for table_name, conf in tables_conf.items():
            logging.info(f'Start exporting {table_name}')
            df = conf['func'](base_dir, report_start_dt)
            if df.empty:
                logging.info(f'Data is empty at {table_name}')
                continue

            if 'account_name' in df:
                df['account_name'] = df['account_name'] + '@3jane.com'

            df['ts'] = pd.to_datetime(df['ts'])
            df = df[(df.ts >= report_start_dt) & (df.ts < report_end_dt)]

            if df.empty:
                logging.info(f'Data is empty at {table_name} after filter')
                continue

            if 'timestamp' in df.columns:
                df.rename(columns={'timestamp': '_timestamp'}, inplace=True)

            symb_trans_cols = {'base', 'quote', 'symbol'}
            if symb_trans_cols & set(df.columns) == symb_trans_cols:
                df['symbol'] = df['base'] + '/' + df['quote']

            for col_name in conf['categorical']:
                df[col_name] = pd.Categorical(df[col_name])

            df.sort_values('ts', inplace=True)
            t = time.time()
            sender.dataframe(df, table_name=table_name, at='ts')
            sender.flush()
            logging.info(f'Exported {table_name} rows: {len(df)} {df.ts.min()} {df.ts.max()} in {time.time() - t}')


def generate_parameters(start, end):
    return {
        "start": start,
        "end": end,
        "maker_rebate": -0.4e-4,
        "bnb_discount_coef": 0.75
    }


if __name__ == '__main__':
    INTERVAL = timedelta(minutes=3)
    script_start = time.time()

    shots = 10

    dirs = [x for x in os.listdir(os.path.join(BASE_DIR, 'data')) if not x.startswith('.')]
    if dirs:
        start = sorted(dirs, reverse=True)[0].split(' – ')[-1]
        start = str_to_dt(start)
        now = datetime.utcnow()
        start = start.replace(tzinfo=now.tzinfo)
    else:
        start = datetime.utcnow()
        start = start.replace(year=2023, month=3, day=1, hour=0, minute=0, second=0, microsecond=0)

    end = start + INTERVAL
    logging.info(f"Initial range: {start} {end}")

    while shots != 0:
        gap = datetime.utcnow() - start
        logging.info(f"Gap {gap}")

        if gap < INTERVAL:
            time.sleep(60)
            logging.info(f'Wait end interval {end}')
            continue

        if gap < timedelta(days=1):
            end = start + timedelta(minutes=int(gap.total_seconds() / 60.))
        else:
            end = start + timedelta(days=1)

        end -= timedelta(minutes=1)

        logging.info(f"Process {start} {end}")
        start_str = dt_to_str(start)
        end_str = dt_to_str(end)

        params = generate_parameters(start_str, end_str)
        json.dump(
            params,
            open(os.path.join(BASE_DIR, 'inputs', 'params.json'), 'w+')
        )
        try:
            gen_data()
        except Exception as e:
            logging.exception(f"Error during gen_data() of {params}")
            base_dir = os.path.join(BASE_DIR, 'data', f"{params['start']} – {params['end']}")
            if os.path.exists(base_dir):
                shutil.rmtree(base_dir)
            time.sleep(30)
            continue

        export_data_params(params)
        start = end
        end = start + INTERVAL
        time.sleep(60)
        shots -= 1

    logging.info("End script")
