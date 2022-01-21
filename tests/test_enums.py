import pytest

from lib.schemas.exchange import AccountType


@pytest.mark.parametrize(
    'use_value, test_choices',
    [
        (
            True,
            [
                ('SPOT', 'Spot'),
                ('CROSS_MARGIN', 'Cross Margin'),
                ('ISOLATED_MARGIN', 'Isolated Margin'),
                ('USDT_M_FUTURES', 'USDT-M Futures'),
                ('COIN_M_FUTURES', 'COIN-M Futures'),
                ('INVERSE_FUTURES', 'Inverse Futures'),
                ('USDT_PERPETUAL', 'USDT Perpetual'),
                ('INVERSE_PERPETUAL', 'Inverse Perpetual')
            ]
        ),
        (
            False,
            [
                (AccountType.SPOT, 'Spot'),
                (AccountType.CROSS_MARGIN, 'Cross Margin'),
                (AccountType.ISOLATED_MARGIN, 'Isolated Margin'),
                (AccountType.USDT_M_FUTURES, 'USDT-M Futures'),
                (AccountType.COIN_M_FUTURES, 'COIN-M Futures'),
                (AccountType.INVERSE_FUTURES, 'Inverse Futures'),
                (AccountType.INVERSE_PERPETUAL, 'Inverse Perpetual')
            ]
        )
    ]
)
def test_AccountType_choices(use_value, test_choices):
    assert set(AccountType.choices(use_value=use_value)) == set(test_choices)


@pytest.mark.parametrize(
    'account_type, test_label',
    [
        (AccountType.SPOT, 'Spot'),
        (AccountType.CROSS_MARGIN, 'Cross Margin'),
        (AccountType.ISOLATED_MARGIN, 'Isolated Margin'),
        (AccountType.USDT_M_FUTURES, 'USDT-M Futures'),
        (AccountType.COIN_M_FUTURES, 'COIN-M Futures'),
        (AccountType.INVERSE_FUTURES, 'Inverse Futures'),
        (AccountType.INVERSE_PERPETUAL, 'Inverse Perpetual')
    ]
)
def test_AccountType_label(account_type, test_label):
    assert account_type.label == test_label


def test_AccountType_in_set():
    assert AccountType.SPOT in {AccountType.SPOT, AccountType.CROSS_MARGIN}
