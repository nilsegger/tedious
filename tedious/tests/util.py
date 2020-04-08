from datetime import datetime, timedelta
import random
from typing import Tuple

from tedious.asgi.request_interface import RequestInterface, Methods
from tedious.logger import Logger
from tedious.mdl.model import Model

from tedious.util import create_uuid

from tedious.mdl.fields import UUIDField, StrField, IntField, EnumField, DateTimeField, BoolField

from tedious.auth.auth import Auth, Requester

from tedious.sql.postgres import PostgreSQLDatabase
import uuid
import tedious.config
import aiofiles


async def read_file(asset):
    async with aiofiles.open(asset, 'rb') as f:
        _bytes = await f.read()
    return _bytes


class TestConnection:
    __slots__ = ('db', 'connection')

    async def __aenter__(self):
        assert tedious.config.CONFIG is not None, "Please load configuration file."
        self.db = PostgreSQLDatabase(**tedious.config.CONFIG["DB_CREDENTIALS"])
        await self.db.connect()
        self.connection = await self.db.acquire()
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.connection.close()
        await self.db.close()


class AuthUtil:

    @staticmethod
    async def create_user(connection) -> Requester:
        username = uuid.uuid4().hex[:30]
        password = "12345678"
        role = 'user'
        return await Auth().register(connection, username, password, role)


def randomize(mdl: Model):
    from tedious.tests.words import words

    for field_key in mdl:
        field = mdl[field_key]
        if isinstance(field, Model):
            randomize(field)
        elif isinstance(field, UUIDField):
            field.value = create_uuid()
        elif isinstance(field, StrField):
            field.value = ' '.join(random.choices(words, k=3))
            while field.min_len is not None and len(field.value) < field.min_len:
                field.value += ' {}'.format(' '.join(random.choices(words, k=5)))
            if field.max_len is not None and len(field.value) > field.max_len:
                field.value = field.value[:field.max_len]
        elif isinstance(field, IntField):
            min_val = field.min_val if field.min_val is not None else 1
            field.value = random.randrange(min_val, field.max_val if field.max_val is not None else min_val + 1000)
        elif isinstance(field, EnumField):
            field.value = field.enum_class(random.choice([item.value for item in field.enum_class]))
        elif isinstance(field, DateTimeField):
            if field.min_age is not None:
                field.value = datetime.now() - timedelta(seconds=random.randrange(field.min_age, field.min_age + 2592000))
            elif field.max_age is not None:
                field.value = datetime.now() - timedelta(seconds=random.randrange(1, field.max_age))
            else:
                field.value = datetime.now() + timedelta(seconds=random.randrange(0, 2592000))
        elif isinstance(field, BoolField):
            field.value = random.choice([True, False])
        else:
            raise NotImplementedError("Field of type {} can not be randomized".format(type(field)))

    return mdl


def compare(actual: Model, expected: Model):
    assert isinstance(actual, type(expected)), "Actual does not match expected type of {} with {}.".format(type(expected), type(actual))
    for field in expected:
        expected_field = expected[field]
        actual_field = actual[field]
        if isinstance(expected_field, Model):
            compare(actual_field, expected_field)
        else:
            assert (
                           expected_field.value is None or actual_field.value is None) or expected_field.value == actual_field.value, "Actual value '{}' does not match expected '{}' for field {}.".format(
                actual_field.value,
                expected_field.value, field)


class MockRequest(RequestInterface):
    """
        Class used for testing, all members are easily set.
    """

    def __init__(self, requester=None, url=None, method=None, client=None, cookies=None, body_bytes=None, body_json=None, params=None, headers=None):
        self._requester = requester
        self._url = url
        self._method = method
        self._client = client
        self._cookies = cookies
        self._body_bytes = body_bytes
        self._body_json = body_json
        self._headers = headers
        self._params = params

    @property
    def requester(self) -> Requester:
        return self._requester

    @property
    def url(self) -> str:
        return self._url

    @property
    def method(self) -> Methods:
        return self._method

    @property
    def client(self) -> Tuple[str, int]:
        return self._client

    @property
    def cookies(self) -> dict:
        return self._cookies

    async def get_body_bytes(self) -> bytes:
        return self._body_bytes

    async def get_body_json(self) -> dict:
        return self._body_json

    def get_header(self, key, default=None):
        return self._headers[key] if self._headers is not None and key in self._headers else default

    def get_param(self, key, default=None):
        return self._params[key] if self._params is not None and key in self._params else default


class MockLogger(Logger):
    pass
