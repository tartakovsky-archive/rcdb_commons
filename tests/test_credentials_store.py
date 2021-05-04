import json
from typing import Tuple
from unittest.mock import MagicMock

import pytest
from onepasswordconnectsdk.models import Vault, SummaryItem, Item

from lib.stores import CredentialsStore
from lib.schemas.strategy_configs import ExchangeCredentialsEmpty, ExchangeCredentials, Exchange, AccountType

HOST = 'host'
TOKEN = 'token'
VAULT_NAME = 'vault name'
VAULT = Vault(id='aiwiodaw', name=VAULT_NAME)
SUMMARY_ITEM_ID = 'summary_item_id'
SECRET = '{"secret": "some"}'

STORE_MOCK_TYPE = Tuple[MagicMock, CredentialsStore]


@pytest.fixture
def credentials_store(mocker):

    class VaultsMixin(MagicMock):
        def get_vaults(self):
            return [VAULT]

    mocked_new_client = mocker.patch('lib.stores.credentials_store.new_client', VaultsMixin())
    store = CredentialsStore(HOST, TOKEN, VAULT_NAME)
    store.client.get_item_by_title.return_value = SummaryItem(id=SUMMARY_ITEM_ID)
    store.client.get_item.return_value = Item(id='asdsa', fields=[{'id': 'notesPlain', 'value': SECRET}])
    yield mocked_new_client, store


def test_init(credentials_store: STORE_MOCK_TYPE):
    mocked_new_client, store = credentials_store
    mocked_new_client.assert_called_once_with(HOST, TOKEN)
    assert store.vault == VAULT


@pytest.mark.parametrize('raw', [True, False])
def test_get_secret(credentials_store: STORE_MOCK_TYPE, raw):
    _, store = credentials_store
    test_name = 'name'
    assert store.get_secret(test_name, raw=raw) == (SECRET if raw else json.loads(SECRET))
    store.client.get_item_by_title.assert_called_once_with(test_name, store.vault.id)
    store.client.get_item.assert_called_once_with(SUMMARY_ITEM_ID, store.vault.id)


def test_replace_exchange_credentials_with_secrets_empty(credentials_store: STORE_MOCK_TYPE):
    _, store = credentials_store

    with pytest.raises(Exception) as ex:
        store.replace_exchange_credentials_with_secrets(ExchangeCredentialsEmpty())

    ex.match('exchange_credentials is instance of ExchangeCredentialsEmpty')


def test_replace_exchange_credentials_with_secrets_filled(credentials_store: STORE_MOCK_TYPE):
    _, store = credentials_store
    exchange_credentials = ExchangeCredentials(
        exchange=Exchange.binance,
        credentials={'auth': 21231},
        type=AccountType.CROSS_MARGIN
    )
    assert store.replace_exchange_credentials_with_secrets(exchange_credentials) is exchange_credentials


def test_replace_exchange_credentials_with_secrets(credentials_store: STORE_MOCK_TYPE):
    _, store = credentials_store
    exchange_credentials = ExchangeCredentials(
        exchange=Exchange.binance,
        credentials='name',
        type=AccountType.CROSS_MARGIN
    )
    result = store.replace_exchange_credentials_with_secrets(exchange_credentials)
    assert result == ExchangeCredentials(
        **{
            **exchange_credentials.dict(),
            'credentials': json.loads(SECRET)
        }
    )
