from typing import List, Tuple
import asyncpg
from .interface import SQLConnectionInterface, SQLInterface
import asyncio
import tedious.config
from ..mdl.model import Model, IOModel
from ..util import KeyPathsIter


class Connection(SQLConnectionInterface):
    """Connection retrieved from a pool."""

    def __init__(self, connection: asyncpg.connection.Connection, pool: asyncpg.pool.Pool):
        self._connection = connection
        self._parent_pool = pool
        self._closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @property
    def is_open(self) -> bool:
        """

        Returns:
            if connection hasn't been closed manually,
            the actual connection will be checked,
            otherwise the _closed attribute.
        """

        if not self._closed:
            return not self._connection.is_closed()
        else:
            return not self._closed

    async def execute(self, statement: str, *values) -> None:
        """Executes SQL statement.

        Args:
            statement: SQL statement to be executed.
            values: Values to be inserted into statement.
        """

        await self._connection.execute(statement, *values)

    async def execute_many(self, statement: str, values: List[Tuple]) -> None:
        """Executes statement with multiple different valuesExecutes statement with multiple different values."""

        await self._connection.executemany(statement, values)

    async def fetch_value(self, statement: str, *values):
        """Fetches single value.

        Args:
            statement: SQL statement to be executed.
            values: Values to be inserted into statement.

        Returns:
            Single value retrieved from database.
        """

        return await self._connection.fetchval(statement, *values)

    async def fetch_row(self, statement: str, *values):
        """Fetches single row from database.

        Args:
            statement: SQL statement to execute.
            values: values to be inserted into statement.

        Returns:
            Single row from database.
        """

        return await self._connection.fetchrow(statement, *values)

    async def fetch_rows(self, statement: str, *values):
        """Fetches list of rows.

        Args:
            statement: SQL statement to be executed.
            values: Values to be inserted into statement.

        Returns:
            List of rows.
        """

        return await self._connection.fetch(statement, *values)

    @staticmethod
    async def _recursively_set_values(field:IOModel, _iter: KeyPathsIter, value):
        """Sets value according to key paths iterator."""
        if _iter is None:
            await field.input(value)
        else:
            for key, __iter in _iter:
                await Connection._recursively_set_values(field[key], __iter, value)

    async def row_to_mdl(self, row: asyncpg.Record, mdl: Model) -> Model:
        """Converts a asyncpg.Record into a ModelInterface, it does this recursively.

        Args:
            row (:class:`asyncpg.Record`): Retrieved row from database.
            mdl (:class:`~tedious.mdl.model.Model`): Model to be set.

        Returns:
            Model
        """

        for key in row.keys():
            # _iter will always only return single item before raising StopIteration,
            # to prevent this, values would have to be grouped before doing this
            _iter = KeyPathsIter([key])
            for field, __iter in _iter:
                # Here again __iter will only return a single value, before raising StopIteration
                await Connection._recursively_set_values(mdl[field], __iter, row[key])

        return mdl

    async def close(self) -> None:
        """Releases connection from Connection pool."""

        self._closed = True
        await self._parent_pool.release(self._connection, timeout=int(tedious.config.CONFIG['DB']['close-timeout']))


class PostgreSQLDatabase(SQLInterface):
    """Long lived connection to database. Opens pool to spawn multiple short-lived connection to database."""

    __slots__ = ('pool', 'database', 'user', 'password', 'port')

    def __init__(self, database, user, password, port=5432):
        self.pool = None
        self.database = database
        self.user = user
        self.password = password
        self.port = port

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self) -> None:
        """
        Initializes connection pool to database.
        https://magicstack.github.io/asyncpg/current/usage.html#connection-pools
        """
        self.pool = await asyncpg.create_pool(database=self.database, user=self.user, password=self.password, port=self.port)

    async def acquire(self) -> SQLConnectionInterface:
        """Spawns short-lived connection to database from pool.

        Returns:
            An instance of :class:`~.Connection`.
        """

        return Connection(await self.pool.acquire(), self.pool)

    async def close(self) -> None:
        """Waits a few seconds for the pool to close, then forces each connection to close."""

        try:
            await asyncio.wait_for(self.pool.close(), int(tedious.config.CONFIG['DB']['close-timeout']))
        except asyncio.TimeoutError:
            self.pool.terminate()
