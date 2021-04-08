import logging

from rcdb_commons.schemas.bot import BotConfigResponse
import requests


logger = logging.getLogger("rcdb_config_store")


class ConfigException(Exception):
    pass


class ConfigStore:
    def __init__(self, api_url, token):
        self.api_url = api_url
        self.session = requests.Session()
        self.session.headers.update({'Authorization': f'Bearer {token}'})
        # self.session.headers.update(
        # {'X-CSRFToken': f'1dzy45EaC1LjJp7T67TnOYTCEotlO9aRge1z0Knn31b1ps19RKLFh3CtZHnOrAqd'})

    def get_config(self, bot_id: int) -> BotConfigResponse:
        r = self.session.get(
            f"{self.api_url}/bot/{bot_id}",
            timeout=100
        )
        if r.status_code == 200:
            return BotConfigResponse(**r.json())
        elif r.status_code == 404:
            return None
        else:
            raise ConfigException(r.text)
