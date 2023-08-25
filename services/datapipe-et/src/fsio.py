import json
import pathlib

import pandas as pd
from datetime import datetime as dt
from dateutil.parser import parse


class InputReader:
    def __init__(self,
                 input_dir: str = './inputs',
                 input_backup_dir: str = None,
                 creds_file: str = 'credentials.json',
                 proxies_file: str = 'proxies.csv',
                 acc_map_file: str = 'acc_map.json',
                 params_file: str = 'params.json',
                 *args, **kwargs):
        self.input_dir = input_dir
        self.input_backup_dir = input_backup_dir
        self.creds_file = creds_file
        self.proxies_file = proxies_file
        self.acc_map_file = acc_map_file
        self.params_file = params_file


class DatasetDirStructure(InputReader):
    def __init__(self,
                 dataset_name: str = None,
                 output_dir: str = './data',
                 *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.dataset_name = dataset_name
        self.output_dir = output_dir

        if self.dataset_name is None:
            def date_to_name(d):
                return parse(d).strftime('%Y-%m-%d, %H:%M')

            params = read_global_params(self)
            self.dataset_name = f"{date_to_name(params['start'])} – {date_to_name(params['end'])}"

        self.dataset_dir = f"{self.output_dir}/{self.dataset_name}"
        self.input_backup_dir = f"{self.dataset_dir}/inputs"

        self.ds_aux_dir = f"{self.dataset_dir}/aux"
        self.ds_data_spot_klines_dir = f"{self.dataset_dir}/spot_klines"
        self.ds_data_spot_trades_dir = f"{self.dataset_dir}/spot_trades"
        self.ds_data_swap_trades_dir = f"{self.dataset_dir}/swap_trades"

        for d in [self.input_backup_dir, self.ds_aux_dir]:
            pathlib.Path(d).mkdir(parents=True, exist_ok=True)


class ReportDirStructure(InputReader):
    def __init__(self,
                 dataset_dirs: DatasetDirStructure,
                 report_name: str = 'default',
                 output_dir: str = './reports',
                 *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.dataset_dirs = dataset_dirs
        self.report_name = report_name
        self.output_dir = output_dir

        self.report_dir = f"{self.output_dir}/{dataset_dirs.dataset_name}/{self.report_name}"

        self.input_backup_dir = f"{self.report_dir}/inputs"
        self.rp_per_bot_dir = f"{self.report_dir}/per_bot"
        self.rp_plots_dir = f"{self.report_dir}/plots"

        for d in [self.input_backup_dir, self.rp_per_bot_dir, self.rp_plots_dir]:
            pathlib.Path(d).mkdir(parents=True, exist_ok=True)


# global inputs read

def read_global_creds(dirs: InputReader):
    return json.load(open(f"{dirs.input_dir}/{dirs.creds_file}"))


def read_global_params(dirs: InputReader):
    return json.load(open(f"{dirs.input_dir}/{dirs.params_file}"))


def read_global_acc_map(dirs: InputReader):
    return json.load(open(f"{dirs.input_dir}/{dirs.acc_map_file}"))


def read_global_proxies(dirs: InputReader):
    return list(pd.read_csv(f"{dirs.input_dir}/{dirs.proxies_file}").iloc[:, 0].values)


# local inputs write

def write_local_creds(dirs: InputReader, data):
    json.dump(data, open(f"{dirs.input_backup_dir}/{dirs.creds_file}", "w"), indent=4)


def write_local_params(dirs: InputReader, data):
    json.dump(data, open(f"{dirs.input_backup_dir}/{dirs.params_file}", "w"), indent=4)


def write_local_acc_map(dirs: InputReader, data):
    json.dump(data, open(f"{dirs.input_backup_dir}/{dirs.acc_map_file}", "w"), indent=4)


def write_local_proxies(dirs: InputReader, data):
    pd.DataFrame(data, columns=['proxy']).to_csv(
        f"{dirs.input_backup_dir}/{dirs.proxies_file}",
        index=False
    )


# local inputs read

def read_local_creds(dirs: InputReader):
    return json.load(open(f"{dirs.input_backup_dir}/{dirs.creds_file}"))


def read_local_params(dirs: InputReader):
    return json.load(open(f"{dirs.input_backup_dir}/{dirs.params_file}"))


def read_local_acc_map(dirs: InputReader):
    return json.load(open(f"{dirs.input_backup_dir}/{dirs.acc_map_file}"))


def read_local_proxies(dirs: InputReader):
    return list(pd.read_csv(f"{dirs.input_backup_dir}/{dirs.proxies_file}").iloc[:, 0].values)


# dataset/aux files
def write_spot_fees(dirs: DatasetDirStructure, df, *args, **kwargs):
    df.to_csv(f"{dirs.ds_aux_dir}/spot_fees.csv")


def read_spot_fees(dirs: DatasetDirStructure, *args, **kwargs):
    return pd.read_csv(f"{dirs.ds_aux_dir}/spot_fees.csv", index_col=0)


def write_swap_fees(dirs: DatasetDirStructure, df, *args, **kwargs):
    df.to_csv(f"{dirs.ds_aux_dir}/swap_fees.csv")


def read_swap_fees(dirs: DatasetDirStructure, *args, **kwargs):
    return pd.read_csv(f"{dirs.ds_aux_dir}/swap_fees.csv", index_col=0)


def write_swap_rewards(dirs: DatasetDirStructure, df, *args, **kwargs):
    df.to_csv(f"{dirs.ds_aux_dir}/swap_rewards.csv")


def read_swap_rewards(dirs: DatasetDirStructure, *args, **kwargs):
    return pd.read_csv(f"{dirs.ds_aux_dir}/swap_rewards.csv", index_col=0)


def write_quote_prices(dirs: DatasetDirStructure, quote_prices, *args, **kwargs):
    json.dump(quote_prices, open(f"{dirs.ds_aux_dir}/quote_prices.json", "w"), indent=4)


def read_quote_prices(dirs: DatasetDirStructure, *args, **kwargs):
    return json.load(open(f"{dirs.ds_aux_dir}/quote_prices.json"))


def write_current_time(dirs: DatasetDirStructure, *args, **kwargs):
    time = dt.now().strftime('%Y-%m-%d, %H:%M:%S')
    json.dump({'time': time}, open(f"{dirs.ds_aux_dir}/time.json", "w"), indent=4)


# dataset/spot_klines files
def write_spot_klines(dirs: DatasetDirStructure, df, acc, base, quote, *args, **kwargs):
    folder = pathlib.Path(f"{dirs.ds_data_spot_klines_dir}/{acc}")
    folder.mkdir(parents=True, exist_ok=True)
    df.to_csv(f"{folder}/{base}_{quote}.csv.gz", compression='gzip')


def read_spot_klines(dirs: DatasetDirStructure, acc, base, quote, start=None, end=None, *args, **kwargs):
    try:
        df = pd.read_csv(
            f"{dirs.ds_data_spot_klines_dir}/{acc}/{base}_{quote}.csv.gz",
            compression='gzip',
            index_col=0
        )
        if start is not None and end is not None:
            return df[(df.index >= start) & (df.index < end)]

        return df
    except:
        return pd.DataFrame()


# dataset/spot_trades files
def write_spot_trades(dirs: DatasetDirStructure, df, acc, base, quote, *args, **kwargs):
    folder = pathlib.Path(f"{dirs.ds_data_spot_trades_dir}/{acc}")
    folder.mkdir(parents=True, exist_ok=True)
    df.to_csv(f"{folder}/{base}_{quote}.csv.gz", compression='gzip')


def read_spot_trades(dirs: DatasetDirStructure, acc, base, quote, start=None, end=None,
                     *args, **kwargs):
    try:
        df = pd.read_csv(
            f"{dirs.ds_data_spot_trades_dir}/{acc}/{base}_{quote}.csv.gz",
            compression='gzip',
            index_col=0
        )
        if start is not None and end is not None:
            return df[(df.index >= start) & (df.index < end)]

        return df
    except:
        return pd.DataFrame()


# dataset/swap_trades files
def write_swap_trades(dirs: DatasetDirStructure, df, acc, base, quote, *args, **kwargs):
    folder = pathlib.Path(f"{dirs.ds_data_swap_trades_dir}/{acc}")
    folder.mkdir(parents=True, exist_ok=True)
    df.to_csv(f"{folder}/{base}_{quote}.csv.gz", compression='gzip')


def read_swap_trades(dirs: DatasetDirStructure, acc, base, quote, start=None, end=None,
                     *args, **kwargs):
    try:
        df = pd.read_csv(
            f"{dirs.ds_data_swap_trades_dir}/{acc}/{base}_{quote}.csv.gz",
            compression='gzip',
            index_col=0
        )

        if start is not None and end is not None:
            return df[(df.index >= start) & (df.index < end)]

        return df
    except:
        return pd.DataFrame()


# reports/per_bot files
def write_bot_report(dirs: ReportDirStructure, df, acc, base, quote, *args, **kwargs):
    folder = pathlib.Path(f"{dirs.rp_per_bot_dir}/{acc}")
    folder.mkdir(parents=True, exist_ok=True)
    df.to_csv(f"{folder}/{base}_{quote}.csv.gz", compression='gzip')


def read_bot_report(dirs: ReportDirStructure, acc, base, quote, *args, **kwargs):
    try:
        return pd.read_csv(
            f"{dirs.rp_per_bot_dir}/{acc}/{base}_{quote}.csv.gz",
            compression='gzip',
            index_col=0
        )
    except:
        return pd.DataFrame()


# pivot by bot

def write_pivot_by_bot(dirs: ReportDirStructure, df, *args, **kwargs):
    df.to_csv(f"{dirs.report_dir}/pivot_by_bot.csv", float_format='%.2f')


def read_pivot_by_bot(dirs: ReportDirStructure, *args, **kwargs):
    try:
        return pd.read_csv(
            f"{dirs.report_dir}/pivot_by_bot.csv",
            index_col=0
        )
    except:
        return pd.DataFrame()


# pivot by pair

def write_pivot_by_pair(dirs: ReportDirStructure, df, *args, **kwargs):
    df.to_csv(f"{dirs.report_dir}/pivot_by_pair.csv", float_format='%.2f')


def read_pivot_by_pair(dirs: ReportDirStructure, *args, **kwargs):
    try:
        return pd.read_csv(
            f"{dirs.report_dir}/pivot_by_pair.csv",
            index_col=0
        )
    except:
        return pd.DataFrame()


# pivot by account

def write_pivot_by_account(dirs: ReportDirStructure, df, *args, **kwargs):
    df.to_csv(f"{dirs.report_dir}/pivot_by_account.csv", float_format='%.2f')


def read_pivot_by_account(dirs: ReportDirStructure, *args, **kwargs):
    try:
        return pd.read_csv(
            f"{dirs.report_dir}/pivot_by_account.csv",
            index_col=0
        )
    except:
        return pd.DataFrame()


# pivot metrics

def write_pivot_metrics(dirs: ReportDirStructure, data: dict, raw=False, *args, **kwargs):
    suffix = '_raw' if raw else ''
    json.dump(data, open(f"{dirs.report_dir}/pivot_metrics{suffix}.json", "w"), indent=4)


def read_pivot_metrics(dirs: ReportDirStructure, raw=False, *args, **kwargs):
    suffix = '_raw' if raw else ''
    return json.load(open(f"{dirs.report_dir}/pivot_metrics{suffix}.json"))
