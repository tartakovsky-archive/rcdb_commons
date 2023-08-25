import logging

import asyncio

from rotator.limiters import RealTimeLimiter
from tqdm.asyncio import tqdm as aiotqdm

from exchanges import Exchanges
from exchanges.apis.http_client import wrap_client_with_rotating_proxies

from . import fsio
from .fsio import InputReader, DatasetDirStructure, ReportDirStructure


def backup_inputs(dirs: InputReader):
    fsio.write_local_creds(dirs, fsio.read_global_creds(dirs))
    fsio.write_local_params(dirs, fsio.read_global_params(dirs))
    fsio.write_local_acc_map(dirs, fsio.read_global_acc_map(dirs))
    fsio.write_local_proxies(dirs, fsio.read_global_proxies(dirs))


async def load_aux_files(dirs: DatasetDirStructure,
                         stables=('USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'USDP'),
                         wrapped=('BETH', 'WBTC', 'BDOT')):
    # Exchanges client
    creds = fsio.read_global_creds(dirs)
    params = fsio.read_global_params(dirs)

    accs = list(creds.keys())

    ex = Exchanges(credentials={'binance': dict(
        api_key=creds[accs[0]]['apiKey'],
        api_secret=creds[accs[0]]['secret'],
    )})

    # Spot fees
    df_spot_fees = await ex.bn.spot.get_fees(maker_rebate=params['maker_rebate'],
                                             bnb_discount_coef=params['bnb_discount_coef'])
    fsio.write_spot_fees(dirs, df_spot_fees)

    # Swap fees
    df_swap_fees = await ex.bn.swap.get_fees()
    fsio.write_swap_fees(dirs, df_swap_fees)

    # Swap rewards
    df_swap_rewards = await ex.bn.swap.get_rewards()
    fsio.write_swap_rewards(dirs, df_swap_rewards)

    # Quote prices in USDT
    quotes = set(df_swap_rewards['quote']).difference(wrapped)
    df_tickers = await ex.bn.spot.get_tickers(stables=stables)
    quote_prices = {q: 1 if q in stables else df_tickers.loc[f"{q}/USDT", 'last'] for q in quotes}
    fsio.write_quote_prices(dirs, quote_prices)

    # Current time
    fsio.write_current_time(dirs)


async def load_dataset(dirs: DatasetDirStructure,
                       progress: bool = True):
    creds = fsio.read_global_creds(dirs)
    params = fsio.read_global_params(dirs)
    acc_map = fsio.read_global_acc_map(dirs)
    proxies = fsio.read_global_proxies(dirs)
    df_spot_fees = fsio.read_spot_fees(dirs)
    df_swap_rewards = fsio.read_swap_rewards(dirs)
    quote_prices = fsio.read_quote_prices(dirs)

    tasks = []
    for acc in acc_map.keys():
        for bot in acc_map[acc]:
            task = dict(
                account=acc,
                api_key=creds[acc]['apiKey'],
                api_secret=creds[acc]['secret'],
                base=bot['base'],
                quote=bot['quote'],
                start=params['start'],
                end=params['end'],
                mode='sequential',
                bnb_maker_fee=df_spot_fees.loc[f"{bot['base']}/{bot['quote']}", 'maker'],
                bnb_taker_fee=df_spot_fees.loc[f"{bot['base']}/{bot['quote']}", 'taker'],
                bnb_reward_size=df_swap_rewards.loc[f"{bot['base']}/{bot['quote']}", 'reward'],
                quote_usd_price=quote_prices[bot['quote']],
            )
            tasks.append(task)

    async def load_task_data(task, data_type='spot_trades'):
        ex = Exchanges(credentials={'binance': dict(
            api_key=task['api_key'],
            api_secret=task['api_secret'],
        )})

        if data_type == 'spot_klines':
            df_klines = await ex.bn.spot.get_klines(interval='1m', **task)
            fsio.write_spot_klines(dirs, df_klines, task['account'], task['base'], task['quote'])
        elif data_type == 'spot_trades':
            df_trades = await ex.bn.spot.get_trades(**task)
            fsio.write_spot_trades(dirs, df_trades, task['account'], task['base'], task['quote'])
        elif data_type == 'swap_trades':
            df_trades = await ex.bn.swap.get_trades(**task)
            fsio.write_swap_trades(dirs, df_trades, task['account'], task['base'], task['quote'])


    logging.info("Load klines")
    wrap_client_with_rotating_proxies(proxies, limiter_class=RealTimeLimiter, limiter_args=(1000, 60))
    await (aiotqdm if progress else asyncio).gather(*[load_task_data(task=t, data_type='spot_klines') for t in tasks])
    logging.info("Load spot trades")
    wrap_client_with_rotating_proxies(proxies, limiter_class=RealTimeLimiter, limiter_args=(110, 60))
    await (aiotqdm if progress else asyncio).gather(*[load_task_data(task=t, data_type='spot_trades') for t in tasks])
    logging.info("Load swap trades")
    wrap_client_with_rotating_proxies(proxies, limiter_class=RealTimeLimiter, limiter_args=(30, 60))
    await (aiotqdm if progress else asyncio).gather(*[load_task_data(task=t, data_type='swap_trades') for t in tasks])

    # _ = await (aiotqdm if progress else asyncio).gather(
    #     *[load_task_data(task=t, data_type='spot_klines') for t in tasks],
    #     *[load_task_data(task=t, data_type='spot_trades') for t in tasks],
    #     *[load_task_data(task=t, data_type='swap_trades') for t in tasks],
    # )
