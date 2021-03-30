import json
from importlib import resources

import pytest

from schemas.bot import \
    BOT_CONFIG_CLASS_MAP, Exchange, ExchangeCredentials, BotConfigResponse, Instrument, Symbol, DatastoreConfig


BOT_CONFIG_JSON = json.load(resources.open_text('tests.datasets', 'valid_config.json'))


@pytest.fixture(scope='session')
def bot_config_response():
    bot_id = 1
    BOT_CONFIG_DB = {
        1: {
            "class": "OwnLongBotConfig",
            "json": {
                'debug': False,
                'frequency_seconds': 2,
                'is_margin': False,
                'borrowing': {'is_base_borrow_enabled': False, 'base_amount_max': 0.0, 'base_borrow_level_pct': 0.0,
                              'base_repay_level_pct': 0.0, 'is_quote_borrow_enabled': False, 'quote_amount_max': 0.0,
                              'quote_borrow_level_pct': 0.0, 'quote_repay_level_pct': 0.0, 'margin_level_max': 1.5},
                'own_capital': {'entry_start': 0.0, 'entry_end': 0.0, 'entry_levels': 0, 'exit_start': 0.0,
                                'exit_end': 0.0, 'exit_levels': 0, 'is_std_channels_enabled': False,
                                'std_channels_mult_min': None, 'std_channels_mult_max': None},
                'base_capital': {'entry_start': 0.0, 'entry_end': 0.0, 'entry_levels': 0, 'exit_start': 0.0,
                                 'exit_end': 0.0, 'exit_levels': 0, 'is_std_channels_enabled': False,
                                 'std_channels_mult_min': None, 'std_channels_mult_max': None},
                'quote_capital': {'entry_start': 0.0, 'entry_end': 0.0, 'entry_levels': 0, 'exit_start': 0.0,
                                  'exit_end': 0.0, 'exit_levels': 0, 'is_std_channels_enabled': False,
                                  'std_channels_mult_min': None, 'std_channels_mult_max': None},
                'piranha': {
                    'order_limit': None, 'wall_distance': None},
                'order_config': {
                    'min_fill_to_replace_pct': 0.9, 'price_merge_step_pct': 0.0005,
                    'price_tolerance_pct': 0.0001}},
        }
    }

    def orm_get_bot_config(bot_id):
        bot_conf = BOT_CONFIG_DB[bot_id]
        bot_conf_inst = BOT_CONFIG_CLASS_MAP[bot_conf['class']](**bot_conf['json'])
        return bot_conf_inst

    return BotConfigResponse(
        bot_id=bot_id,
        bot_config=orm_get_bot_config(bot_id),
        exchange_credentials=ExchangeCredentials(
            exchange=Exchange.binance,
            credentials=dict(secret="XYZ")
        ),
        instrument=Instrument(
            symbol=Symbol(base="EUR", quote="USD"),
            exchange=Exchange.binance,
            amount_precision=2,
            price_precision=4,
            order_amount_max=100_000,
            order_amount_min=10
        ),
        datastore=DatastoreConfig(api_url="", token="")
    )


def test_bot_config_to_json(bot_config_response: BotConfigResponse):
    assert bot_config_response.dict() == BOT_CONFIG_JSON


def test_bot_config_from_json(bot_config_response: BotConfigResponse):
    assert bot_config_response == BotConfigResponse(**BOT_CONFIG_JSON)
