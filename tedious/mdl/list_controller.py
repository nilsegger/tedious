from typing import List

from tedious.mdl.model_controller import ModelController

from tedious.mdl.model import Model
from tedious.sql.interface import SQLConnectionInterface


class ListController:
    __slots__ = ('_model_class',)

    def __init__(self, model_class: type(Model)):
        self._model_class = model_class

    async def _select_stmt(self, limit, offset, join_foreign_keys) -> str:
        """Returns select statement as str."""
        raise NotImplementedError

    async def _select_values(self):
        """Returns tuple of values needed for the select statement, if None, values wont be passed to query."""
        return None

    async def get_orders(self):
        """Returns list of tuples containing column and sorting direction."""
        pass

    async def get(self, connection: SQLConnectionInterface, limit=25, offset=0,
                  join_foreign_keys=False) -> List[Model]:
        """
            Fetches multiple rows from database.
        :param limit: N rows to return, if orders is not given, rows will never be returned in same order.
                        order is set automatically to identifier key if not given
        :param offset: N rows to skip
        :param join_foreign_keys: If true, select statement should join foreign keys, must be overriden.
        :return: Returns List of models
        """

        stmt = await self._select_stmt(limit, offset, join_foreign_keys)
        values = await self._select_values()
        if values is None:
            return await connection.fetch_models(self._model_class, stmt)
        else:
            return await connection.fetch_models(self._model_class, stmt,
                                                 *values)
