# Polish archival README

**Date:** 2026-05-23 20:49
**Scope:** README.md

## Summary

Rewrote the archival showcase README. Grounded every technical claim by reading the actual source under `lib/`, `services/`, and the top-level `data_store.py` / `config_store.py` / `setup.py` / `requirements.txt`.

## Decisions Made

### Softened / corrected vs. the prior Archival Notes
- **Chose:** describe the credential vault as "self-hosted 1Password Connect" rather than a generic "credential vault." The code in `lib/stores/credentials_store.py` imports `onepasswordconnectsdk` directly.
- **Chose:** describe `orderbook-syncer` as an `aws s3 sync` shell script of gzipped daily orderbook captures, not "real-time depth snapshots." The script `services/orderbook-syncer/dump-orderbooks.sh` is a daily S3 sync.
- **Chose:** describe Sentry both as the `sentry_sdk.init` integration used by the Python sidecars AND the self-hosted Sentry Docker Compose stack under `services/sentry/`. The prior note only said "integration."
- **Chose:** call out that the `datapipe-streams-conf-generator` emits Chronicle Queue / Chronicle Services YAML, which the prior note omitted entirely.
- **Chose:** describe the datapipe-et ETL as ingesting per-account trade/balance/kline CSVs into QuestDB via `questdb.ingress.Sender`, not "streaming market data from multiple exchanges." The prior framing was too broad.

### Could NOT verify in code
- The claim that the datastore accepts "Kalman-filtered signals, bot performance metrics, and account trade logs via a REST API" - the `DataType` enum confirms `ohlcv`, `kalman`, `bot_performance`, `price_index`, `account_trades`, so this one is fine. Kept.
- "Dozens of configuration variants" - actual count of active `*Config` classes in `strategy_configs.py` is ~15-16 (with several more commented out). Reworded to "the strategy zoo: ~15 active `*Config` variants."

## Architectural Notes

The README emphasizes the dependency-injection-via-URL-and-token pattern, which is real and visible across all three stores (`DataStore.__init__`, `ConfigStore.__init__`, `CredentialsStore.__init__` all take `api_url`/`host` + `token`). Added a Mermaid diagram showing commons in the middle of the platform.

## Information Sources
- `data_store.py`, `config_store.py`, `setup.py`, `requirements.txt`
- `lib/stores/{data_store,config_store,credentials_store}.py`
- `lib/schemas/{exchange,strategy_configs,exchange_events}.py`
- `lib/misc/rounding.py`, `lib/misc/types.py`, `lib/helpers/graceful_killer.py`
- `services/datapipe-et/main.py`, `services/qdb-backup/script.py`, `services/orderbook-syncer/dump-orderbooks.sh`, `services/datapipe-streams-conf-generator/script.py`, `services/grafana/start.sh`, `services/{sentry,1password-connect-server}/README.md`

## Key Files for Context
- `README.md` - the rewritten file
- The existing Archival Notes paragraph in the prior README was used as raw material

## Next Steps
- None. One-shot README polish.
