import logging
import requests

from ..schemas.strategy_configs import BotConfigResponse

logger = logging.getLogger("rcdb_config_store")


class ConfigException(Exception):
    pass


class ConfigStore:
    def __init__(self, api_url, token):
        self.api_url = api_url
        self.session = requests.Session()
        self.session.headers.update({'Authorization': f'Bearer {token}'})

    def get_config(self, bot_id: int) -> BotConfigResponse:
        r = self.session.get(
            f"{self.api_url}/bot/{bot_id}",
            timeout=100
        )
        if r.status_code == 200:
            # data = r.json()
            # data['instrument']['type'] = "SPOT"
            # data['exchange_credentials']['type'] = "SPOT"
            # data['strategy_config'] = data['bot_config']
            # del data['bot_config']
            # del data['is_margin']
            return BotConfigResponse(**r.json())
        elif r.status_code == 404:
            return None
        else:
            raise ConfigException(r.text)
