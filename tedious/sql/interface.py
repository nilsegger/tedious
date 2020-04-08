from typing import List, Tuple

from tedious.mdl.model import Model


class SQLConnectionInterface:
    """Interface which defines most useful methods for executing SQL statements."""

    @property
    def is_open(self) -> bool:
        """Checks if connection is still open.

        Returns:
            Bool if connection is open.
        """

        raise NotImplementedError

    async def execute(self, statement: str, *values) -> None:
        """Executes sql statement.

        Args:
            statement: SQL statement.
            *values: Tuple of values that will be formatted into the SQL statement.
        """

        raise NotImplementedError

    async def execute_many(self, statement: str, values: List[Tuple]) -> None:
        """Execute many is not mean to execute many different SQL Statements, but to execute same statement multiple times with different values."""

        raise NotImplementedError

    async def fetch_value(self, statement: str, *values):
        """Returns single value from a statement.

        Args:
            statement: SQL statement to execute.
            *values: Values to fill into SQL statement.

        Returns:
            Single value retrieved from SQL statement.
        """

        raise NotImplementedError

    async def fetch_row(self, statement: str, *values):
        """Retrieves single row.

        Args:
            statement: SQL statement to execute.
            *values: Values to fill into SQL statement.

        Returns:
            Returns single row.
        """

        raise NotImplementedError

    async def fetch_model(self, mdl: Model, statement: str, *values) -> Model:
        """Fetches single model. Uses fetch_row and simply converts it into a model.

        Args:
            mdl: Instance of :class:`~tedious.mdl.model.Model` which will read in the retrieved values.
            statement: SQL statement to execute.
            *values: Values to fill into statement.

        Returns:
            Model with new values.
        """

        row = await self.fetch_row(statement, *values)
        if row is None:
            return None
        return await self.row_to_mdl(row, mdl)

    async def fetch_rows(self, statement: str, *values):
        """Retrieves multiple rows.

        Args:
            statement: SQL statement to execute.
            *values: Values to fill into statement.

        Returns:
            List of row.
        """

        raise NotImplementedError

    async def fetch_models(self, mdl_class: type(Model), statement: str, *values) -> List[Model]:
        """Fetches rows and converts each row into a model.

        Args:
            mdl_class: Class to be used for each row.
            statement: SQL statement to execute.
            *values: Values to fill into statement.

        Returns:
            List of models.
        """

        return [await self.row_to_mdl(row, mdl_class()) for row in await self.fetch_rows(statement, *values)]

    async def row_to_mdl(self, row, mdl: Model) -> Model:
        """Converts a row into a model.

        Args:
            row: Fetched row.
            mdl: Instance of model to fill in.

        Returns:
            Model
        """

        raise NotImplementedError

    async def close(self) -> None:
        """Closes connection."""

        raise NotImplementedError


class SQLInterface:
    """Connection to database. Which should be able to spawn short-lived connections."""

    async def connect(self) -> None:
        """Connects to database."""

        raise NotImplementedError

    async def acquire(self) -> SQLConnectionInterface:
        """Spawns short-lived connection.

        Returns:
            Instance of :class:`~.SQLConnectionInterface`
        """
        raise NotImplementedError

    async def close(self) -> None:
        """Closes the connection to the database."""

        raise NotImplementedError
