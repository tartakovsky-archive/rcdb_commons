from decimal import Decimal

from pydantic import BaseModel, Field, constr, root_validator
from pydantic.typing import Optional, Literal, Union

from .exchange import Exchange, AccountType, Symbol, SymbolEmpty


class ExchangeCredentials(BaseModel):
    exchange: Exchange
    credentials: Union[dict, str]
    type: AccountType

    def is_filled(self) -> bool:
        return isinstance(self.credentials, dict)


class ExchangeCredentialsEmpty(ExchangeCredentials):
    exchange: Literal['EMPTY'] = 'EMPTY'
    credentials: Union[dict, str] = 'EMPTY'
    type: Literal['EMPTY'] = 'EMPTY'


class BorrowingConfig(BaseModel):
    is_base_borrow_enabled: bool = False
    base_amount_max: float = 0.0
    base_borrow_level_pct: float = 0.0
    base_repay_level_pct: float = 0.0

    is_quote_borrow_enabled: bool = False
    quote_amount_max: float = 0.0
    quote_borrow_level_pct: float = 0.0
    quote_repay_level_pct: float = 0.0

    margin_level_max: float = 1.5


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
class EmptyExchangeCredentialsMixin(BaseModel):
    exchange_credentials: Union[ExchangeCredentialsEmpty, ExchangeCredentials] = ExchangeCredentialsEmpty()


class EmptySymbolMixin(BaseModel):
    symbol: Union[SymbolEmpty, Symbol] = SymbolEmpty()


class EmptySymbolExchangeCredentialsMixin(EmptySymbolMixin, EmptyExchangeCredentialsMixin):
    pass


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


class BotDefaultConfig(EmptySymbolExchangeCredentialsMixin):
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
# MarketMaking
##########################################

class PureMarketMakingConfig(EmptySymbolExchangeCredentialsMixin):
    config_type: Literal['PureMarketMakingConfig'] = 'PureMarketMakingConfig'

    bid_spread: Decimal = Decimal("0.0")
    ask_spread: Decimal = Decimal("0.0")

    minimum_spread: Decimal = Decimal("0.0")
    dust_amount: Decimal = Decimal("0.0")

    price_change_tolerance: Decimal = Decimal("0.0")

    order_amount_max: Decimal = Decimal("0.0")
    order_amount_min: Decimal = Decimal("0.0")

    bid_levels: int = 1
    ask_levels: int = 1


class ExposureFnConfig(BaseModel):
    start: Decimal = Decimal("0.0")
    end: Decimal = Decimal("-0.005")
    min_exp: Decimal = Decimal("0.0")
    max_exp: Decimal = Decimal("1.0")
    direction: str = 'long'


class KalmanStepGainConfig(EmptySymbolExchangeCredentialsMixin):
    config_type: Literal['KalmanStepGainConfig'] = 'KalmanStepGainConfig'
    kalman_datastore_label: str

    long_exposure: ExposureFnConfig
    short_exposure: ExposureFnConfig
    dust_amount: Decimal = Decimal("0.0")
    price_change_tolerance: Decimal = Decimal("0.0")
    order_amount_max: Decimal
    order_amount_min: Decimal


class PureAMMConfig(EmptySymbolExchangeCredentialsMixin):
    config_type: Literal['PureAMMConfig'] = 'PureAMMConfig'
    min_spread: Decimal


##########################################
# API bot config response
##########################################


class BotConfigResponse(BaseModel):
    bot_id: int
    debug: bool = False
    strategy_config: Union[
        PureAMMConfig,
        PureMarketMakingConfig,
        KalmanStepGainConfig,
        OwnLongBotConfig,
        OwnShortBotConfig
    ] = Field(descriminator='config_type')
    datastore: DatastoreConfig


STRATEGY_CONFIG_CLASS_MAP = {
    "OwnLongBotConfig": OwnLongBotConfig,
    "OwnShortBotConfig": OwnShortBotConfig,
    "PureMarketMakingConfig": PureMarketMakingConfig
}


class AdminConfigInput(BaseModel):
    config_type: constr(regex=f'^({"|".join(STRATEGY_CONFIG_CLASS_MAP)})$')  # noqa
    data: Optional[
        Union[OwnLongBotConfig, OwnShortBotConfig, PureMarketMakingConfig]
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
