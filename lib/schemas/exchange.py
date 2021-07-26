import decimal
from enum import Enum
from decimal import Decimal

from pydantic import BaseModel
from pydantic.typing import Literal, List, Tuple, Dict, Union


class Exchange(Enum):
    binance = "binance"
    kraken = "kraken"
    okex = "okex"


class SymbolEmpty(BaseModel):
    base: Literal['EMPTY'] = 'EMPTY'
    quote: Literal['EMPTY'] = 'EMPTY'


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
    symbol: Symbol
    exchange: Exchange
    type: AccountType

    amount_precision: int
    price_precision: int
    order_amount_max: Decimal
    order_cost_min: Decimal

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


OrderbookLevelTuple = Tuple[Decimal, Decimal]


class OrderbookLevel(OrderbookLevelTuple):
    @property
    def price(self) -> Decimal:
        return self[0]

    @property
    def amount(self) -> Decimal:
        return self[1]


# class AssetBalance(BaseModel):
#     base: Decimal
#     quote: Decimal
#     base_net: Decimal
#     quote_net: Decimal
#     quote_borrowed: Decimal
#     base_borrowed: Decimal


class AssetSpotBalance(BaseModel):
    name: str
    free: Decimal
    locked: Decimal
    total: Decimal


class AssetMarginBalance(BaseModel):
    name: str
    free: Decimal
    locked: Decimal
    total: Decimal
    borrowed: Decimal
    interest: Decimal
    net: Decimal


class AssetFutureBalance(BaseModel):
    name: str
    wallet_balance: Decimal
    unrealized_profit: Decimal
    margin_balance: Decimal
    margin_maintain: Decimal
    margin_initial: Decimal
    cross_wallet_balance: Decimal
    crossUnPnl: Decimal
    available_balance: Decimal


class PositionSide(Enum):
    BOTH: "BOTH"
    LONG: "LONG"
    SHORT: "SHORT"


class Position(BaseModel):
    symbol: Symbol
    margin_initial: Decimal
    margin_maintain: Decimal
    unrealized_profit: Decimal
    position_initial_margin: Decimal
    leverage: Decimal
    isolated: bool
    price_entry: Decimal
    notional: Decimal
    notional_max: Decimal
    position_side: PositionSide
    amount: Decimal
    isolated_wallet: bool


class AccountBalance(BaseModel):
    type: AccountType
    balances: Dict[str, Union[AssetMarginBalance, AssetSpotBalance]]  # {"USDT": AssetXXXBalance}

    def __getitem__(self, key):
        try:
            return self.balances[key]
        except KeyError:
            if self.type == AccountType.SPOT:
                return AssetSpotBalance(
                    name=key, free=Decimal("0.0"), locked=Decimal("0.0"), total=Decimal("0.0"))
            elif self.type == AccountType.CROSS_MARGIN:
                return AssetMarginBalance(
                    name=key, free=Decimal("0.0"), locked=Decimal("0.0"), total=Decimal("0.0"),
                    borrowed=Decimal("0.0"), interest=Decimal("0.0"), net=Decimal("0.0"))

    def __iter__(self):
        for item in self.balances.items():
            yield item


class OrderbookSpread(BaseModel):
    bid: OrderbookLevel
    ask: OrderbookLevel


class OrderBook(BaseModel):
    bids: List[OrderbookLevel]
    asks: List[OrderbookLevel]

    @property
    def bid_best(self) -> Decimal:
        return self.bids[0][0]

    @property
    def ask_best(self) -> Decimal:
        return self.asks[0][0]

    def bid_ask_no_dust(self, dust_amount: Decimal = Decimal('0.0')) -> (OrderbookLevel, OrderbookLevel):
        bid_price: Decimal = None
        bid_vol: Decimal = Decimal("0.0")
        for lvl in self.bids:
            bid_vol += lvl.amount
            if bid_vol > dust_amount:
                bid_price = lvl.price
                break

        ask_price = None
        ask_vol = Decimal("0.0")
        for lvl in self.asks:
            ask_vol += lvl.amount
            if ask_vol > dust_amount:
                ask_price = lvl.price
                break

        return OrderbookLevel((bid_price, bid_vol)), OrderbookLevel((ask_price, ask_vol))

    def price_bid_ask_no_dust(self, dust_amount: Decimal = Decimal('0.0')) -> (Decimal, Decimal):
        bid, ask = self.bid_ask_no_dust(dust_amount)
        return bid.price, ask.price


class Trade(BaseModel):
    symbol: Symbol
    side: OrderSide
    price: Decimal
    amount: Decimal


class Ticker(BaseModel):
    symbol: Symbol
    bid: Decimal
    ask: Decimal


class Order(BaseModel):
    id_client: str  # = Field(default_factory=lambda: str(uuid4()))
    id_exchange: str = None
    timestamp: int = None
    instrument: Instrument
    type: OrderType
    status: OrderStatus = OrderStatus.SCHEDULED
    side: OrderSide
    price: Decimal  # order price
    amount: Decimal  # order quantity
    amount_filled: Decimal = Decimal('0.00000000')
    amount_filled_latest: Decimal = Decimal('0.00000000')

    def get_filled_pct(self) -> Decimal:
        return self.amount_filled_latest / self.amount_filled

    @staticmethod
    def to_precision(value: Decimal, precision: int) -> Decimal:
        v = value.quantize(Decimal("1." + "0" * precision), rounding=decimal.ROUND_DOWN)
        return v

    @property
    def price_to_precision(self) -> Decimal:
        return self.to_precision(self.price, self.instrument.price_precision)

    @property
    def amount_to_precision(self) -> Decimal:
        return self.to_precision(self.amount, self.instrument.amount_precision)


class TransferType(Enum):
    MAIN_C2C = 'MAIN_C2C'
    MAIN_UMFUTURE = 'MAIN_UMFUTURE'
    MAIN_CMFUTURE = 'MAIN_CMFUTURE'
    MAIN_MARGIN = 'MAIN_MARGIN'
    MAIN_MINING = 'MAIN_MINING'
    C2C_MAIN = 'C2C_MAIN'
    C2C_UMFUTURE = 'C2C_UMFUTURE'
    C2C_MARGIN = 'C2C_MARGIN'
    UMFUTURE_MAIN = 'UMFUTURE_MAIN'
    UMFUTURE_C2C = 'UMFUTURE_C2C'
    UMFUTURE_MARGIN = 'UMFUTURE_MARGIN'
    CMFUTURE_MAIN = 'CMFUTURE_MAIN'
    CMFUTURE_MARGIN = 'CMFUTURE_MARGIN'
    MARGIN_MAIN = 'MARGIN_MAIN'
    MARGIN_UMFUTURE = 'MARGIN_UMFUTURE'
    MARGIN_CMFUTURE = 'MARGIN_CMFUTURE'
    MARGIN_MINING = 'MARGIN_MINING'
    MARGIN_C2C = 'MARGIN_C2C'
    MINING_MAIN = 'MINING_MAIN'
    MINING_UMFUTURE = 'MINING_UMFUTURE'
    MINING_C2C = 'MINING_C2C'
    MINING_MARGIN = 'MINING_MARGIN'
    MAIN_PAY = 'MAIN_PAY'
    PAY_MAIN = 'PAY_MAIN'
    MAIN_DEPOSIT = 'MAIN_DEPOSIT'
    MAIN_WITHDRAWAL = 'MAIN_WITHDRAWAL'

    @classmethod
    def external_transfers(cls) -> set:
        return {cls.MAIN_DEPOSIT, cls.MAIN_WITHDRAWAL}
