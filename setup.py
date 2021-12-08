import os
import sys
from setuptools import setup, find_packages


REQUIREMENTS_DIR = "requirements"


def parse_reqs(path):
    with open(path) as f:
        return [req.strip() for req in f.readlines() if req.strip() and not req.startswith('#')]


module_name = "rcdb_commons"
if 'egg_info' in sys.argv:
    os.rename('lib', module_name)


setup(
    name='rcdb_commons',
    version='0.1',
    packages=find_packages(include=[f"{module_name}*"]),
    install_requires=parse_reqs("requirements.txt")
)
