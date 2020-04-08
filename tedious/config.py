"""
    load_config: loads given config file into global variable CONFIG.
"""

from configparser import ConfigParser
import os
from typing import List

CONFIG = None

AUTH_REQUIRED_KEYS = ['KEYS.private-keys', 'KEYS.public-keys', 'KEYS.identifier-secret',
                      'TOKEN.expire', 'TOKEN.issuer', 'TOKEN.refresh-token-bytes', 'TOKEN.refresh-token-lifespan', 'TOKEN.audience',
                      'SCRYPT.mem_cost', 'SCRYPT.rounds']
SQL_REQUIRED_KEYS = ['DB_CREDENTIALS.database', 'DB_CREDENTIALS.user', 'DB_CREDENTIALS.password', 'DB.close-timeout']
ASGI_REQUIRED_KEYS = ['ASGI.max-body-size']
STORAGE_REQUIRED_KEYS = ['STG.public-directory', 'STG.private-directory', 'STG.temporary-directory']

_REQUIRED_VALUES = AUTH_REQUIRED_KEYS + SQL_REQUIRED_KEYS + ASGI_REQUIRED_KEYS + STORAGE_REQUIRED_KEYS


def _check_required_keys(required_keys):
    missing = []

    for key_path in required_keys:
        steps = key_path.split('.')
        path = CONFIG
        for step in steps:
            if step not in path:
                missing.append(key_path)
            else:
                path = path[step]

    return missing


def load_config(file_path: str, required_keys: List[str] = None) -> None:
    """

    :param file_path: path to config file
    :param required_keys: list of required keys. can be key paths like 'DB.user'.
    :raises: ValueError if keys are missing
    """

    if required_keys is None:
        required_keys = _REQUIRED_VALUES

    if not os.path.exists(file_path):
        raise ValueError(f"Can't find file {file_path}")

    parser = ConfigParser()
    parser.read(file_path)

    global CONFIG
    CONFIG = {}

    for section in parser.sections():
        CONFIG[section] = {}
        for item in parser.items(section):
            CONFIG[section][item[0]] = item[1]

    missing_keys = _check_required_keys(required_keys)
    if len(missing_keys) > 0:
        raise ValueError("Config is missing some keys.\n" + ", ".join(missing_keys))


def _create_empty_config_file():
    """
        Creates config file with all required keys according to _REQUIRED_VALUES, all keys will be set to nothing
        python3 script.py <path to config file>
    """
    from sys import argv
    from os.path import exists
    if len(argv) < 2:
        print("Please add path to write to.")
        return

    global CONFIG
    CONFIG = {}

    for key_path in _REQUIRED_VALUES:
        section_key = key_path.split('.')
        if section_key[0] not in CONFIG:
            CONFIG[section_key[0]] = []
        CONFIG[section_key[0]].append(section_key[1])

    if exists(argv[1]):
        print("File already exists.")
        return

    try:
        with open(argv[1], 'a+') as file:
            for section in CONFIG:
                file.writelines(['[{}]\n'.format(section)] + ['{}=\n'.format(key) for key in CONFIG[section]])
    except OSError:
        print("Unable to find file '{}'.".format(argv[1]))


if __name__ == '__main__':
    _create_empty_config_file()
