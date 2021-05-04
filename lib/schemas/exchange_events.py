from enum import Enum


class ExchangeEvents(Enum):
    TRADE = "TRADE"
    ORDER_FILL = "ORDER_FILL"
    ORDERBOOK = "ORDERBOOK"
    TICKER = "TICKER"
    BALANCE = "BALANCE"


class BinanceStreams(Enum):
    TRADES = "TRADES"
    ORDERBOOK = "ORDERBOOK"
    ORDER_FILL = "ORDER_FILL"
    BALANCE = "BALANCE"
    TICKER = "TICKER"
