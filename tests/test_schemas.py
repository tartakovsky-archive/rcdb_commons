import json
from importlib import resources

import pytest
import pydantic

from schemas.strategy_configs import STRATEGY_CONFIG_CLASS_MAP, BotConfigResponse, DatastoreConfig, \
    AdminConfigInput, OwnShortBotConfig, OwnLongBotConfig, PureMarketMakingConfig


BOT_CONFIG_JSON = json.load(resources.open_text('tests.datasets', 'valid_config.json'))


@pytest.fixture(scope='session')
def bot_config_response():
    bot_id = 1
    BOT_CONFIG_DB = {
        1: {
            "class": "OwnLongBotConfig",
            "json": {
                "exchange_credentials": {
                    "exchange": "binance",
                    "credentials": {},
                    "type": "CROSS_MARGIN"
                },
                "symbol": {
                    "base": "EUR",
                    "quote": "BUSD"
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
                "config_type": "OwnLongBotConfig",
                "quote_own": {
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
        }
    }

    def orm_get_bot_config(bot_id):
        bot_conf = BOT_CONFIG_DB[bot_id]
        bot_conf_inst = STRATEGY_CONFIG_CLASS_MAP[bot_conf['class']](**bot_conf['json'])
        return bot_conf_inst

    return BotConfigResponse(
        bot_id=bot_id,
        strategy_config=orm_get_bot_config(bot_id),
        datastore=DatastoreConfig(api_url="", token="")
    )


def test_bot_config_to_json(bot_config_response: BotConfigResponse):
    print('bb', bot_config_response.json(indent=4))
    assert json.loads(bot_config_response.json()) == BOT_CONFIG_JSON


def test_bot_config_from_json(bot_config_response: BotConfigResponse):
    assert bot_config_response == BotConfigResponse(**BOT_CONFIG_JSON)


def test_admin_config_input():
    AdminConfigInput(**AdminConfigInput.Config.example)


def test_admin_config_input_different_config(bot_config_response: BotConfigResponse):
    data = {'data': bot_config_response.strategy_config, 'config_type': 'OwnShortBotConfig'}
    with pytest.raises(pydantic.error_wrappers.ValidationError) as exc:
        AdminConfigInput(**data)

    assert 'config_type and type of data are mismatched' in str(exc)


def test_from_admin_input_to_response(bot_config_response: BotConfigResponse):
    admin_input = AdminConfigInput(
        config_type=bot_config_response.strategy_config.config_type,
        data=bot_config_response.strategy_config
    )

    assert BotConfigResponse(
        bot_id=bot_config_response.bot_id,
        strategy_config=admin_input.data,
        datastore=bot_config_response.datastore
    ) == bot_config_response


def test_wrong_config_type():
    data = {**AdminConfigInput.Config.example, 'config_type': 'some'}
    with pytest.raises(pydantic.error_wrappers.ValidationError) as exc:
        AdminConfigInput(**data)

    assert 'string does not match regex' in str(exc)


@pytest.mark.parametrize(
    'config_data',
    [
        ('OwnLongBotConfig', OwnLongBotConfig),
        ('OwnShortBotConfig', OwnShortBotConfig),
        ('PureMarketMakingConfig', PureMarketMakingConfig)
    ]
)
def test_default_config(config_data):
    config_type, config_class = config_data
    assert STRATEGY_CONFIG_CLASS_MAP[config_type] == config_class
    assert AdminConfigInput(**{'config_type': config_type}).data == config_class()


@pytest.mark.parametrize(
    'config_data',
    [
        ('OwnLongBotConfig', OwnLongBotConfig),
        ('OwnShortBotConfig', OwnShortBotConfig),
        ('PureMarketMakingConfig', PureMarketMakingConfig)
    ]
)
def test_config_union(config_data):
    config_type, config_class = config_data
    assert AdminConfigInput(**{'config_type': config_type, 'data': config_class().dict()}).data == config_class()
