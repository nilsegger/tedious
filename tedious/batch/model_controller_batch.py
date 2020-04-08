from typing import Dict
from tedious.batch.interface import BatchInterface
from tedious.logger import Logger
from tedious.mdl.model import Model
from tedious.mdl.model_controller import ModelController, ValidationTypes
from tedious.sql.interface import SQLConnectionInterface


class ModelControllerBatch(BatchInterface, ModelController):
    __slots__ = ('_create_queue', '_update_queue', '_delete_queue')

    def __init__(self, table: str, identifier_key: str, columns_to_fields: Dict[str, str] = None):
        super().__init__(table, identifier_key, columns_to_fields)
        self._create_queue = []
        self._update_queue = []
        self._delete_queue = []

    async def create(self, connection: SQLConnectionInterface, model: Model):
        await self.validate(model, ValidationTypes.CREATE)
        self._create_queue.append(await self._model_to_sql_values(model))
        return model

    async def update(self, connection: SQLConnectionInterface, model: Model, _global: Model = None):
        await self.validate(model, ValidationTypes.UPDATE)
        self._update_queue.append(await self._model_to_sql_values(model))
        return model

    async def delete(self, connection: SQLConnectionInterface, model: Model, _global: Model = None):
        await self.validate(model, ValidationTypes.DELETE)
        self._delete_queue.append((model[self.identifier_key].value,))
        return model

    async def _commit_revertable(self, connection: SQLConnectionInterface, logger: Logger):
        pass

    async def _commit_unrevertable(self, connection: SQLConnectionInterface, logger: Logger):
        if len(self._create_queue) > 0:
            await connection.execute_many(await self._insert_stmt(), self._create_queue)
        if len(self._update_queue) > 0:
            await connection.execute_many(await self._update_stmt(), self._update_queue)
        if len(self._delete_queue) > 0:
            await connection.execute_many(await self._delete_stmt(), self._delete_queue)

    async def revert(self, connection: SQLConnectionInterface, logger: Logger):
        pass
