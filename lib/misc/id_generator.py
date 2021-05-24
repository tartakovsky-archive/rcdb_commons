from random import choice
from string import digits, ascii_letters


def random_numeric_id(length: int = 10):
    return ''.join(choice(digits) for _ in range(length))


def random_string_id(length: int = 10):
    return ''.join(choice(digits + ascii_letters) for _ in range(length))