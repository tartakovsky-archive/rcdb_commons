import json
import logging
from typing import Union

from onepasswordconnectsdk.client import ItemVault, Client, new_client

from schemas.strategy_configs import ExchangeCredentials, ExchangeCredentialsEmpty

logger = logging.getLogger("rcdb_credentials_store")


class CredentialsStore:
    """
    Helps to retrieve secrets from the 1p vault.

    Example:
    >>> store = CredentialsStore('http://localhost:8080', '<TOKEN>', '<VAULT NAME>')
    >>> exc_creds = ExchangeCredentials(exchange=Exchange.binance, credentials='test-cred-2', type=AccountType.SPOT)
    >>> store.replace_exchange_credentials_with_secrets(exc_creds)
    exchange=<Exchange.binance: 'binance'> credentials={'apiKey': 'a', 'secretKey': 'a'} type=<AccountType.SPOT: 'SPOT'>
    """
    def __init__(self, host: str, token: str, vault_name: str = 'prod-secrets'):
        self.client: Client = new_client(host, token)
        self.vault = self.get_vault_by_name(vault_name)

    def get_secret(self, name: str, raw=False) -> Union[dict, str]:
        summary_item = self.client.get_item_by_title(name, self.vault.id)
        item = self.client.get_item(summary_item.id, self.vault.id)
        value = [field['value'] for field in item.to_dict()['fields'] if field['id'] == 'notesPlain'][0]
        return value if raw else json.loads(value)

    def get_vault_by_name(self, name: str) -> ItemVault:
        return [vault for vault in self.client.get_vaults() if vault.name == name][0]

    def replace_exchange_credentials_with_secrets(
        self,
        exchange_credentials: ExchangeCredentials
    ) -> ExchangeCredentials:
        if isinstance(exchange_credentials, ExchangeCredentialsEmpty):
            raise Exception('exchange_credentials is instance of ExchangeCredentialsEmpty')

        if exchange_credentials.is_filled():
            logger.warning('exchange_credentials is already filled')
            return exchange_credentials

        return ExchangeCredentials(
            **{
                **exchange_credentials.dict(),
                'credentials': self.get_secret(exchange_credentials.credentials)
            }
        )
