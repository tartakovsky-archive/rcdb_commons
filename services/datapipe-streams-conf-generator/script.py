import os
import copy
import json
from string import Template
from collections import defaultdict

import ccxt
import requests


if os.path.exists('conf'):
    for f in os.listdir("conf/services"):
        os.remove(os.path.join("conf/services/", f))


accounts = defaultdict(list) # {"SPOT": ["et_sub_1"]}
credentials = json.load(open('credentials.json'))

token = os.environ['TOKEN']
r = requests.get('https://dash.3jane.com/api/exchange-credentials', headers={'Authorization': f'Bearer {token}'})
r.raise_for_status()
res = {}

for cred in r.json():
    if cred['account_type'] in {'SPOT', 'USDT_M_FUTURES'}:
        accounts[cred['account_type']].append(cred['name'])

HOST_PATH = "/home/ubuntu/streams"

latest_source_id = 10_000

def get_source_id():
    global latest_source_id
    latest_source_id += 1
    return latest_source_id

def batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]


def get_queue(type, account_type, batch_id, direction='out'):
    queue_name = f'exchange-data-{type}-{account_type}-{batch_id}-{direction}'
    roll_cycle = 'TEN_MINUTELY' if direction == 'out' else 'FAST_DAILY'

    return (
        queue_name,
        Template("$queue_name: { path: queues/$queue_name, sourceId: $queue_id, builder: !SingleChronicleQueueBuilder { blockSize: 268435456, readOnly: false, rollCycle: $roll_cycle }}").substitute(
            queue_name=queue_name,
            queue_id=get_source_id(),
            roll_cycle=roll_cycle,

        )
    )

quest_services = Template("""
!ChronicleServicesCfg {

  queues: {
    quest-in-trades: {path: queues/quest-in-trades, sourceId: 505, builder: !SingleChronicleQueueBuilder {blockSize: 268435456, rollCycle: FAST_DAILY }},
    quest-out-trades: {path: queues/quest-out-trades, sourceId: 506, builder: !SingleChronicleQueueBuilder {blockSize: 268435456, rollCycle: FAST_DAILY }},
    quest-in-price-tickers: {path: queues/quest-in-price-tickers, sourceId: 503, builder: !SingleChronicleQueueBuilder {blockSize: 268435456, rollCycle: FAST_DAILY }},
    quest-out-price-tickers: {path: queues/quest-out-price-tickers, sourceId: 504, builder: !SingleChronicleQueueBuilder {blockSize: 268435456, rollCycle: FAST_DAILY }},
    quest-in-ob: {path: queues/quest-in-ob, sourceId: 501, builder: !SingleChronicleQueueBuilder {blockSize: 268435456, rollCycle: FAST_DAILY }},
    quest-out-ob: {path: queues/quest-out-ob, sourceId: 502, builder: !SingleChronicleQueueBuilder {blockSize: 268435456, rollCycle: FAST_DAILY }},
    instruments-out: { path: queues/instruments-out, sourceId: 2, builder: !SingleChronicleQueueBuilder { blockSize: 268435456, rollCycle: FAST_DAILY }},
    monitoring-exporters-in: { path: queues/monitoring-exporters-in, sourceId: 301, builder: !SingleChronicleQueueBuilder { blockSize: 26843545600, rollCycle: TEN_MINUTELY }},
    monitoring-exporters-out: { path: queues/monitoring-exporters-out, sourceId: 300, builder: !SingleChronicleQueueBuilder { blockSize: 26843545600, rollCycle: TEN_MINUTELY }},
    monitoring-private-and-trades-out: { path: queues/monitoring-private-and-trades-out, sourceId: 299, builder: !SingleChronicleQueueBuilder { blockSize: 26843545600, rollCycle: TEN_MINUTELY }},
    monitoring-ob-out: { path: queues/monitoring-ob-out, sourceId: 298, builder: !SingleChronicleQueueBuilder { blockSize: 26843545600, rollCycle: TEN_MINUTELY }},
    monitoring-price-tickers-out: { path: queues/monitoring-price-tickers-out, sourceId: 297, builder: !SingleChronicleQueueBuilder { blockSize: 26843545600, rollCycle: TEN_MINUTELY }},

    prometheus-gw-out: { path: queues/prometheus-gw-out, sourceId: 302, builder: !SingleChronicleQueueBuilder { blockSize: 26843545600, rollCycle: TEN_MINUTELY }},
    
    $queues
  },

  services: {
    prometheus-gw: {
      inputs: [ monitoring-exporters-out, monitoring-private-and-trades-out, monitoring-ob-out, monitoring-price-tickers-out ],
      output: prometheus-gw-out,
      pauser: busy,
      startFromStrategy: END,
      implClass: !type software.chronicle.monitorgateway.prometheus.PrometheusGateway
   },

    quest-trades: {
      inputs: [ quest-in-trades, instruments-out, $queues_trades  ],
      output: quest-out-trades,
      implClass: !type com._3jane.common.services.ILPExporter,
      endpoint: '172.31.32.203:9009',
      periodicUpdateMS: 100, # This is necessary - periodic updates are used instead of timer thread.
      periodicUpdateMSInitial: 100,
      startFromStrategy: NAMED,
      pauser: busy,
    },
    
    quest-price-tickers: {
      inputs: [ quest-in-price-tickers, instruments-out, $queues_price_tickers_private ],
      output: quest-out-price-tickers,
      implClass: !type com._3jane.common.services.ILPExporter,
      endpoint: '172.31.32.203:9009',
      periodicUpdateMS: 100, # This is necessary - periodic updates are used instead of timer thread.
      periodicUpdateMSInitial: 100,
      startFromStrategy: NAMED,
      pauser: busy,
    },
    
    quest-ob: {
      inputs: [ quest-in-ob, instruments-out, $queues_ob ],
      output: quest-out-ob,
      implClass: !type com._3jane.common.services.ILPExporter,
      endpoint: '172.31.32.203:9009',
      periodicUpdateMS: 100, # This is necessary - periodic updates are used instead of timer thread.
      periodicUpdateMSInitial: 100,
      startFromStrategy: NAMED,
      pauser: busy,
    },
    
    monitoring-exporters: {
      inputs: [
        monitoring-exporters-in,
        quest-out-trades,
        quest-out-price-tickers,
        quest-out-ob,
        instruments-out,
        prometheus-gw-out
      ],
      output: monitoring-exporters-out,
      pauser: busy,
      startFromStrategy: END,
      implClass: !type software.chronicle.services.monitor.MonitorService,
      periodicUpdateMS: 1000,
      aggregate: 10
    },
  }
}
""")

TEMPLATE = Template("""
!ChronicleServicesCfg {

  queues: {
    instruments-in: {path: queues/instruments-in, sourceId: 1, builder: !SingleChronicleQueueBuilder {blockSize: 268435456, rollCycle: FAST_DAILY }},
    instruments-out: { path: queues/instruments-out, sourceId: 2, builder: !SingleChronicleQueueBuilder { blockSize: 268435456, rollCycle: FAST_DAILY }},
    rotator-in: {path: queues/rotator-in, sourceId: 13, builder: !SingleChronicleQueueBuilder {blockSize: 268435456, rollCycle: FAST_DAILY }},
    rotator-out: {path: queues/rotator-out, sourceId: 14, builder: !SingleChronicleQueueBuilder {blockSize: 268435456, rollCycle: FAST_DAILY }},
    monitoring-private-and-trades-in: { path: queues/monitoring-private-and-trades-in, sourceId: 303, builder: !SingleChronicleQueueBuilder { blockSize: 26843545600, rollCycle: TEN_MINUTELY }},
    monitoring-private-and-trades-out: { path: queues/monitoring-private-and-trades-out, sourceId: 299, builder: !SingleChronicleQueueBuilder { blockSize: 26843545600, rollCycle: TEN_MINUTELY }},
    $queues
  },

  services: {
    instruments: {
      inputs: [instruments-in],
      output: instruments-out,
      implClass: !type com._3jane.common.services.InstrumentsService,
      apiUrl: 'http://instruments.3jservices.ml',
      periodicUpdateMS: 100, # This is necessary - periodic updates are used instead of timer thread.
      periodicUpdateMSInitial: 100,
      startFromStrategy: END,
      pauser: yielding,
    },

    rotator: {
      inputs: [ rotator-in ],
      output: rotator-out,
      startFromStrategy: END,
      implClass: !type com._3jane.common.services.QueuesRollerService,
      queueDirs: [
        $rotator_queues
      ],
      removeOnly: true,
      periodicUpdateMS: 300000,
      periodicUpdateMSInitial: 100,
      pauser: yielding,
    },
    
    $services
    
    monitoring-private-and-trades: {
      inputs: [
        monitoring-private-and-trades-in,
        instruments-out,
        rotator-out,
        $queues_monitoring
      ],
      output: monitoring-private-and-trades-out,
      pauser: yielding,
      startFromStrategy: END,
      implClass: !type software.chronicle.services.monitor.MonitorService,
      periodicUpdateMS: 1000,
      aggregate: 10
    },
  }
}
""")

PUBLIC_STREAMS_OB_TEMPLATE = Template("""
!ChronicleServicesCfg {

  queues: {
    instruments-out: { path: queues/instruments-out, sourceId: 2, builder: !SingleChronicleQueueBuilder { blockSize: 268435456, rollCycle: FAST_DAILY }},
    monitoring-ob-in: { path: queues/monitoring-ob-in, sourceId: 304, builder: !SingleChronicleQueueBuilder { blockSize: 26843545600, rollCycle: TEN_MINUTELY }},
    monitoring-ob-out: { path: queues/monitoring-ob-out, sourceId: 298, builder: !SingleChronicleQueueBuilder { blockSize: 26843545600, rollCycle: TEN_MINUTELY }},
    $queues
  },

  services: {
    $services
    
    monitoring-ob: {
      inputs: [
        monitoring-ob-in,
        $queues_monitoring
      ],
      output: monitoring-ob-out,
      pauser: busy,
      startFromStrategy: END,
      implClass: !type software.chronicle.services.monitor.MonitorService,
      periodicUpdateMS: 1000,
      aggregate: 10
    },
  }
}
""")

PUBLIC_STREAMS_PRICE_TICKERS_TEMPLATE = Template("""
!ChronicleServicesCfg {

  queues: {
    instruments-out: { path: queues/instruments-out, sourceId: 2, builder: !SingleChronicleQueueBuilder { blockSize: 268435456, rollCycle: FAST_DAILY }},
    exchange-data-price-tickers: { path: queues/exchange-data-price-tickers, sourceId: 105, builder: !SingleChronicleQueueBuilder { blockSize: 268435456, rollCycle: TEN_MINUTELY }},
    monitoring-price-tickers-in: { path: queues/monitoring-price-tickers-in, sourceId: 305, builder: !SingleChronicleQueueBuilder { blockSize: 26843545600, rollCycle: TEN_MINUTELY }},
    monitoring-price-tickers-out: { path: queues/monitoring-price-tickers-out, sourceId: 297, builder: !SingleChronicleQueueBuilder { blockSize: 26843545600, rollCycle: TEN_MINUTELY }},
    
    $queues
  },

  services: {
    $services
    
    monitoring-price-tickers: {
      inputs: [
        monitoring-price-tickers-in,
        instruments-out,
        $queues_monitoring
      ],
      output: monitoring-price-tickers-out,
      pauser: busy,
      startFromStrategy: END,
      implClass: !type software.chronicle.services.monitor.MonitorService,
      periodicUpdateMS: 1000,
      aggregate: 10
    },
  }
}
""")


def gen_public_service(tickers, delay, account_type, batch_id, out_queue, in_queue):
    template = Template("""
    $account_type-$batch_id-market-data: {
      inputs: [ $in_queue, instruments-out ],
      output: $out_queue,
      startFromStrategy: END,
      implClass: !type com._3jane.adapters.binance.BinancePublicStreamHandlerImpl,
      periodicUpdateMS: 100,
      periodicUpdateMSInitial: $delay,
      pauser: yielding,
      tickers: [ $tickers ],
      market: $account_type,
      depth: true,
      bookTicker: true,
      trade: true,
      forceNetty: true
    },
    """)
    return template.substitute(
        tickers=tickers, delay=delay, account_type=account_type,
        batch_id=batch_id, out_queue=out_queue, in_queue=in_queue
    )

def gen_public_ob_service(tickers, delay, account_type, batch_id, out_queue, in_queue):
    template = Template("""
    $account_type-$batch_id-market-data-ob: {
      inputs: [ $in_queue, instruments-out ],
      output: $out_queue,
      startFromStrategy: END,
      implClass: !type com._3jane.adapters.binance.BinancePublicStreamHandlerImpl,
      periodicUpdateMS: 100,
      periodicUpdateMSInitial: $delay,
      pauser: yielding,
      tickers: [ $tickers ],
      market: $account_type,
      depth: true,
      forceNetty: true
    },
    """)
    return template.substitute(
        tickers=tickers, delay=delay, account_type=account_type,
        batch_id=batch_id, out_queue=out_queue, in_queue=in_queue
    )


def gen_public_price_tickers_service(tickers, delay, account_type, batch_id, out_queue, in_queue):
    template = Template("""
    $account_type-$batch_id-market-data-price-tickers: {
      inputs: [ $in_queue, instruments-out ],
      output: $out_queue,
      startFromStrategy: END,
      implClass: !type com._3jane.adapters.binance.BinancePublicStreamHandlerImpl,
      periodicUpdateMS: 100,
      periodicUpdateMSInitial: $delay,
      pauser: yielding,
      tickers: [ $tickers ],
      market: $account_type,
      bookTicker: true,
      forceNetty: true
    },
    """)
    return template.substitute(
        tickers=tickers, delay=delay, account_type=account_type,
        batch_id=batch_id, out_queue=out_queue, in_queue=in_queue
    )

def gen_public_trades_service(tickers, delay, account_type, batch_id, out_queue, in_queue):
    template = Template("""
    $account_type-$batch_id-market-data-trades: {
      inputs: [ $in_queue, instruments-out ],
      output: $out_queue,
      startFromStrategy: END,
      implClass: !type com._3jane.adapters.binance.BinancePublicStreamHandlerImpl,
      periodicUpdateMS: 100,
      periodicUpdateMSInitial: $delay,
      pauser: yielding,
      tickers: [ $tickers ],
      market: $account_type,
      trade: true,
      forceNetty: true
    },
    """)
    return template.substitute(
        tickers=tickers, delay=delay, account_type=account_type,
        batch_id=batch_id, out_queue=out_queue, in_queue=in_queue
    )

SWAP_QUEUE_ID = 3000

def gen_swap_market_data_service(tickers, delay, out_queue, in_queue):
    template = Template("""
    SWAP-market-data: {
      inputs: [ $in_queue, instruments-out ],
      output: $out_queue,
      startFromStrategy: END,
      implClass: !type com._3jane.adapters.binance.BinancePublicStreamHandlerImpl,
      periodicUpdateMS: 100,
      periodicUpdateMSInitial: $delay,
      pauser: yielding,
      accountNames: [ bn_cy_main@3jane.com ],
      tickers: [ $tickers ],
      market: SWAP,
      bookTicker: true,
      forceNetty: true
    },
    """)
    return template.substitute(
        tickers=tickers, delay=delay, out_queue=out_queue, in_queue=in_queue
    )


def get_balance_conf(queue_in, account_names, is_spot, delay, batch_id, ip, out_queue):
    if is_spot:
        klass = 'BinanceAccountInfoServiceImpl'
    else:
        klass = 'BinanceFuturesAccountInfoServiceImpl'

    template = Template("""
    binance-balance-service-$account_type-$batch_id: {
      inputs: [ $queue_in, instruments-out ],
      output: $out_queue,
      startFromStrategy: END,
      implClass: !type com._3jane.adapters.binance.$klass,
      periodicUpdateMS: 100, # This is necessary - periodic updates are used instead of timer thread.
      periodicUpdateMSInitial: $delay, # This is necessary - periodic updates are used instead of timer thread.
      pauser: yielding,
      accountNames: [ $account_names ],
      forceNetty: true
    },
""")
    return template.substitute(
        account_type='spot' if is_spot else 'futures',
        batch_id=batch_id,
        queue_in=queue_in,
        klass=klass,
        delay=delay,
        account_names=account_names,
        out_queue=out_queue
    )

api = ccxt.binance({})
binance_markets_spot = set([x['symbol'].replace('/', '') for x in api.fetch_markets() if x['active']])
binance_markets_spot_top_20_volume = {'BTCUSDT', 'BTCUSDT'}

api = ccxt.binanceusdm({})
binance_markets_fut = set([x['symbol'].replace('/', '') for x in api.fetch_markets() if x['active']])

print(len(binance_markets_spot), len(binance_markets_fut))
delay = 0


public_queues = []
public_services = []

all_out_queues = []
all_in_queues = []

exportable_queues = defaultdict(list)

# rotator conf
rotator_queues = [
    'quest-in',
    'quest-out',
    'instruments-out',
    'instruments-in',
    'rotator-in',

    'quest-in-price-tickers',
    'quest-out-price-tickers',

    'quest-in-trades',
    'quest-out-trades',

    'quest-in-ob',
    'quest-out-ob',

    'monitoring-out',
    'monitoring-ob-in',
    'monitoring-exporters-in',
    'monitoring-private-and-trades-in',
    'monitoring-price-tickers-in',
    'prometheus-gw-out',
]


for type_start, gen_func, template, name in [
    (0, gen_public_price_tickers_service, PUBLIC_STREAMS_PRICE_TICKERS_TEMPLATE, 'price-tickers'),
    (100, gen_public_ob_service, PUBLIC_STREAMS_OB_TEMPLATE, 'ob'),
    (200, gen_public_trades_service, None, 'trades')
]:
    public_queues.clear()
    public_services.clear()

    for tickers, is_spot in [(binance_markets_spot, True), (binance_markets_fut, False)]:
        if is_spot:
            batch_size = 800
            prefix = 'spot'
        else:
            batch_size = 105
            prefix = 'futures'

        for batch_id, tickers_batch in enumerate(batch(list(tickers), batch_size)):
            delay += 10_000

            in_queue_name, in_queue_row  = get_queue(name, prefix, batch_id, 'in')
            out_queue_name, out_queue_row = get_queue(name, prefix, batch_id, 'out')

            exportable_queues[name].append((out_queue_name, out_queue_row))

            rotator_queues.append(in_queue_name)
            rotator_queues.append(out_queue_name)

            public_queues.append((in_queue_name, in_queue_row))
            public_queues.append((out_queue_name, out_queue_row))

            public_services.append(
                gen_func(
                    account_type='SPOT' if is_spot else 'LINEAR_FUTURES',
                    batch_id=batch_id,
                    delay=delay,
                    tickers=', '.join(tickers_batch),
                    out_queue=out_queue_name,
                    in_queue=in_queue_name
                )
            )
    if name == 'price-tickers':
        in_queue_name, in_queue_row = get_queue(name, 'swap', 0, 'in')
        out_queue_name, out_queue_row = get_queue(name, 'swap', 0, 'out')
        exportable_queues[name].append((out_queue_name, out_queue_row))

        rotator_queues.append(in_queue_name)
        rotator_queues.append(out_queue_name)

        public_queues.append((in_queue_name, in_queue_row))
        public_queues.append((out_queue_name, out_queue_row))

        delay += 2_000
        public_services.append(
            gen_swap_market_data_service(
                tickers=', '.join(x for x in (binance_markets_spot | binance_markets_fut)),
                delay=delay, out_queue=out_queue_name, in_queue=in_queue_name
            )
        )

    if name != 'trades':
        open(f"conf/services/{name}-streams.yaml", "w+").write(
            template.substitute(
                queues=',\n    '.join(y for x, y in public_queues),
                services='\n'.join(public_services),
                queues_monitoring=',\n        '.join(x for x, y in public_queues if 'out' in x)
            )
        )


# PRIVATE STREAMS
delay += 10_000
services = []
futures_services = []
queues = []
futures_queues = []
for i, b in enumerate(list(credentials)):
    ip = None

    in_queue_spot_name, in_queue_spot_row = get_queue('balance', 'spot', i, 'in')
    in_queue_future_name, in_queue_future_row = get_queue('balance', 'future', i, 'in')
    out_queue_spot_name, out_queue_spot_row = get_queue('balance', 'spot', i, 'out')
    out_queue_future_name, out_queue_future_row = get_queue('balance', 'future', i, 'out')

    exportable_queues['private'].append((out_queue_future_name, out_queue_future_row))
    exportable_queues['private'].append((out_queue_spot_name, out_queue_spot_row))

    services.append(
        get_balance_conf(in_queue_spot_name, b, True, delay + 1000 * i, i, ip, out_queue_spot_name)
    )
    futures_services.append(
        get_balance_conf(in_queue_future_name, b, False, delay + 1000 * i, i, ip, out_queue_future_name)
    )
    queues.append((in_queue_spot_name, in_queue_spot_row))
    queues.append((out_queue_spot_name, out_queue_spot_row))
    futures_queues.append((in_queue_future_name, in_queue_future_row))
    futures_queues.append((out_queue_future_name, out_queue_future_row))

    for q in [in_queue_future_name, out_queue_future_name, in_queue_spot_name, out_queue_spot_name]:
        rotator_queues.append(q)


open(f"conf/services/private-and-trades-streams.yaml", "w+").write(
    TEMPLATE.substitute(
        queues=',\n    '.join(x[1] for x in (queues + futures_queues + public_queues)),
        rotator_queues=',\n        '.join(map(lambda q: f'queues/{q}', rotator_queues)),
        services='\n'.join(services + futures_services + public_services),
        queues_monitoring=',\n        '.join(x for x, y in filter(lambda q: 'out' in q[0], queues + futures_queues + public_queues))
    )
)

open(f"conf/services/quest-exporter.yaml", "w+").write(
    quest_services.substitute(
        queues_trades=', '.join(x[0] for x in exportable_queues['trades']),
        queues_ob=', '.join(x[0] for x in exportable_queues['ob']),
        queues_price_tickers_private=', '.join(x[0] for x in exportable_queues['price-tickers'] + exportable_queues['private']),
        queues=',\n    '.join(x[1] for x in (exportable_queues['trades'] + exportable_queues['ob'] + exportable_queues['price-tickers'] + exportable_queues['private']))
    )
)



ram = {
    'private-and-trades-streams': 4000,
    'ob-streams': 9000,
    'price-tickers-streams': 5000,
    'quest-exporter': 1000
}
print(sum(ram.values()))

isolate = {
    'ob-streams': '2',
    'price-tickers-streams': '4',
    'private-and-trades-streams': '6',
    'quest-exporter': '1'
}

app = {
    "name": "",
    "namespace": "export",
    "cwd": HOST_PATH,
    "args": [
      "-XX:+UnlockExperimentalVMOptions",
      "-XX:+UseZGC",
      "-server",
      "-Xmx1280m",
      "-DfastJava8IO=true",
      "-XX:CompileThreshold=1500",
      "--add-exports=java.base/jdk.internal.ref=ALL-UNNAMED",
      "--add-exports=java.base/jdk.internal.util=ALL-UNNAMED",
      "--add-exports=java.base/sun.nio.ch=ALL-UNNAMED",
      "--add-exports=jdk.unsupported/sun.misc=ALL-UNNAMED",
      "--add-exports=jdk.compiler/com.sun.tools.javac.file=ALL-UNNAMED",
      "--add-opens=jdk.compiler/com.sun.tools.javac=ALL-UNNAMED",
      "--add-opens=java.base/java.lang=ALL-UNNAMED",
      "--add-opens=java.base/java.lang.reflect=ALL-UNNAMED",
      "--add-opens=java.base/java.io=ALL-UNNAMED",
      "--add-opens=java.base/java.util=ALL-UNNAMED",
      "-XX:+HeapDumpOnOutOfMemoryError",
      "-cp", "runners-1.0-SNAPSHOT-all.jar",
      "com._3jane.runners.RunServiceEventLoop", "ANY"
    ],
    "env": {
        "CREDENTIALS_PATH": "/home/ubuntu/streams/credentials.json",
        "LOG_LEVEL": "WARN",
        "PAUSER": "YIELDING",
        "REFETCH_SNAPSHOT": "true",
        "DISABLE_DEPTH_SNAPSHOTS": "true"
    },
    "script": "java",
    "node_args": [],
    "time": True,
    "exec_interpreter": "none",
    "exec_mode": "fork"
}
files = os.listdir("conf/services")

apps = []
for f in sorted(files):
    t = copy.deepcopy(app)
    t['name'] = f.replace(".yaml", "")

    if t['name'] in isolate:
        t['args'][-1] = isolate.get(t['name'], 'ANY')

    if t['name'] == 'quest-exporter':
        t['env']['PAUSER'] = 'BUSY'

    t['args'].append("services/" + f)
    t['args'][3] = f'-Xmx{ram[t["name"]]}m'
    apps.append(t)

res = f'''
module.exports = {{
  "apps": {json.dumps(apps, indent=4)}
}}
'''
open("conf/ecosystem.config.js", "w+").write(res)

res = []

extra = {
"SPOT": {
      "orderPerTimeframeCount": 2,
      "orderTimeframeNs": 10000000000,
      "orderMinTimeBetweenOrdersNs": 0,
      "orderBurstPerInstrumentCount": 2147483647,
      "orderBurstPerInstrumentTimeframe": 0
    },
    "SWAP": {
      "orderPerTimeframeCount": 50,
      "orderTimeframeNs": 10000000000,
      "orderMinTimeBetweenOrdersNs": 0,
      "orderBurstPerInstrumentCount": 2147483647,
      "orderBurstPerInstrumentTimeframe": 0
    },
    "MARGIN": {
      "orderPerTimeframeCount": 50,
      "orderTimeframeNs": 10000000000,
      "orderMinTimeBetweenOrdersNs": 0,
      "orderBurstPerInstrumentCount": 2147483647,
      "orderBurstPerInstrumentTimeframe": 0
    },
    "LINEAR_FUTURES": {
      "dualPositionMode": True,
      "orderPerTimeframeCount": 50,
      "orderTimeframeNs": 10000000000,
      "orderMinTimeBetweenOrdersNs": 0,
      "orderBurstPerInstrumentCount": 2147483647,
      "orderBurstPerInstrumentTimeframe": 0
    },
    "INVERSE_FUTURES": {
      "dualPositionMode": True,
      "orderPerTimeframeCount": 100,
      "orderTimeframeNs": 10000000000,
      "orderMinTimeBetweenOrdersNs": 0,
      "orderBurstPerInstrumentCount": 2147483647,
      "orderBurstPerInstrumentTimeframe": 0
    }
}
for i, [k, v] in enumerate(credentials.items()):
    res.append({'id': i, 'accountName': k, 'exchange': 'BINANCE', **v, 'settings': extra})

json.dump(res, open('conf/credentials.json', 'w'), indent=4)

