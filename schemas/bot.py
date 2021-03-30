import enum
import typing
import typing_extensions

import pydantic


class Exchange(enum.Enum):
    binance = "binance"
    kraken = "kraken"
    okex = "okex"


class ExchangeCredentials(pydantic.BaseModel):
    exchange: Exchange
    credentials: dict

    class Config:
        use_enum_values = True


class Symbol(pydantic.BaseModel):
    base: str
    quote: str


class Instrument(pydantic.BaseModel):
    symbol: Symbol
    exchange: Exchange
    amount_precision: float
    price_precision: float
    order_amount_max: float
    order_amount_min: float

    class Config:
        use_enum_values = True


class BorrowingConfig(pydantic.BaseModel):
    is_base_borrow_enabled: bool = False
    base_amount_max: float = 0.0
    base_borrow_level_pct: float = 0.0
    base_repay_level_pct: float = 0.0

    is_quote_borrow_enabled: bool = False
    quote_amount_max: float = 0.0
    quote_borrow_level_pct: float = 0.0
    quote_repay_level_pct: float = 0.0

    margin_level_max: float = 1.5


class DatastoreConfig(pydantic.BaseModel):
    api_url: str
    token: str


class OrderGridConfig(pydantic.BaseModel):
    entry_start: float = 0.0
    entry_end: float = 0.0
    entry_levels: int = 0

    exit_start: float = 0.0
    exit_end: float = 0.0
    exit_levels: int = 0

    is_std_channels_enabled: bool = False
    std_channels_mult_min: float = None
    std_channels_mult_max: float = None


class BidAskLevelsConfig(pydantic.BaseModel):
    bid_start: float
    bid_end: float
    bid_levels: int

    ask_start: float
    ask_end: float
    ask_levels: float


class LongOrderGridConfig(OrderGridConfig):
    def get_bid_ask_channel(self):
        return BidAskLevelsConfig(
            bid_start=self.entry_start,
            bid_end=self.entry_end,
            bid_levels=self.entry_levels,

            ask_start=self.exit_start,
            ask_end=self.exit_end,
            ask_levels=self.exit_levels,
        )


class ShortOrderGridConfig(OrderGridConfig):
    def get_bid_ask_channel(self):
        return BidAskLevelsConfig(
            ask_start=self.entry_start,
            ask_end=self.entry_end,
            ask_levels=self.entry_levels,

            bid_start=self.exit_start,
            bid_end=self.exit_end,
            bid_levels=self.exit_levels,
        )


class OrderConfig(pydantic.BaseModel):
    min_fill_to_replace_pct: float = 0.9
    price_merge_step_pct: float = 0.0005
    price_replace_tolerance_pct: float = 0.0001


class PiranhaConfig(pydantic.BaseModel):
    order_limit: float = None
    wall_distance: float = None


#####################
# Bot Configs
#####################


class BotBaseConfig(pydantic.BaseModel):
    debug: bool = False
    frequency_seconds: int = 2
    is_margin: bool = False
    borrowing: BorrowingConfig = pydantic.Field(default_factory=BorrowingConfig)


#####################
# Bot default Kalman config
#####################


class BotDefaultConfig(pydantic.BaseModel):
    piranha: PiranhaConfig = pydantic.Field(default_factory=PiranhaConfig)
    order_config: OrderConfig = pydantic.Field(default_factory=OrderConfig)


class OwnLongBotConfig(BotDefaultConfig):
    config_type: typing_extensions.Literal['OwnLongBotConfig'] = 'OwnLongBotConfig'

    quote_own: LongOrderGridConfig = pydantic.Field(default_factory=LongOrderGridConfig)
    base_brw: ShortOrderGridConfig = pydantic.Field(default_factory=ShortOrderGridConfig)
    quote_brw: LongOrderGridConfig = pydantic.Field(default_factory=LongOrderGridConfig)


class OwnShortBotConfig(BotDefaultConfig):
    config_type: typing_extensions.Literal['OwnShortBotConfig'] = 'OwnShortBotConfig'

    base_own: ShortOrderGridConfig = pydantic.Field(default_factory=LongOrderGridConfig)
    base_brw: ShortOrderGridConfig = pydantic.Field(default_factory=ShortOrderGridConfig)
    quote_brw: LongOrderGridConfig = pydantic.Field(default_factory=LongOrderGridConfig)


#####################
# API bot config response
#####################


class BotConfigResponse(BotBaseConfig):
    bot_id: int
    bot_config: typing.Union[OwnLongBotConfig, OwnShortBotConfig] = pydantic.Field(descriminator='config_type')
    exchange_credentials: ExchangeCredentials
    instrument: Instrument
    datastore: DatastoreConfig


BOT_CONFIG_CLASS_MAP = {
    "OwnLongBotConfig": OwnLongBotConfig,
    "OwnShortBotConfig": OwnShortBotConfig,
}


class AdminConfigInput(pydantic.BaseModel):
    config_type: pydantic.constr(regex=f'^({"|".join(BOT_CONFIG_CLASS_MAP)})$')  # noqa
    data: typing.Optional[
        typing.Union[OwnLongBotConfig, OwnShortBotConfig]
    ] = pydantic.Field(descriminator='config_type')

    @pydantic.root_validator
    def check_config_type_data(cls, values):
        if values.get('data') is not None and type(values.get('data')).__name__ != values.get('config_type'):
            raise ValueError('config_type and type of data are mismatched')
        return values

    @pydantic.root_validator
    def transform_empty_data(cls, values):
        if not values.get('data') and values.get('config_type'):
            values['data'] = BOT_CONFIG_CLASS_MAP[values['config_type']]()
        return values

    class Config:
        example = {
            "config_type": "OwnLongBotConfig",
            "data": {
                'debug': False,
                'frequency_seconds': 2,
                'is_margin': False,
                'borrowing': {
                    'is_base_borrow_enabled': False,
                    'base_amount_max': 0.0,
                    'base_borrow_level_pct': 0.0,
                    'base_repay_level_pct': 0.0,
                    'is_quote_borrow_enabled': False,
                    'quote_amount_max': 0.0,
                    'quote_borrow_level_pct': 0.0,
                    'quote_repay_level_pct': 0.0,
                    'margin_level_max': 1.5
                },
                'own_capital': {
                    'entry_start': 0.0,
                    'entry_end': 0.0,
                    'entry_levels': 0,
                    'exit_start': 0.0,
                    'exit_end': 0.0,
                    'exit_levels': 0,
                    'is_std_channels_enabled': False,
                    'std_channels_mult_min': None,
                    'std_channels_mult_max': None
                },
                'base_capital': {
                    'entry_start': 0.0,
                    'entry_end': 0.0,
                    'entry_levels': 0,
                    'exit_start': 0.0,
                    'exit_end': 0.0,
                    'exit_levels': 0,
                    'is_std_channels_enabled': False,
                    'std_channels_mult_min': None,
                    'std_channels_mult_max': None
                },
                'quote_capital': {
                    'entry_start': 0.0,
                    'entry_end': 0.0,
                    'entry_levels': 0,
                    'exit_start': 0.0,
                    'exit_end': 0.0,
                    'exit_levels': 0,
                    'is_std_channels_enabled': False,
                    'std_channels_mult_min': None,
                    'std_channels_mult_max': None
                },
                'piranha': {
                    'order_limit': None,
                    'wall_distance': None
                },
                'order_config': {
                    'min_fill_to_replace_pct': 0.9,
                    'price_merge_step_pct': 0.0005,
                    'price_tolerance_pct': 0.0001
                }
            }
        }
