import enum
from typing import List


class AccountType(enum.Enum):
    SPOT = 'SPOT'
    CROSS_MARGIN = 'CROSS_MARGIN'
    ISOLATED_MARGIN = 'ISOLATED_MARGIN'
    USDT_M_FUTURES = 'USDT_M_FUTURES'
    COIN_M_FUTURES = 'COIN_M_FUTURES'

    @property
    def label(self) -> str:
        return self.labels()[self]

    @classmethod
    def labels(cls) -> dict:
        return {
            cls.SPOT: 'Spot',
            cls.CROSS_MARGIN: 'Cross Margin',
            cls.ISOLATED_MARGIN: 'Isolated Margin',
            cls.USDT_M_FUTURES: 'USDT-M Futures',
            cls.COIN_M_FUTURES: 'COIN-M Futures'
        }

    @classmethod
    def choices(cls, use_value: bool = True) -> List[tuple]:
        labels = cls.labels().items()
        if use_value:
            labels = map(lambda choice: (choice[0].value, choice[1]), labels)
        return list(labels)
