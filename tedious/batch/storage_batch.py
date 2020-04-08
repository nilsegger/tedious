from uuid import UUID

from tedious.batch.interface import BatchInterface
from tedious.logger import Logger
from tedious.sql.interface import SQLConnectionInterface
import os

from tedious.stg.storage import Storage, MimeTypes


class StorageBatch(Storage, BatchInterface):

    __slots__ = ('_save_queue', '_remove_queue')

    def __init__(self):
        super().__init__()
        self._save_queue = []
        self._remove_queue = []

    async def _insert(self, connection: SQLConnectionInterface, uuid: UUID, owner: UUID, path: str, mime_type: MimeTypes, is_public: bool):
        """
            Does not make any changes, simply saves _insert into _save_queue
        """
        self._save_queue.append((uuid, owner, path, mime_type.value, is_public))

    async def remove(self, connection: SQLConnectionInterface, uuid: UUID):
        self._remove_queue.append(uuid)

    async def _commit_revertable(self, connection: SQLConnectionInterface, logger: Logger):
        """
            Uploads files from save_queue and appends them to the saved list.
        """
        await connection.execute_many("INSERT INTO files(uuid, owner, path, mime, public) VALUES ($1, $2, $3, $4, $5)", self._save_queue)

    async def _commit_unrevertable(self, connection: SQLConnectionInterface, logger: Logger):
        """
            Removes files from remove_queue, once removed these files are lost forever
        """
        for uuid in self._remove_queue:
            await super().remove(connection, uuid)

    async def revert(self, connection: SQLConnectionInterface, logger: Logger):
        """
            Removes freshly saved files.
            Since its impossible to know which one of the _save_queue failed, each single one will be tried.
        """
        for queued in self._save_queue:
            try:
                await super().remove(connection, queued[0])
            except FileNotFoundError:
                continue

            if os.path.exists(queued[2]):
                os.remove(queued[2])

