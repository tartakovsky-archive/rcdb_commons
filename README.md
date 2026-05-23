# rcdb_commons

> Shared Python SDK and schema layer for the RCDB multi-exchange automated trading platform.

[![Python](https://img.shields.io/badge/Python-3.x-3776AB)](https://www.python.org/)
[![Pydantic](https://img.shields.io/badge/Pydantic-1.8-E92063)](https://docs.pydantic.dev/)
[![1Password Connect](https://img.shields.io/badge/1Password-Connect-0572EC)](https://developer.1password.com/docs/connect/)
[![Grafana](https://img.shields.io/badge/Grafana-Provisioned-F46800)](https://grafana.com/)
[![Sentry](https://img.shields.io/badge/Sentry-Integrated-362D59)](https://sentry.io/)
[![Status](https://img.shields.io/badge/Status-Archived-lightgrey)](#lineage)

**Archived** - cloned from `hcmc-project/rcdb_commons` for posterity. Part of the **RCDB** automated trading platform, later merged into [3Jane Technologies](https://github.com/3jane).

---

## Table of contents

- [What this was](#what-this-was)
- [Tech stack](#tech-stack)
- [What's inside](#whats-inside)
- [Schema highlights](#schema-highlights)
- [Operational tooling](#operational-tooling)
- [Architecture role](#architecture-role)
- [Lineage](#lineage)
- [Sibling repos](#sibling-repos)

## What this was

`rcdb_commons` was the **shared SDK every other RCDB service linked against**. It defined the Pydantic schemas that crossed every service boundary - research notebooks, the execution engine, the operations dashboard, and the time-series datastore - so that strategy configs, exchange credentials, symbols, and account types had a single canonical representation across the platform.

On top of those schemas it shipped **three typed REST clients**: `DataStore` for pushing and pulling time-series rows (OHLCV, Kalman-filtered signals, bot performance, price index, account trades), `ConfigStore` for fetching validated `BotConfigResponse` strategy bundles by `bot_id`, and `CredentialsStore` for resolving exchange API keys out of a self-hosted 1Password Connect vault at runtime.

Alongside the library the repo packages the **operational sidecars** that kept the platform running: a Python datapipe ETL that ships per-account trade and balance CSVs into QuestDB via the `questdb.ingress` line protocol, a QuestDB partition backup job that rolls cold data to S3, an orderbook dump shell script that syncs gzipped depth captures to S3, a YAML generator for the Chronicle-Queue stream configs that fanned exchange data into the platform, and Docker Compose stacks for self-hosted Sentry and 1Password Connect plus a Grafana/Prometheus bootstrap with nine pre-built dashboards.

## Tech stack

| Layer | Tools |
|---|---|
| Language | Python 3, `setuptools` |
| Schemas and validation | `pydantic==1.8.1` (discriminated unions, root validators, `Literal` config types) |
| HTTP | `requests~=2.26.0` with `requests-mock` for tests |
| Data | `pandas~=1.3.4` |
| Time-series sink | QuestDB via `questdb.ingress.Sender` (line protocol) |
| Secrets | 1Password Connect (`onepasswordconnectsdk==1.0.1`), self-hosted via Docker Compose |
| Object storage | AWS S3 (`s3fs`, `aws s3 sync`) |
| Observability | Sentry (`sentry_sdk`), Grafana OSS, Prometheus, `node_exporter` |
| Streams config | Chronicle Queue / Chronicle Services YAML |
| Test | `pytest==6.2.2`, `pytest-mock`, `requests-mock` |

## What's inside

- `data_store.py`, `config_store.py` - top-level entry points (kept for backwards compatibility); the real implementations live under `lib/stores/`
- `lib/stores/data_store.py` - typed `DataStore` REST client. Auto-detects the `DataType` (`ohlcv`, `kalman`, `bot_performance`, `price_index`, `account_trades`) from a DataFrame's columns and POSTs rows to `/log/`; `read()` returns timestamp-indexed DataFrames from `/latest/`
- `lib/stores/config_store.py` - typed `ConfigStore` REST client. `get_config(bot_id)` returns a fully parsed `BotConfigResponse`, dispatched through Pydantic's discriminated union on `config_type`
- `lib/stores/credentials_store.py` - `CredentialsStore` wraps the 1Password Connect SDK; `replace_exchange_credentials_with_secrets()` resolves an `ExchangeCredentials` whose `credentials` field is a vault item title into one whose `credentials` field is the decrypted JSON
- `lib/schemas/exchange.py` - the trading domain: `Exchange`, `AccountType`, `ExchangeCredentials`, `Symbol`, `SymbolFutures`, `Instrument`, `Order`, `OrderBook`, `Position`, `Positions`, `AssetSpotBalance` / `AssetMarginBalance` / `AssetFuturesBalance`, `OrderSide`, `OrderType`, `OrderStatus`, `TransferType`
- `lib/schemas/strategy_configs.py` - the strategy zoo: ~15 active `*Config` variants (pure market making, grid, stat-arb Kalman, spike filter, trend following, futures, cross-exchange MM, spot-to-futures hedge, ZMQ external price, orderbook collectors, ...) plus `BorrowingConfig`, `OrderGridConfig`, `BotConfigResponse`, and the `STRATEGY_CONFIG_CLASS_MAP` registry
- `lib/schemas/exchange_events.py` - `ExchangeEvents` and `BinanceStreams` event-type enums
- `lib/misc/rounding.py` - `to_precision`, `to_auto_price_precision`, `Rounder` (decimal-safe price/amount quantization down to sub-bp precision)
- `lib/misc/types.py`, `lib/misc/id_generator.py` - small typing and id helpers
- `lib/helpers/graceful_killer.py` - SIGINT/SIGTERM trap for long-running workers
- `services/` - operational sidecars (see below)
- `tests/` - `pytest` coverage for the three stores and the schema/enum layer (`test_datastore.py`, `test_credentials_store.py`, `test_schemas.py`, `test_enums.py`) using `requests-mock` and `pytest-mock`

## Schema highlights

The schema layer is what made the rest of the platform safe to refactor. Everything below is `pydantic.BaseModel`, lives in `lib/schemas/`, and is shared verbatim by the datastore, dashboard, research, and execution sides.

- `ExchangeCredentials` (`lib/schemas/exchange.py`) - `{exchange: Exchange, credentials: dict | str, type: AccountType}`. The `str` form is a 1Password vault item title that `CredentialsStore` resolves at runtime; `is_filled()` distinguishes the two states. `ExchangeCredentialsEmpty` is a `Literal['EMPTY']` sentinel used as a default in configs.
- `AccountType` (`lib/schemas/exchange.py`) - `MAIN`, `SPOT`, `SWAP`, `CROSS_MARGIN`, `ISOLATED_MARGIN`, `USDT_M_FUTURES`, `COIN_M_FUTURES`, plus Bybit-specific `INVERSE_PERPETUAL` and `INVERSE_FUTURES`. Carries `is_spot`, `is_margin`, `is_futures` predicates and Django-style `choices()`.
- `Exchange` enum covers Binance (spot, USDM, COINM, swap, public), Ascendex, Coinbase, Commex, Kraken, OKEx, KuCoin, Bybit, Huobi, WhiteBIT.
- `Symbol` and `SymbolFutures` - canonical pair representation with `from_ccxt` / `from_binance` parsers and `to_ccxt` / `to_binance` / `to_kucoin` serializers; `SYMBOL_EMPTY` is the sentinel default.
- `BotConfigResponse` (`lib/schemas/strategy_configs.py`) - the wire shape returned by the config API. The `strategy_config` field is a `Union[...]` discriminated on `config_type` covering the full strategy zoo (`GridConfig`, `PureMarketMakingConfig`, `PureMarketMakingFuturesConfig`, `StatArbKalmanConfig`, `CrossExchangeMarketMakingFuturesConfig`, `SpotToFuturesHedgingConfig`, `FuturesToFuturesHedgingConfig`, `PureMarketMakingSpikeFilterConfig`, `TrendFollowingMakingFuturesConfig`, `OrderBookCollectorSpotConfig`, `OrderBookCollectorFuturesConfig`, `PureMarketMakingExternalPriceConfig`, `PureMarketMakingExternalPriceZMQConfig`, `PureMarketMakingExternalCrossPriceConfig`, `PureMarketMakingFuturesExternalPriceConfig`, `BSwapSellConfig`).
- `BorrowingConfig` - cross-margin borrow/repay levels for base and quote with `margin_level_max` ceiling.
- `OrderGridConfig` / `LongOrderGridConfig` / `ShortOrderGridConfig` - entry/exit grid parameters convertible to `BidAskLevelsConfig` depending on side.
- `Order`, `OrderBook`, `Position`, `Positions`, `AccountBalance`, `AccountMarginBalance` - execution-side primitives with `Decimal` everywhere and helpers like `OrderBook.bid_ask_no_dust()` that skip dust levels when picking the effective top of book.
- `AdminConfigInput` - the inverse shape used by the dashboard's admin form, with `root_validator`s that enforce `config_type` matches `type(data).__name__` and synthesize defaults when `data` is omitted.

## Operational tooling

- `services/datapipe-et/` - Python ETL (`main.py` + `src/data_loader.py`, `src/fsio.py`) that reads per-account spot/swap trade and kline CSVs, normalizes columns, joins quote prices and fees, and ingests into QuestDB via the `questdb.ingress.Sender` line protocol. Posts to the dashboard API using a bearer token; reports failures to Sentry when `SENTRY_DSN` is set.
- `services/qdb-backup/` - rolls QuestDB partitions older than the retention window (`orderbook`: 24 partitions, `trades`: 7 * 24, `price_tickers`: 7) out of the live database to an `s3fs`-mounted `qdb-backups` bucket as gzipped CSVs; retries with backoff on connection failure.
- `services/orderbook-syncer/dump-orderbooks.sh` - `aws s3 sync` of gzipped daily orderbook captures to an S3 bucket, excluding the file dated today; removes successfully uploaded files locally.
- `services/datapipe-streams-conf-generator/` - generator that pulls live exchange credentials from `dash.3jane.com/api/exchange-credentials`, partitions them into SPOT and USDT_M_FUTURES batches, and emits Chronicle Queue / Chronicle Services YAML configs that wire up the per-exchange data, orderbook, ticker, and trade streams plus monitoring exporters and a Prometheus gateway.
- `services/grafana/` - bootstrap `start.sh` that brings up Prometheus and Grafana OSS in Docker, with provisioned `nodes/` (`node_exporter` install script, systemd unit, Docker `daemon.json`), `prometheus.yml`, and nine pre-built dashboards under `dashboards/` (account assets, accounts data, futures accounts, Chronicle metrics, high-level overview, Node Exporter Full, QuestDB, table stat, table updates).
- `services/sentry/` - Docker Compose stack for a self-hosted Sentry instance used by the platform; the Python services hook into it via `sentry_sdk.init(SENTRY_DSN)`.
- `services/1password-connect-server/` - Docker Compose stack for the on-prem 1Password Connect server that `CredentialsStore` talks to.

## Architecture role

`rcdb_commons` sat in the middle of the platform. Every other service depended on it for schemas and clients; it depended on no other RCDB service at code level - it spoke to them only through injected `api_url` + `token` pairs.

```mermaid
graph LR
    research[rcdb_research<br/>quant notebooks]
    dashboard[rcdb_dashboard<br/>Django ops console]
    execution[execution engine<br/>bots]
    datastore[rcdb_datastore<br/>FastAPI time-series API]

    commons[(rcdb_commons<br/>schemas + clients)]

    op[1Password Connect]
    qdb[(QuestDB)]
    s3[(S3 backups)]
    sentry[Sentry]
    grafana[Grafana / Prometheus]

    research --> commons
    dashboard --> commons
    execution --> commons
    datastore --> commons

    commons -. DataStore .-> datastore
    commons -. ConfigStore .-> dashboard
    commons -. CredentialsStore .-> op

    datapipe[datapipe-et] --> qdb
    qdbbackup[qdb-backup] --> s3
    obsync[orderbook-syncer] --> s3
    datapipe --> sentry
    qdbbackup --> sentry
    qdb --> grafana
```

The pattern throughout is **API URLs and bearer tokens passed in at construction**, not direct cross-service imports. Each service can be deployed and scaled independently; `rcdb_commons` only constrains the wire shape.

## Lineage

- **Origin:** `hcmc-project/rcdb_commons` (private)
- **Archive:** `tartakovsky-archive/rcdb_commons` (this repo)
- **Successor:** [3Jane Technologies](https://github.com/3jane)

## Sibling repos

- [rcdb_datastore](https://github.com/tartakovsky-archive/rcdb_datastore) - FastAPI time-series API
- [rcdb_dashboard](https://github.com/tartakovsky-archive/rcdb_dashboard) - Django operations console
- [rcdb_research](https://github.com/tartakovsky-archive/rcdb_research) - quantitative research framework
