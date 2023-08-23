import dataclasses
import gzip
import logging
import os
import time
from typing import List, Callable

import s3fs
import sentry_sdk
from sqlalchemy import create_engine, text
import pandas as pd
from dateutil import parser

logging.basicConfig(
    format='%(asctime)s %(levelname)-5s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)

IS_DEV = os.environ.get('ENV') == 'dev'

if not IS_DEV and os.environ.get('SENTRY_DSN'):
    sentry_sdk.init(os.environ['SENTRY_DSN'])
USER = os.environ['DB_USER']
PASSWORD = os.environ['DB_PASSWORD']
HOST = 'qdb' if IS_DEV else 'localhost'
PORT = int(os.environ['DB_PORT'])
DB_URI = f'postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/qdb'
BUCKET = 'qdb-backups'
CACHE_PATH = 'cache'

_CONNECTION = None

def retry_call(call: Callable, attempts: int = 5, wait: float = 1):
    sleep = 0
    for attempt in range(attempts):
        try:
            return call()
        except Exception as e:
            if attempt == attempts - 1:
                raise

            sleep += wait

            logging.warning(f"Call {call} raised {type(e)}: {e}. Retry in {sleep}...")
            time.sleep(sleep)


engine = retry_call(lambda: create_engine(DB_URI))


def connection():
    global _CONNECTION
    if not _CONNECTION or _CONNECTION.closed:
        _CONNECTION = retry_call(engine.connect)

    return _CONNECTION


@dataclasses.dataclass
class TableData:
    partitions_to_leave: int
    columns: List[str]


TABLES_DATA = {
    'orderbook': TableData(24, ['timestamp', 'ts_nanos', 'is_bid', 'is_flush', 'is_reset', 'price', 'qty', 'exchange_timestamp']),
    'trades': TableData(7 * 24, ['timestamp', 'ts_nanos', 'price', 'quantity', 'exchange_timestamp', 'is_market_buy']),
    'price_tickers': TableData(7, ['timestamp', 'ts_nanos', 'bid', 'bid_amount', 'ask', 'ask_amount']),
}


def get_data(table, instrument, partition, cols) -> pd.DataFrame:
    columns = ', '.join(cols)
    sql = text(f"""
    SELECT 
        {columns}
    FROM :table 
    WHERE instrument = :instrument AND timestamp IN :partition
    """)
    return retry_call(
        lambda: pd.read_sql(
            sql,
            connection(),
            params={
                'partition': partition,
                'instrument': instrument,
                'table': table
            }
        )
    )


def get_partitions(table) -> pd.DataFrame:
    sql = text("""
        SHOW PARTITIONS FROM :table;
        """)
    return retry_call(lambda: pd.read_sql(sql, connection(), params={'table': table}))


def get_partition_instruments(table, partition) -> pd.DataFrame:
    sql = text(f"""
        SELECT 
            DISTINCT instrument
        FROM :table 
        WHERE timestamp IN :partition
        """)
    return retry_call(lambda: pd.read_sql(sql, connection(), params={'partition': partition, 'table': table}))


def export_data(table, partition, instrument, data, lock_path):
    flush_cache(table, partition, instrument)

    if 'timestamp' in data.columns:
        data.drop('timestamp', inplace=True, axis=1)

    if 'ts_nanos' in data.columns:
        data.rename(columns={'ts_nanos': 'timestamp'}, inplace=True)

    path = get_cache_path(table, partition, instrument)
    add_headers = not os.path.exists(path)
    with gzip.open(path, 'a') as file:
        data.to_csv(file, index=False, header=add_headers)
    os.makedirs(lock_path, exist_ok=True)
    logging.info(f'Stored {partition} to {path}')


def get_instrument_cache_path(table, instrument):
    return os.path.join(CACHE_PATH, table, instrument)


def get_cache_path(table, partition, instrument):
    return os.path.join(get_instrument_cache_path(table, instrument), f'{str(parser.parse(partition).date())}.csv.gz')


def get_partition_lock_path(table, partition, instrument):
    return os.path.join(CACHE_PATH, 'locks', table, partition, instrument)


def flush_cache(table, current_partition, instrument):
    fs = s3fs.S3FileSystem(profile='3jane') if IS_DEV else s3fs.S3FileSystem()

    current_date = parser.parse(current_partition).date()
    instrument_dir = get_instrument_cache_path(table, instrument)
    if not os.path.exists(instrument_dir):
        os.makedirs(instrument_dir, exist_ok=True)
        return

    for partition_raw in os.listdir(instrument_dir):
        partition = partition_raw.replace('.csv.gz', '')
        date = parser.parse(partition).date()
        if date < current_date:
            path = os.path.join(instrument_dir, partition_raw)
            s3_path = get_path(table, partition, instrument)
            t = time.time()
            retry_call(lambda: fs.upload(path, s3_path))
            os.remove(path)
            logging.info(f'Exported {s3_path} in {time.time() - t}')


def get_path(table, partition, instrument):
    exchange, market_type, symbol = instrument.split('__')
    date = partition
    year, month, day = date.split('-')
    if 'T' in day:
        day = day.split('T')[0]

    return f's3://{BUCKET}/{table}/{exchange}/{market_type}/{symbol}/{year}/{month}/{day}/{date}.csv.gz'


def drop_partition(table, partition):
    retry_call(
        lambda: connection().execute(
            text("ALTER TABLE :table DROP PARTITION LIST :partition"),
            parameters={'table': table, 'partition': partition}
        )
    )
    logging.info(f"Partition dropped {table}:{partition}")


if __name__ == '__main__':
    while True:
        for table in TABLES_DATA:
            partitions = get_partitions(table)[:-TABLES_DATA[table].partitions_to_leave]
            for partition in partitions.name.values:
                instruments = get_partition_instruments(table, partition)
                for i_instr, instrument in enumerate(instruments.instrument.values):
                    logging.info(f'Process {table} {partition} {instrument} ({i_instr + 1} / {len(instruments)})')

                    lock_path = get_partition_lock_path(table, partition, instrument)
                    if os.path.exists(lock_path):
                        logging.info(f'Data already appended {lock_path}')
                        continue

                    t = time.time()
                    data = get_data(table, instrument, partition, TABLES_DATA[table].columns)
                    logging.info(f'Queried {table} {partition} {instrument} in {time.time() - t}')
                    export_data(table, partition, instrument, data, lock_path)
                    del data
                drop_partition(table, partition)
        logging.info('DONE')
        time.sleep(60*60)
