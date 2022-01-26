import time
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel
from pydantic.typing import List, Dict, Union, Literal

from ..misc.rounding import to_precision, Rounder, to_auto_price_precision
from ..misc.types import to_decimal


class Exchange(Enum):
    empty = "EMPTY"

    binance = "binance"
    binanceusdm = "binanceusdm"
    binancecoinm = "binancecoinm"
    binance_swap = "binance_swap"
    binance_public = "binance_public"

    ascendex = "ascendex"
    kraken = "kraken"
    okex = "okex"
    kucoin = "kucoin"
    bybit = "bybit"
    huobi = "huobi"


class AccountType(Enum):
    MAIN = 'MAIN'
    SPOT = 'SPOT'
    SWAP = 'SWAP'
    CROSS_MARGIN = 'CROSS_MARGIN'
    ISOLATED_MARGIN = 'ISOLATED_MARGIN'
    USDT_M_FUTURES = 'USDT_M_FUTURES'
    COIN_M_FUTURES = 'COIN_M_FUTURES'

    # bybit specials
    INVERSE_PERPETUAL = 'INVERSE_PERPETUAL'
    INVERSE_FUTURES = 'INVERSE_FUTURES'

    @property
    def label(self) -> str:
        return self.labels()[self]

    @classmethod
    def labels(cls) -> dict:
        return {
            cls.MAIN: 'Main',
            cls.SPOT: 'Spot',
            cls.SWAP: 'Swap',
            cls.CROSS_MARGIN: 'Cross Margin',
            cls.ISOLATED_MARGIN: 'Isolated Margin',
            cls.USDT_M_FUTURES: 'USDT-M Futures',
            cls.COIN_M_FUTURES: 'COIN-M Futures',
            cls.INVERSE_FUTURES: 'Inverse Futures',
            cls.INVERSE_PERPETUAL: 'Inverse Perpetual'
        }

    @classmethod
    def choices(cls, use_value: bool = True) -> List[tuple]:
        labels = cls.labels().items()
        if use_value:
            labels = map(lambda choice: (choice[0].value, choice[1]), labels)
        return list(labels)

    @property
    def is_spot(self):
        return self == AccountType.SPOT

    @property
    def is_margin(self):
        return self == AccountType.CROSS_MARGIN

    @property
    def is_futures(self):
        return self in {
            AccountType.COIN_M_FUTURES,
            AccountType.USDT_M_FUTURES,
            AccountType.INVERSE_PERPETUAL,
            AccountType.INVERSE_FUTURES,
        }


class ExchangeCredentials(BaseModel):
    exchange: Exchange
    credentials: Union[dict, str]
    type: AccountType

    def is_filled(self) -> bool:
        return isinstance(self.credentials, dict)

    @property
    def is_spot(self):
        return self.type == AccountType.SPOT

    @property
    def is_margin(self):
        return self.type == AccountType.CROSS_MARGIN

    @property
    def is_futures(self):
        return self.type in {AccountType.COIN_M_FUTURES, AccountType.USDT_M_FUTURES}


# EXCHANGE_CREDENTIALS_EMPTY = ExchangeCredentials(exchange="EMPTY", credentials={}, type="EMPTY")


class ExchangeCredentialsEmpty(ExchangeCredentials):
    exchange: Literal['EMPTY'] = 'EMPTY'
    credentials: Union[dict, str] = 'EMPTY'
    type: Literal['EMPTY'] = 'EMPTY'


class Symbol(BaseModel):
    base: str
    quote: str

    #
    # def __init__(self, base, quote):
    #     self.base = base
    #     self.quote = quote

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

    def to_kucoin(self):
        return f"{self.base}-{self.quote}"


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

    def to_kucoin(self):
        return self.name

    def to_binance(self):
        try:
            return self.extras.name_binance
        except AttributeError:
            self.extras = SymbolExtras(name_binance=self.name.replace("/", ""))

        return self.extras.name_binance


SYMBOL_EMPTY = Symbol(base="EMPTY", quote="EMPTY")
SymbolAny = Union[Symbol, SymbolFutures]


class Instrument:
    def __init__(self,
                 symbol: SymbolAny,
                 exchange: Exchange,
                 type: AccountType,

                 amount_precision: int,
                 price_precision: int,
                 order_amount_max: Decimal = None,
                 order_cost_min: Decimal = None,

                 order_notional_min: Decimal = None,
                 order_notional_max: Decimal = None):
        self.symbol: SymbolAny = symbol
        self.exchange: Exchange = exchange
        self.type: AccountType = type

        self.amount_precision: int = self.__to_type__(amount_precision, int)
        self.price_precision: int = self.__to_type__(price_precision, int)
        self.order_amount_max: Decimal = self.__to_type__(order_amount_max, Decimal, nullable=True)
        self.order_cost_min: Decimal = self.__to_type__(order_cost_min, Decimal, nullable=True)

        self.order_notional_min: Decimal = self.__to_type__(order_notional_min, Decimal, nullable=True)
        self.order_notional_max: Decimal = self.__to_type__(order_notional_max, Decimal, nullable=True)

    @staticmethod
    def __to_type__(v, t, nullable=False):
        if not nullable and v is None:
            raise Exception(f"Value `{v}` with type `{t}` can't be None")

        if v is not None and t(v) == t:
            return v

        return t(v) if v is not None else None

    def __dict__(self):
        return [self.exchange.value, self.type.value, self.symbol.to_ccxt()]

    class Config:
        arbitrary_types_allowed = True

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

    def to_kucoin(self):
        return self.symbol.to_kucoin()


# class FuturesFundingRate(BaseModel):
#     instrument: Instrument
#     market_price: Decimal
#     index_price: Decimal
#     funding_rate: Decimal
#     interest_rate: Decimal
#     next_funding_time: int


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


class AssetSpotBalance:
    # name: str
    # free: condecimal(ge=Decimal("0.0"))
    # locked: condecimal(ge=Decimal("0.0"))
    # total: Decimal

    def __init__(self, name, free, locked, total):
        self.name: str = name
        self.free: Decimal = free
        self.locked: Decimal = locked
        self.total: Decimal = total

        assert free >= Decimal("0.0")
        assert locked >= Decimal("0.0")

    def __repr__(self):
        return f'<{type(self).__name__}(name={self.name}, free={self.free}, locked={self.locked}, total={self.total})>'


# class CapitalBalance(BaseModel):
#     base: condecimal(ge=Decimal("0.0"))
#     quote: condecimal(ge=Decimal("0.0"))
#
#
# class CapitalParts(BaseModel):
#     quote_own: CapitalBalance
#     base_own: CapitalBalance
#     quote_borrowed: CapitalBalance
#     base_borrowed: CapitalBalance


class AssetMarginBalance(AssetSpotBalance):
    borrowed: Decimal
    interest: Decimal
    net: Decimal

    def __init__(self, *args, borrowed: Decimal, interest: Decimal, net: Decimal, **kwargs):
        super().__init__(*args, **kwargs)
        self.borrowed: Decimal = borrowed
        self.interest: Decimal = interest
        self.net: Decimal = net


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

    @property
    def base(self):
        zero = Decimal("0.0")
        if self.amount >= zero:
            return AssetMarginBalance(
                free=zero,
                locked=zero,
                total=zero,
                borrowed=zero,
                interest=zero,
                net=zero
            )

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


class Positions(BaseModel):
    positions: Dict[str, Position]
    collateral: Decimal = None

    @property
    def margin_balance(self):
        balance = self.collateral
        for p in self.positions.values():
            balance += p.unrealized_profit

        return balance

    # def __calc_amounts(self, symbol_name):
    #     p = self.position[symbol_name].amount
    #     base = max(Decimal("0.0"), p)
    #     quote = self.margin_balance
    #     return base, quote
    #
    # def base_amount(self, symbol_name):
    #     base, quote = self.__calc_amounts(symbol_name)
    #
    #     return AssetMarginBalance(
    #         name=symbol_name,
    #         free=,
    #         locked=,
    #         total=,
    #         borrowed=,
    #         interest=,
    #         net=)

    def __getitem__(self, item):
        if item in self.positions:
            return self.positions[item]
        else:
            return Position(
                symbol=SymbolFutures(name=item),
                unrealized_profit=Decimal("0.0"),
                amount=Decimal("0.0")
            )

    def __setitem__(self, key, value):
        self.positions[key] = value

    def __contains__(self, item):
        return item in self.positions


AssetBalance = Union[AssetMarginBalance, AssetSpotBalance, AssetFuturesBalance]


class AccountBalance:
    # type: AccountType
    # balances: Dict[str, AssetBalance]  # {"USDT": AssetXXXBalance}

    def __init__(self, type: AccountType, balances: Dict[str, AssetBalance]):
        self.type = type
        self.balances = balances

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


class Trade:
    # symbol: SymbolAny
    # side: OrderSide
    # price: Decimal
    # amount: Decimal
    # timestamp: float

    def __init__(self, symbol: SymbolAny,
                 side: OrderSide,
                 price: Decimal,
                 amount: Decimal,
                 timestamp: float):
        self.symbol: SymbolAny = symbol
        self.side: OrderSide = side
        self.price: Decimal = price
        self.amount: Decimal = amount
        self.timestamp: float = timestamp


class Ticker:
    # symbol: SymbolAny
    # bid: Decimal
    # ask: Decimal

    def __init__(self, symbol: SymbolAny, bid: Decimal, ask: Decimal):
        self.symbol = symbol
        self.bid = bid


class Order:
    def __init__(self,
                 instrument: Instrument,
                 order_type: OrderType,
                 side: OrderSide,
                 amount: Decimal,
                 amount_filled: Decimal = Decimal('0.00000000'),
                 amount_filled_latest: Decimal = Decimal('0.00000000'),
                 status: OrderStatus = OrderStatus.SCHEDULED,
                 id_client: str = None,
                 id_exchange: str = None,
                 price: Decimal = None,
                 timestamp: int = None):
        """

        Returns
        -------
        object
        """
        self.id_client: str = id_client  # = Field(default_factory=lambda: str(uuid4()))
        self.id_exchange: str = id_exchange
        self.timestamp: int = timestamp
        self.instrument: Instrument = instrument
        if type(self.instrument) != Instrument:
            raise Exception("type(self.instrument) != Instrument")
        self.type: OrderType = order_type if type(order_type) == OrderType else OrderType(order_type)
        self.status: OrderStatus = status if type(status) == OrderStatus else OrderStatus(status.upper())
        self.side: OrderSide = side if type(side) == OrderSide else OrderSide(side.upper())
        self.price: Decimal = to_decimal(price)
        self.amount: Decimal = to_decimal(amount)
        self.amount_filled: Decimal = to_decimal(amount_filled)
        self.amount_filled_latest: Decimal = to_decimal(amount_filled_latest)

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

    def dict(self):
        return dict(
            id_client=self.id_client,
            id_exchange=self.id_exchange,
            timestamp=self.timestamp,
            instrument=self.instrument,
            type=self.type,
            status=self.status,
            side=self.side,
            price=self.price,
            amount=self.amount,
            amount_filled=self.amount_filled,
            amount_filled_latest=self.amount_filled_latest
        )


class OrderBook:
    bids: List  # [OrderbookLevel]
    asks: List  # [OrderbookLevel]
    instrument: Instrument
    timestamp: float = None

    skip_status = {
        OrderStatus.ERROR,
        OrderStatus.CANCELED,
        OrderStatus.FILLED,
    }

    def __init__(self, bids, asks, instrument, timestamp):
        self.bids = bids
        self.asks = asks
        self.instrument = instrument
        self.timestamp = timestamp

    @property
    def __dict__(self):
        return {
            "b": str(to_auto_price_precision(self.bids[0].price, Rounder.ROUND_DOWN)),
            "b_a": str(self.bids[0].amount),
            "a": str(to_auto_price_precision(self.asks[0].price, Rounder.ROUND_UP)),
            "a_a": str(self.asks[0].amount),
            "ts_e": self.timestamp,
            "ts_l": self.timestamp,
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
                price = lvl.price
                # if vol_to_dust_ratio > 1.8:
                #     if i != 0:
                #         price = lvl.price + plus_tick
                #     else:
                #         price = lvl.price
                # else:
                #     price = lvl.price
                break
        return OrderbookLevel(price=price, amount=vol)

    def bid_ask_no_dust(self,
                        bid_dust_amount: Decimal = Decimal('0.0'),
                        ask_dust_amount: Decimal = Decimal('0.0'),
                        tick_size: Decimal = Decimal('0.0')
                        ) -> (OrderbookLevel, OrderbookLevel):

        # print("---")
        # for l in reversed(self.asks[0:20]):
        #     print(">   ", l.price, l.amount)
        # print(self.asks[0].price, self._get_price_no_dust(self.asks, ask_dust_amount, -tick_size).price)
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


class TransferType(Enum):
    MAIN_UMFUTURE = 'MAIN_UMFUTURE'
    MAIN_CMFUTURE = 'MAIN_CMFUTURE'
    MAIN_MARGIN = 'MAIN_MARGIN'
    MAIN_MINING = 'MAIN_MINING'
    UMFUTURE_MAIN = 'UMFUTURE_MAIN'
    UMFUTURE_MARGIN = 'UMFUTURE_MARGIN'
    CMFUTURE_MAIN = 'CMFUTURE_MAIN'
    CMFUTURE_MARGIN = 'CMFUTURE_MARGIN'
    MARGIN_MAIN = 'MARGIN_MAIN'
    MARGIN_UMFUTURE = 'MARGIN_UMFUTURE'
    MARGIN_CMFUTURE = 'MARGIN_CMFUTURE'
    MARGIN_MINING = 'MARGIN_MINING'
    MINING_MAIN = 'MINING_MAIN'
    MINING_UMFUTURE = 'MINING_UMFUTURE'
    MINING_MARGIN = 'MINING_MARGIN'
    MAIN_DEPOSIT = 'MAIN_DEPOSIT'
    MAIN_WITHDRAWAL = 'MAIN_WITHDRAWAL'
    UMFUTURE_DEPOSIT = 'UMFUTURE_DEPOSIT'
    UMFUTURE_WITHDRAWAL = 'UMFUTURE_WITHDRAWAL'
    CMFUTURE_DEPOSIT = 'CMFUTURE_DEPOSIT'
    CMFUTURE_WITHDRAWAL = 'CMFUTURE_WITHDRAWAL'
    MAIN_FUNDING = 'MAIN_FUNDING'
    FUNDING_MAIN = 'FUNDING_MAIN'
    FUNDING_UMFUTURE = 'FUNDING_UMFUTURE'
    UMFUTURE_FUNDING = 'UMFUTURE_FUNDING'
    MARGIN_FUNDING = 'MARGIN_FUNDING'
    FUNDING_MARGIN = 'FUNDING_MARGIN'
    FUNDING_CMFUTURE = 'FUNDING_CMFUTURE'
    CMFUTURE_FUNDING = 'CMFUTURE_FUNDING'

    @classmethod
    def external_transfers(cls) -> set:
        return {cls.MAIN_DEPOSIT, cls.MAIN_WITHDRAWAL}

    @classmethod
    def sub_accounts_transfers(cls) -> set:
        return {cls.UMFUTURE_DEPOSIT, cls.UMFUTURE_WITHDRAWAL, cls.CMFUTURE_DEPOSIT, cls.CMFUTURE_WITHDRAWAL}
