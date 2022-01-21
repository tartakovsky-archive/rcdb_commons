from decimal import Decimal

from pydantic import BaseModel, Field, constr, root_validator
from pydantic.typing import Optional, Literal, Union, List

from .exchange import Symbol, SymbolFutures, SYMBOL_EMPTY, OrderType, ExchangeCredentials, \
    ExchangeCredentialsEmpty


class BorrowingConfig(BaseModel):
    is_base_borrow_enabled: bool = False
    base_amount_max: Decimal = Decimal("0.0")
    base_borrow_level_pct: Decimal = Decimal("0.0")
    base_repay_level_pct: Decimal = Decimal("0.0")

    is_quote_borrow_enabled: bool = False
    quote_amount_max: Decimal = Decimal("0.0")
    quote_borrow_level_pct: Decimal = Decimal("0.0")
    quote_repay_level_pct: Decimal = Decimal("0.0")

    margin_level_max: Decimal = Decimal("1.5")


class DatastoreConfig(BaseModel):
    api_url: str
    token: str


class OrderGridConfig(BaseModel):
    entry_start: float = 0.0
    entry_end: float = 0.0
    entry_levels: int = 0

    exit_start: float = 0.0
    exit_end: float = 0.0
    exit_levels: int = 0

    is_std_channels_enabled: bool = False
    std_channels_mult_min: float = None
    std_channels_mult_max: float = None


class BidAskLevelsConfig(BaseModel):
    bid_start: float
    bid_end: float
    bid_levels: int

    ask_start: float
    ask_end: float
    ask_levels: float


class LongOrderGridConfig(OrderGridConfig):
    def get_bid_ask_channel(self) -> BidAskLevelsConfig:
        return BidAskLevelsConfig(
            bid_start=self.entry_start,
            bid_end=self.entry_end,
            bid_levels=self.entry_levels,

            ask_start=self.exit_start,
            ask_end=self.exit_end,
            ask_levels=self.exit_levels,
        )


class ShortOrderGridConfig(OrderGridConfig):
    def get_bid_ask_channel(self) -> BidAskLevelsConfig:
        return BidAskLevelsConfig(
            ask_start=self.entry_start,
            ask_end=self.entry_end,
            ask_levels=self.entry_levels,

            bid_start=self.exit_start,
            bid_end=self.exit_end,
            bid_levels=self.exit_levels,
        )


class OrderConfig(BaseModel):
    min_fill_to_replace_pct: float = 0.9
    price_merge_step_pct: float = 0.0005
    price_replace_tolerance_pct: float = 0.0001


class PiranhaConfig(BaseModel):
    order_limit: float = None
    wall_distance: float = None


##########################################
# Schema mixins
##########################################

# class EmptyExchangeCredentialsMixin(BaseModel):
#     exchange_credentials: Union[ExchangeCredentialsEmpty, ExchangeCredentials] = ExchangeCredentialsEmpty()
#
#
# class EmptySymbolMixin(BaseModel):
#     symbol: Union[SymbolEmpty, Symbol] = SymbolEmpty()
#
#
# class EmptySymbolExchangeCredentialsMixin(EmptySymbolMixin, EmptyExchangeCredentialsMixin):
#     pass


##########################################
# Bot Configs
##########################################


# class BotBaseConfig(BaseModel):
#     debug: bool = False
#     frequency_seconds: int = 2
#     borrowing: BorrowingConfig = Field(default_factory=BorrowingConfig)


##########################################
# Bot default Kalman config
##########################################


class BotDefaultConfig(BaseModel):
    piranha: PiranhaConfig = Field(default_factory=PiranhaConfig)
    order_config: OrderConfig = Field(default_factory=OrderConfig)


class OwnLongBotConfig(BotDefaultConfig):
    config_type: Literal['OwnLongBotConfig'] = 'OwnLongBotConfig'

    quote_own: LongOrderGridConfig = Field(default_factory=LongOrderGridConfig)
    base_brw: ShortOrderGridConfig = Field(default_factory=ShortOrderGridConfig)
    quote_brw: LongOrderGridConfig = Field(default_factory=LongOrderGridConfig)


class OwnShortBotConfig(BotDefaultConfig):
    config_type: Literal['OwnShortBotConfig'] = 'OwnShortBotConfig'

    base_own: ShortOrderGridConfig = Field(default_factory=LongOrderGridConfig)
    base_brw: ShortOrderGridConfig = Field(default_factory=ShortOrderGridConfig)
    quote_brw: LongOrderGridConfig = Field(default_factory=LongOrderGridConfig)


##########################################
# MarketMakingÁ
##########################################

class BaseOneAssetConfig(BaseModel):
    exchange_credentials: Union[ExchangeCredentialsEmpty, ExchangeCredentials] = ExchangeCredentialsEmpty()
    borrow_config: BorrowingConfig = BorrowingConfig()

    process_step_frequency_sec: float = 0.5

    symbol: Symbol = SYMBOL_EMPTY
    order_replace_frequency: float = 0.0
    price_change_tolerance: Decimal = Decimal("0.0")

    bid_dust_amount: Decimal = Decimal("0.0")
    ask_dust_amount: Decimal = Decimal("0.0")
    auto_remove_liquidity: bool = False

    balance_base_reserved: Decimal = Decimal("0.0")
    balance_quote_reserved: Decimal = Decimal("0.0")

    balance_base_reserved: Decimal = Decimal("0.0")
    balance_quote_reserved: Decimal = Decimal("0.0")

    order_amount_fraction: Decimal = Decimal("0.25")
    jump_above_best_price: bool = False
    spread_force_tighten: bool = False
    force_execute_level_amount: Decimal = Decimal("-1.0")

    bid_buyout_level_amount: Decimal = Decimal("0.0")
    ask_buyout_level_amount: Decimal = Decimal("0.0")

    quote_allowed_limit: Decimal = None
    base_allowed_amount__enabled: bool = False
    quote_allowed_amount__enabled: bool = True

    order_hard_limit_interval: int = 10
    order_hard_limit_count: int = 50
    stats_file: str = None
    disable_trading_on_slow_connection: bool = False
    remove_orders_liquidity: bool = False
    optimize_order_price: bool = False
    order_type: OrderType = OrderType.LIMIT_MAKER

    cancel_orders_on_start_stop: bool = True
    cancel_delay_sec: float = None

    class Config:
        arbitrary_types_allowed = True


class BaseOneAssetFuturesConfig(BaseOneAssetConfig):
    symbol: SymbolFutures
    leverage: int = 1
    # collateral_asset: str


class BSwapSellConfig(BaseOneAssetConfig):
    config_type: Literal['BSwapSellConfig'] = 'BSwapSellConfig'
    asset_to_contract_map: dict


class PureMarketMakingConfig(BaseOneAssetConfig):
    config_type: Literal['PureMarketMakingConfig'] = 'PureMarketMakingConfig'

    bid_spread: Decimal = Decimal("0.0")
    ask_spread: Decimal = Decimal("0.0")

    minimum_spread: Decimal = Decimal("0.0")

    order_amount_max: Decimal = None
    order_amount_divider = Decimal("10.0")
    order_amount_min: Decimal = Decimal("0.0")

    order_amount_fraction: Decimal
    add_liquidity_when_available: bool = True
    replace_on_insufficient_funds: bool = False
    ensure_limit_price: bool = True

    bid_levels: int = 1
    ask_levels: int = 1

    cross_spread: bool = False
    cross_spread__pct_min: float = 0.01
    cross_spread__pct_max: float = 0.05
    cross_spread__jump_when_skewed: bool = True
    cross_spread__ts_freq: float = 10.0
    cross_spread__ob_vs_own_liquidity_ratio: Decimal = Decimal("2.0")


class PureMarketMakingExternalPriceZMQConfig(PureMarketMakingConfig):
    config_type: Literal['PureMarketMakingExternalPriceZMQConfig'] = 'PureMarketMakingExternalPriceZMQConfig'
    stream_price_external: List[str]


class GridConfig(PureMarketMakingConfig):
    config_type: Literal['GridConfig'] = 'GridConfig'
    add_liquidity_when_available: bool = False

    order_amount: Decimal
    bid_levels_spread: Decimal = None
    ask_levels_spread: Decimal = None


class StatArbKalmanConfig(PureMarketMakingConfig):
    config_type: Literal['StatArbKalmanConfig'] = 'StatArbKalmanConfig'
    stream_kalman: List
    stream_maker: List
    stream_taker: List
    stream_cross: List
    is_cross_reversed: bool = False


class PureMarketMakingSpikeFilterConfig(PureMarketMakingConfig):
    config_type: Literal['PureMarketMakingSpikeFilterConfig'] = 'PureMarketMakingSpikeFilterConfig'

    price_history_interval_sec: int = 60
    enable_high_low_spread_pct: Decimal = None
    adjust_spread_pct: Decimal = None

    trend_history_interval_sec: int = None
    bid_spread_down_trend: Decimal = None
    ask_spread_up_trend: Decimal = None
    trend_ticks_gte: int = None
    trend_ticks_pct: Decimal = None


class PureMarketMakingFuturesConfig(PureMarketMakingConfig):
    config_type: Literal['PureMarketMakingFuturesConfig'] = 'PureMarketMakingFuturesConfig'

    symbol: SymbolFutures
    leverage: int = 1

    # bid_spread: Decimal = Decimal("0.0")
    # ask_spread: Decimal = Decimal("0.0")
    #
    # minimum_spread: Decimal = Decimal("0.0")
    #
    # order_amount_max: Decimal = Decimal("0.0")
    # order_amount_divider = Decimal("10.0")
    # order_amount_min: Decimal = Decimal("0.0")
    #
    # order_amount_fraction: Decimal
    # ensure_limit_price: bool = True
    #
    # bid_levels: int = 1
    # ask_levels: int = 1


class OrderBookCollectorSpotConfig(BaseModel):
    config_type: Literal['OrderBookCollectorSpotConfig'] = 'OrderBookCollectorSpotConfig'

    exchange_credentials: Union[ExchangeCredentialsEmpty, ExchangeCredentials] = ExchangeCredentialsEmpty()
    data_collect_directory: str
    symbols: List[Symbol]

    class Config:
        arbitrary_types_allowed = True


class OrderBookCollectorFuturesConfig(BaseModel):
    config_type: Literal['OrderBookCollectorFuturesConfig'] = 'OrderBookCollectorFuturesConfig'

    exchange_credentials: Union[ExchangeCredentialsEmpty, ExchangeCredentials] = ExchangeCredentialsEmpty()
    data_collect_directory: str
    symbols: List[SymbolFutures]


class CrossExchangeMarketMakingFuturesConfig(PureMarketMakingFuturesConfig):
    config_type: Literal['CrossExchangeMarketMakingFuturesConfig'] = 'CrossExchangeMarketMakingFuturesConfig'
    exchange_credentials_cross: Union[ExchangeCredentialsEmpty, ExchangeCredentials] = ExchangeCredentialsEmpty()
    symbol_cross: SymbolFutures

    bid_dust_amount_cross: Decimal = Decimal("0.0")
    ask_dust_amount_cross: Decimal = Decimal("0.0")


class HedgeSpotTask(BaseModel):
    asset__hedge_target: str
    symbol: SymbolFutures


class HedgeSpotTasks(BaseModel):
    exchange_credentials: Union[ExchangeCredentialsEmpty, ExchangeCredentials] = ExchangeCredentialsEmpty()
    tasks: List[HedgeSpotTask]


class SpotToFuturesHedgingConfig(PureMarketMakingFuturesConfig):
    config_type: Literal['SpotToFuturesHedgingConfig'] = 'SpotToFuturesHedgingConfig'
    hedge_accounts: List[HedgeSpotTasks]
    atomic_hedge__order_max_cost: Decimal = Decimal("100.0")


class FuturesToFuturesHedgingConfig(SpotToFuturesHedgingConfig):
    config_type: Literal['FuturesToFuturesHedgingConfig'] = 'FuturesToFuturesHedgingConfig'
    exchange_credentials_hedge: Union[ExchangeCredentialsEmpty, ExchangeCredentials] = ExchangeCredentialsEmpty()
    # symbol_hedge: SymbolFutures


class TrendFollowingMakingConfig(PureMarketMakingConfig):
    config_type: Literal['TrendFollowingMakingConfig'] = 'TrendFollowingMakingConfig'
    sma_slow_len: int
    sma_fast_len: int
    sma_timeframe_sec: float
    sma_price_change_sec: float


class TrendFollowingMakingFuturesConfig(PureMarketMakingFuturesConfig):
    config_type: Literal['TrendFollowingMakingFuturesConfig'] = 'TrendFollowingMakingFuturesConfig'
    sma_slow_len: int
    sma_fast_len: int
    sma_timeframe_sec: float
    sma_price_change_sec: float
    symbol: SymbolFutures


class TrendFilterMarketMakingConfig(PureMarketMakingConfig):
    config_type: Literal['TrendFilterMarketMakingConfig'] = 'TrendFilterMarketMakingConfig'
    kalman_slow_label: str
    kalman_fast_label: str


class PureMarketMakingExternalPriceConfig(PureMarketMakingConfig):
    config_type: Literal['PureMarketMakingExternalPriceConfig'] = 'PureMarketMakingExternalPriceConfig'

    exchange_external_credentials: Union[ExchangeCredentialsEmpty, ExchangeCredentials] = ExchangeCredentialsEmpty()
    symbol_external: Symbol = SYMBOL_EMPTY

    enforce_external_price: bool = False


class PureMarketMakingExternalCrossPriceConfig(PureMarketMakingExternalPriceConfig):
    config_type: Literal['PureMarketMakingExternalCrossPriceConfig'] = 'PureMarketMakingExternalCrossPriceConfig'

    exchange_cross_credentials: Union[ExchangeCredentialsEmpty, ExchangeCredentials] = ExchangeCredentialsEmpty()
    symbol_cross: Symbol = SYMBOL_EMPTY
    is_cross_price_reversed: bool = False


class PureMarketMakingFuturesExternalPriceConfig(PureMarketMakingExternalPriceConfig):
    config_type: Literal['PureMarketMakingFuturesExternalPriceConfig'] = 'PureMarketMakingFuturesExternalPriceConfig'
    leverage: Decimal = Decimal("1.0")

# class PureMarketMakingKalmanOrdersConfig(PureMarketMakingConfig):
#     config_type: Literal['PureMarketMakingKalmanOrdersConfig'] = 'PureMarketMakingKalmanOrdersConfig'
#     kalman_datastore_label: str


class ExposureFnConfig(BaseModel):
    start: Decimal = Decimal("0.0")
    end: Decimal = Decimal("-0.005")
    min_exp: Decimal = Decimal("0.0")
    max_exp: Decimal = Decimal("1.0")
    direction: str = 'long'


# class KalmanStepGainConfig(BaseModel):
#     config_type: Literal['KalmanStepGainConfig'] = 'KalmanStepGainConfig'
#     kalman_datastore_label: str
#
#     long_exposure: ExposureFnConfig
#     short_exposure: ExposureFnConfig
#     dust_amount: Decimal = Decimal("0.0")
#     price_change_tolerance: Decimal = Decimal("0.0")
#     order_amount_max: Decimal
#     order_amount_min: Decimal


# class MeanReversionConfig(BaseOneAssetConfig):
#     config_type: Literal['MeanReversionConfig'] = 'MeanReversionConfig'
#
#     kalman_datastore_label: str
#     long_exposure: ExposureFnConfig
#     short_exposure: ExposureFnConfig
#
#
# class MeanReversionMarketMakingConfig(PureMarketMakingConfig):
#     config_type: Literal['MeanReversionMarketMakingConfig'] = 'MeanReversionMarketMakingConfig'
#
#     kalman_datastore_label: str
#     long_exposure: ExposureFnConfig
#     short_exposure: ExposureFnConfig
#
#
# class KalmanSkewedMarketMakingConfig(PureMarketMakingConfig):
#     config_type: Literal['KalmanSkewedMarketMakingConfig'] = 'KalmanSkewedMarketMakingConfig'
#
#     kalman_datastore_label: str
#     long_exposure: ExposureFnConfig
#     short_exposure: ExposureFnConfig


# class PureAMMConfig(BaseModel):
#     config_type: Literal['PureAMMConfig'] = 'PureAMMConfig'
#     min_spread: Decimal


##########################################
# API bot config response
##########################################


class BotConfigResponse(BaseModel):
    bot_id: int
    debug: bool = False
    strategy_config: Union[
        GridConfig,
        PureMarketMakingExternalPriceZMQConfig,
        BSwapSellConfig,
        StatArbKalmanConfig,
        PureMarketMakingExternalCrossPriceConfig,
        PureMarketMakingFuturesConfig,
        FuturesToFuturesHedgingConfig,
        CrossExchangeMarketMakingFuturesConfig,
        PureMarketMakingConfig,
        OrderBookCollectorFuturesConfig,
        OrderBookCollectorSpotConfig,
        PureMarketMakingExternalPriceConfig,
        SpotToFuturesHedgingConfig,
        PureMarketMakingSpikeFilterConfig,
        TrendFollowingMakingFuturesConfig,
        PureMarketMakingFuturesExternalPriceConfig,
    ] = Field(descriminator='config_type')
    datastore: DatastoreConfig


STRATEGY_CONFIG_CLASS_MAP = {
    # "OwnLongBotConfig": OwnLongBotConfig,
    # "OwnShortBotConfig": OwnShortBotConfig,
    "GridConfig": GridConfig,
    "PureMarketMakingExternalPriceZMQConfig": PureMarketMakingExternalPriceZMQConfig,
    "BSwapSellConfig": BSwapSellConfig,
    "StatArbKalmanConfig": StatArbKalmanConfig,
    "PureMarketMakingConfig": PureMarketMakingConfig,
    "TrendFollowingMakingFuturesConfig": TrendFollowingMakingFuturesConfig,
    "CrossExchangeMarketMakingFuturesConfig": CrossExchangeMarketMakingFuturesConfig,
    "PureMarketMakingFuturesConfig": PureMarketMakingFuturesConfig,
    "FuturesToFuturesHedgingConfig": FuturesToFuturesHedgingConfig,
    "SpotToFuturesHedgingConfig": SpotToFuturesHedgingConfig,
    "OrderBookCollectorFuturesConfig": OrderBookCollectorFuturesConfig,
    "OrderBookCollectorSpotConfig": OrderBookCollectorSpotConfig,
    "PureMarketMakingExternalPriceConfig": PureMarketMakingExternalPriceConfig,
    "PureMarketMakingSpikeFilterConfig": PureMarketMakingSpikeFilterConfig,
    "PureMarketMakingExternalCrossPriceConfig": PureMarketMakingExternalCrossPriceConfig
    # "MeanReversionMarketMakingConfig": MeanReversionMarketMakingConfig,
    # "MeanReversionConfig": MeanReversionConfig,
    # "PureMarketMakingKalmanOrdersConfig": PureMarketMakingKalmanOrdersConfig,
    # "KalmanSkewedMarketMakingConfig": KalmanSkewedMarketMakingConfig,
    # "TrendFilterMarketMakingConfig": TrendFilterMarketMakingConfig
}


class AdminConfigInput(BaseModel):
    config_type: constr(regex=f'^({"|".join(STRATEGY_CONFIG_CLASS_MAP)})$')  # noqa
    data: Optional[
        Union[
            PureMarketMakingExternalPriceZMQConfig,
            BSwapSellConfig,
            StatArbKalmanConfig,
            PureMarketMakingConfig,
            PureMarketMakingFuturesConfig,
            CrossExchangeMarketMakingFuturesConfig,
            TrendFollowingMakingFuturesConfig,
            OrderBookCollectorSpotConfig,
            OrderBookCollectorFuturesConfig,
            SpotToFuturesHedgingConfig,
            PureMarketMakingExternalPriceConfig,
            PureMarketMakingSpikeFilterConfig
        ]
    ] = Field(descriminator='config_type')

    @root_validator
    def check_config_type_data(cls, values):
        if values.get('data') is not None and type(values.get('data')).__name__ != values.get('config_type'):
            raise ValueError('config_type and type of data are mismatched')
        return values

    @root_validator
    def transform_empty_data(cls, values):
        if not values.get('data') and values.get('config_type'):
            values['data'] = STRATEGY_CONFIG_CLASS_MAP[values['config_type']]()
        return values

    class Config:
        example = {
            "exchange_credentials": {
                "exchange": "binance",
                "credentials": {
                    "secret": "secret"
                },
                "type": "SPOT"
            },
            "symbol": {
                "base": "ETH",
                "quote": "USD"
            },
            "piranha": {
                "order_limit": None,
                "wall_distance": None
            },
            "order_config": {
                "min_fill_to_replace_pct": 0.9,
                "price_merge_step_pct": 0.0005,
                "price_replace_tolerance_pct": 0.0001
            },
            "config_type": "OwnShortBotConfig",
            "base_own": {
                "entry_start": 0.0,
                "entry_end": 0.0,
                "entry_levels": 0,
                "exit_start": 0.0,
                "exit_end": 0.0,
                "exit_levels": 0,
                "is_std_channels_enabled": False,
                "std_channels_mult_min": None,
                "std_channels_mult_max": None
            },
            "base_brw": {
                "entry_start": 0.0,
                "entry_end": 0.0,
                "entry_levels": 0,
                "exit_start": 0.0,
                "exit_end": 0.0,
                "exit_levels": 0,
                "is_std_channels_enabled": False,
                "std_channels_mult_min": None,
                "std_channels_mult_max": None
            },
            "quote_brw": {
                "entry_start": 0.0,
                "entry_end": 0.0,
                "entry_levels": 0,
                "exit_start": 0.0,
                "exit_end": 0.0,
                "exit_levels": 0,
                "is_std_channels_enabled": False,
                "std_channels_mult_min": None,
                "std_channels_mult_max": None
            }
        }
