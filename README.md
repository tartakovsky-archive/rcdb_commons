# rcdb_commons

Cloned and published from hcmc-project/rcdb_commons for archival purposes.

---

## Archival Notes

rcdb_commons is a shared Python library that provided the data and configuration backbone for the RCDB automated trading infrastructure. It defines a unified client layer for three internal services — a time-series data store (accepting OHLCV, Kalman-filtered signals, bot performance metrics, and account trade logs via a REST API), a centralized configuration store that serves validated bot strategy configs (entry/exit grid parameters, position sizing, borrowing rules, exchange credentials), and a credential vault. The schema layer is built on Pydantic, enforcing strict type contracts across the system: `ExchangeCredentials`, `BotConfig`, `Symbol`, `AccountType`, and dozens of configuration variants ensure that every component — from the research notebooks to the production execution engine — speaks the same language.

The library also packages operational tooling: a datapipe service for streaming market data from multiple exchanges into the central store, an orderbook syncer for real-time depth snapshots, Grafana provisioning for monitoring dashboards, QDB backup scripts, and Sentry integration for error tracking. The architectural pattern throughout is dependency injection via API URLs and tokens rather than hard imports, allowing each service to be deployed independently while the commons library provides the shared type definitions and client SDKs. This code was developed as part of the RCDB team's work on a multi-exchange, multi-strategy automated trading platform, later merged into 3Jane Technologies (https://github.com/3jane).