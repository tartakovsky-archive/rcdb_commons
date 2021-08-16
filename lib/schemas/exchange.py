import time
from enum import Enum
from decimal import Decimal

from pydantic import BaseModel, validator, condecimal
from pydantic.typing import List, Dict, Union

from rcdb_commons.lib.misc.rounding import to_precision


class Exchange(Enum):
    empty = "EMPTY"

    binance = "binance"
    binanceusdm = "binanceusdm"
    binancecoinm = "binancecoinm"
    ascendex = "ascendex"

    kraken = "kraken"
    okex = "okex"


# class SymbolEmpty(BaseModel):
#     base: Literal['EMPTY'] = 'EMPTY'
#     quote: Literal['EMPTY'] = 'EMPTY'


class Symbol(BaseModel):
    base: str
    quote: str

    @classmethod
    def from_ccxt(cls, symbol_str):
        [base, quote] = symbol_str.split("/")
        return cls(base=base, quote=quote)

    @classmethod
    def from_binance(cls, symbol_str):
        base, quote = symbol_str[0:3], symbol_str[3:]
        return cls(base=base, quote=quote)

    def to_ccxt(self):
        return f"{self.base}/{self.quote}"

    def to_binance(self):
        return f"{self.base}{self.quote}"


class SymbolExtras(BaseModel):
    name_binance: str


class SymbolFutures(BaseModel):
    name: str
    extras: Union[str, SymbolExtras] = None

    @classmethod
    def from_ccxt(cls, symbol_str):
        return cls(name=symbol_str)

    # @classmethod
    # def from_binance(cls, symbol_str):
    #     return cls(name=symbol_str)

    def to_ccxt(self):
        return self.name

    def to_binance(self):
        try:
            return self.extras.name_binance
        except AttributeError:
            self.extras = SymbolExtras(name_binance=self.name.replace("/", ""))

        return self.extras.name_binance


SYMBOL_EMPTY = Symbol(base="EMPTY", quote="EMPTY")
SymbolAny = Union[Symbol, SymbolFutures]


class AccountType(Enum):
    SPOT = 'SPOT'
    CROSS_MARGIN = 'CROSS_MARGIN'
    ISOLATED_MARGIN = 'ISOLATED_MARGIN'
    USDT_M_FUTURES = 'USDT_M_FUTURES'
    COIN_M_FUTURES = 'COIN_M_FUTURES'

    @property
    def label(self) -> str:
        return self.labels()[self]

    @classmethod
    def labels(cls) -> dict:
        return {
            cls.SPOT: 'Spot',
            cls.CROSS_MARGIN: 'Cross Margin',
            cls.ISOLATED_MARGIN: 'Isolated Margin',
            cls.USDT_M_FUTURES: 'USDT-M Futures',
            cls.COIN_M_FUTURES: 'COIN-M Futures'
        }

    @classmethod
    def choices(cls, use_value: bool = True) -> List[tuple]:
        labels = cls.labels().items()
        if use_value:
            labels = map(lambda choice: (choice[0].value, choice[1]), labels)
        return list(labels)


class Instrument(BaseModel):
    symbol: SymbolAny
    exchange: Exchange
    type: AccountType

    amount_precision: int
    price_precision: int
    order_amount_max: Decimal
    order_cost_min: Decimal

    order_notional_min: Decimal = Decimal("0.0")
    order_notional_max: Decimal = Decimal("0.0")

    @property
    def price_tick(self):
        return Decimal("0.1") ** self.price_precision

    @property
    def amount_tick(self):
        return Decimal("0.1") ** self.amount_precision

    @property
    def is_spot(self):
        return self.type == AccountType.SPOT

    @property
    def is_margin(self):
        return self.type == AccountType.CROSS_MARGIN

    @property
    def is_futures(self):
        return self.type in {AccountType.COIN_M_FUTURES, AccountType.USDT_M_FUTURES}

    def to_ccxt(self):
        return self.symbol.to_ccxt()

    def to_binance(self):
        return self.symbol.to_binance()


class FuturesFundingRate(BaseModel):
    instrument: Instrument
    market_price: Decimal
    index_price: Decimal
    funding_rate: Decimal
    interest_rate: Decimal
    next_funding_time: int


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    LIMIT_MAKER = "LIMIT_MAKER"


class OrderStatus(Enum):
    # created but not yet sent to exchange
    SCHEDULED = "SCHEDULED"
    # registered on exchange (response after `create_order` api call)
    NEW = "NEW"
    # placed inside orderbook
    OPEN = "OPEN"
    # CANCEL operation scheduled inside strategy
    CANCELING = "CANCELING"
    # order canceled on exchange
    CANCELED = "CANCELED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    ERROR = "ERROR"


# OrderbookLevelTuple = Tuple[Decimal, Decimal]


class OrderbookLevel:
    def __init__(self, price, amount):
        self.price = price
        self.amount = amount


# class AssetBalance(BaseModel):
#     base: Decimal
#     quote: Decimal
#     base_net: Decimal
#     quote_net: Decimal
#     quote_borrowed: Decimal
#     base_borrowed: Decimal


def gte(name: str) -> str:
    return ' '.join((word.capitalize()) for word in name.split(' '))


class AssetSpotBalance(BaseModel):
    name: str
    free: condecimal(ge=Decimal("0.0"))
    locked: condecimal(ge=Decimal("0.0"))
    total: Decimal


class CapitalBalance(BaseModel):
    base: condecimal(ge=Decimal("0.0"))
    quote: condecimal(ge=Decimal("0.0"))


class CapitalParts(BaseModel):
    quote_own: CapitalBalance
    base_own: CapitalBalance
    quote_borrowed: CapitalBalance
    base_borrowed: CapitalBalance


class AssetMarginBalance(AssetSpotBalance):
    borrowed: Decimal
    interest: Decimal
    net: Decimal


class AssetFuturesBalance(AssetSpotBalance):
    pass
    # name: str
    # wallet_balance: Decimal
    # unrealized_profit: Decimal
    # margin_balance: Decimal
    # margin_maintain: Decimal
    # margin_initial: Decimal
    # cross_wallet_balance: Decimal
    # crossUnPnl: Decimal
    # available_balance: Decimal


class PositionSide(Enum):
    BOTH = "BOTH"
    LONG = "LONG"
    SHORT = "SHORT"


class Position(BaseModel):
    # symbol = pos['symbol'],
    # amount = pos['positionAmt'],
    # price_entry = pos['entryPrice'],
    # unrealized_profit = pos['unrealizedProfit'],
    # position_side = pos['positionSide'],
    # isolated = pos['isolatedWallet']
    symbol: SymbolFutures
    # margin_initial: Decimal = None
    # margin_maintain: Decimal = None
    unrealized_profit: Decimal = None
    # position_initial_margin: Decimal = None
    # leverage: Decimal = None
    # isolated: bool = False
    price_entry: Decimal = None
    # notional: Decimal = None
    # notional_max: Decimal = None
    position_side: PositionSide = None
    amount: Decimal = Decimal("0.0")
    isolated: bool = False

    timestamp: float = None
    timestamp_local: float = None

    has_pending_events: bool = False
    wait_update_since: float = None

    def refresh_required(self):
        self.has_pending_events = True
        self.wait_update_since = time.time() * 1000

    # class Config:
    #     allow_population_by_alias = True
    #     fields = {
    #         'margin_initial': 'initialMargin',
    #         'margin_maintain': 'maintMargin',
    #         'unrealized_profit': 'unrealizedProfit',
    #         'position_initial_margin': 'positionInitialMargin',
    #         # 'openOrderInitialMargin': '0',
    #         'price_entry': 'entryPrice',
    #         'notional_max': 'maxNotional',
    #         'position_side': 'positionSide',
    #         'amount': 'positionAmt',
    #         'isolated_wallet': 'isolatedWallet',
    #         'timestamp': 'updateTime'
    #     }


AssetBalance = Union[AssetMarginBalance, AssetSpotBalance, AssetFuturesBalance]


class AccountBalance(BaseModel):
    type: AccountType
    balances: Dict[str, AssetBalance]  # {"USDT": AssetXXXBalance}

    def __getitem__(self, key):
        if key.find("/") >= 0:
            return self.get_position(key)
        else:
            return self.get_balance(key)

    def get_position(self, pair_name):
        try:
            return self.positions[pair_name]
        except KeyError:
            return Position(pair_name)

    def get_balance(self, asset_name):
        try:
            return self.balances[asset_name]
        except KeyError:
            if self.type == AccountType.SPOT:
                return AssetSpotBalance(
                    name=asset_name, free=Decimal("0.0"), locked=Decimal("0.0"), total=Decimal("0.0"))
            if self.type == AccountType.USDT_M_FUTURES or self.type == AccountType.COIN_M_FUTURES:
                return AssetFuturesBalance(
                    name=asset_name, free=Decimal("0.0"), locked=Decimal("0.0"), total=Decimal("0.0"))
            elif self.type == AccountType.CROSS_MARGIN:
                return AssetMarginBalance(
                    name=asset_name, free=Decimal("0.0"), locked=Decimal("0.0"), total=Decimal("0.0"),
                    borrowed=Decimal("0.0"), interest=Decimal("0.0"), net=Decimal("0.0"))

    def __iter__(self):
        for item in self.balances.items():
            yield item


class AccountMarginBalance(AccountBalance):
    margin_level: Decimal = Decimal("999.0")


# class OrderbookSpread(BaseModel):
#     bid: OrderbookLevel
#     ask: OrderbookLevel


class Trade(BaseModel):
    symbol: SymbolAny
    side: OrderSide
    price: Decimal
    amount: Decimal
    timestamp: float


class Ticker(BaseModel):
    symbol: SymbolAny
    bid: Decimal
    ask: Decimal


class Order(BaseModel):
    id_client: str = None  # = Field(default_factory=lambda: str(uuid4()))
    id_exchange: str = None
    timestamp: int = None
    instrument: Instrument
    type: OrderType
    status: OrderStatus = OrderStatus.SCHEDULED
    side: OrderSide
    price: Decimal = None  # order price, None for type = IrderType.MARKET
    amount: Decimal  # order quantity
    amount_filled: Decimal = Decimal('0.00000000')
    amount_filled_latest: Decimal = Decimal('0.00000000')

    def get_filled_pct(self) -> Decimal:
        return self.amount_filled_latest / self.amount_filled

    @staticmethod
    def to_precision(value: Decimal, precision: int, round_down=True) -> Decimal:
        return to_precision(value, precision, round_down)

    @property
    def price_to_precision(self, precision: int = None) -> Decimal:
        p = precision if precision is not None else self.instrument.price_precision
        if self.side == OrderSide.BUY:
            return self.to_precision(self.price, p, round_down=True)
        else:
            return self.to_precision(self.price, p, round_down=False)

    @property
    def amount_to_precision(self) -> Decimal:
        return self.to_precision(self.amount, self.instrument.amount_precision, round_down=True)

    @property
    def id(self):
        if self.id_client is not None:
            return self.id_client
        return self.id_exchange


class OrderBook(BaseModel):
    bids: List  # [OrderbookLevel]
    asks: List  # [OrderbookLevel]
    instrument: Instrument
    timestamp: int = None

    skip_status = {
        OrderStatus.ERROR,
        OrderStatus.CANCELED,
        OrderStatus.FILLED,
    }

    @property
    def bid_best(self) -> Decimal:
        return self.bids[0].price

    @property
    def ask_best(self) -> Decimal:
        return self.asks[0].price

    def remove_orders_liquidity(self, orders: List[Order]):
        # print(len(orders))
        for o in orders:
            if o.status not in self.skip_status:
                vol_minus = o.amount - o.amount_filled
                ob_side = self.bids if o.side == OrderSide.BUY else self.asks
                for i in range(len(ob_side)):
                    if ob_side[i].price == o.price:
                        if ob_side[i].amount - vol_minus >= Decimal("0.0"):
                            # if we receive negative amount, probably it's a lag on order cancel
                            ob_side[i].amount -= vol_minus
                            ob_side[i].amount = max(ob_side[i].amount, Decimal(0.0))

    @staticmethod
    def _get_price_no_dust(orderbook_levels, dust_amount, plus_tick):
        # set price as worst possible in orderbook
        price: Decimal = orderbook_levels[-1].price
        vol: Decimal = Decimal("0.0")
        for i in range(len(orderbook_levels)):
            lvl = orderbook_levels[i]
            vol += lvl.amount
            vol_to_dust_ratio = vol / dust_amount
            if vol_to_dust_ratio > 1:
                if vol_to_dust_ratio > 1.8:
                    if i != 0:
                        price = lvl.price + plus_tick
                    else:
                        price = lvl.price
                else:
                    price = lvl.price
                break
        return OrderbookLevel(price=price, amount=vol)

    def bid_ask_no_dust(self,
                        bid_dust_amount: Decimal = Decimal('0.0'),
                        ask_dust_amount: Decimal = Decimal('0.0'),
                        tick_size: Decimal = Decimal('0.0')
                        ) -> (OrderbookLevel, OrderbookLevel):

        return (
            self.bids[0] if bid_dust_amount <= Decimal("0.0") else self._get_price_no_dust(
                self.bids, bid_dust_amount, tick_size),
            self.asks[0] if ask_dust_amount <= Decimal("0.0") else self._get_price_no_dust(
                self.asks, ask_dust_amount, -tick_size)
        )

    def price_bid_ask_no_dust(self,
                              bid_dust_amount: Decimal = Decimal('0.0'),
                              ask_dust_amount: Decimal = Decimal('0.0'),
                              tick_size: Decimal = Decimal('0.0')) -> (Decimal, Decimal):
        bid, ask = self.bid_ask_no_dust(bid_dust_amount, ask_dust_amount, tick_size)
        return bid.price, ask.price