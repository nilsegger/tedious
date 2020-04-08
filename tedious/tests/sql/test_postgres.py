import asyncpg
import pytest
from tedious.mdl.fields import StrField

import tedious.config
from tedious.mdl.model import Model
from tedious.sql.postgres import PostgreSQLDatabase

tedious.config.load_config('tedious/tests/config.ini', tedious.config.SQL_REQUIRED_KEYS)

CREDENTIALS = tedious.config.CONFIG['DB_CREDENTIALS']

DROP_TABLE = "DROP TABLE IF EXISTS users"
CREATE_USERS_TABLE = "CREATE TABLE IF NOT EXISTS users(id serial PRIMARY KEY, name text)"
INSERT_USER = "INSERT INTO users (name) VALUES ($1)"
TEST_USER_NAME = "Test User"


@pytest.mark.asyncio
async def test_database_connect():
    database = PostgreSQLDatabase(**CREDENTIALS)
    await database.connect()
    assert database.pool is not None
    return database


@pytest.mark.asyncio
async def test_database_acquire():
    database = await test_database_connect()
    connection = await database.acquire()
    assert connection is not None
    await database.close()


@pytest.mark.asyncio
async def test_database_close():
    database = await test_database_connect()
    await database.close()
    assert database.pool._closed


@pytest.mark.asyncio
async def test_database_with():
    async with PostgreSQLDatabase(**CREDENTIALS) as db:
        connection = await db.acquire()
    with pytest.raises(asyncpg.InterfaceError):
        assert not connection.is_open


@pytest.mark.asyncio
async def test_connection_close():
    database = await test_database_connect()
    connection = await database.acquire()
    await connection.close()
    assert not connection.is_open
    await database.close()


@pytest.mark.asyncio
async def test_connection_execute():
    database = await test_database_connect()
    connection = await database.acquire()
    await connection.execute(CREATE_USERS_TABLE)
    await database.close()


@pytest.mark.asyncio
async def test_connection_fetch_row():
    database = await test_database_connect()
    connection = await database.acquire()
    await connection.execute(CREATE_USERS_TABLE)
    await connection.execute(INSERT_USER, TEST_USER_NAME)

    row = await connection.fetch_row("SELECT name FROM users WHERE name=$1 LIMIT 1", TEST_USER_NAME)
    assert row is not None
    assert row["name"] == TEST_USER_NAME

    await database.close()


@pytest.mark.asyncio
async def test_connection_fetch_rows():
    database = await test_database_connect()
    connection = await database.acquire()
    await connection.execute(CREATE_USERS_TABLE)
    await connection.execute(INSERT_USER, TEST_USER_NAME)
    await connection.execute(INSERT_USER, TEST_USER_NAME)
    rows = await connection.fetch_rows("SELECT name FROM users WHERE name=$1 ", TEST_USER_NAME)
    assert len(rows) >= 2
    for row in rows:
        assert row["name"] == TEST_USER_NAME
    await database.close()


@pytest.mark.asyncio
async def test_connection_fetch_val():
    database = await test_database_connect()
    connection = await database.acquire()
    await connection.execute(CREATE_USERS_TABLE)
    await connection.execute(INSERT_USER, TEST_USER_NAME)
    value = await connection.fetch_value("SELECT name FROM users WHERE name=$1 LIMIT 1", TEST_USER_NAME)
    assert value == TEST_USER_NAME
    await database.close()


@pytest.mark.asyncio
async def test_connection_with():
    async with PostgreSQLDatabase(**CREDENTIALS) as db:
        async with await db.acquire() as connection:
            await connection.execute(INSERT_USER, TEST_USER_NAME)
        assert not connection.is_open


class MockAddressField(Model):

    def __init__(self, name: str):
        super().__init__(name, [
            StrField('street')
        ])


class MockUserModel(Model):

    def __init__(self, name: str=None):
        super().__init__(name, [
            StrField('name'),
            MockAddressField('address')
        ])


@pytest.mark.asyncio
async def test_row_to_mdl():
    mock_addresses_table = "DROP TABLE IF EXISTS mock_addresses CASCADE; CREATE TABLE mock_addresses(id serial4 PRIMARY KEY, street varchar(30) NOT NULL)"
    mock_users_table = "DROP TABLE IF EXISTS mock_user CASCADE; CREATE TABLE mock_user(id serial4 PRIMARY KEY, name varchar(30) NOT NULL, address int4, FOREIGN KEY(address) REFERENCES mock_addresses (id))"
    join_query = "SELECT mock_user.name as name, address.street as \"address.street\" FROM mock_user INNER JOIN mock_addresses as address on (mock_user.address = address.id)"

    async with PostgreSQLDatabase(**tedious.config.CONFIG["DB_CREDENTIALS"]) as db:
        async with await db.acquire() as connection:
            await connection.execute(mock_addresses_table)
            await connection.execute(mock_users_table)

            address_id = await connection.fetch_value("INSERT INTO mock_addresses(id, street) VALUES (DEFAULT, $1) RETURNING id", "Dorfstrasse 24")
            await connection.execute("INSERT INTO mock_user(id, name, address) VALUES (DEFAULT, $1, $2)", "Nils", address_id)

            for row in await connection.fetch_rows(join_query):
                mdl = await connection.row_to_mdl(row, MockUserModel())
                assert mdl["name"].value == "Nils"
                assert mdl["address"]["street"].value == "Dorfstrasse 24"
