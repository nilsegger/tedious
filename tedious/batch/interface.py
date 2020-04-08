from tedious.logger import Logger
from tedious.sql.interface import SQLConnectionInterface


class BatchInterface:

    """
        A batch should enhance performance by grouping requests
    """

    async def _commit_revertable(self, connection: SQLConnectionInterface, logger: Logger):
        """
            Execute revertable actions
        """
        raise NotImplementedError

    async def _commit_unrevertable(self, connection: SQLConnectionInterface, logger: Logger):
        """
            Execute unrevertable actions.
        """
        raise NotImplementedError

    async def commit(self, connection: SQLConnectionInterface, logger: Logger):
        """
            Commits group of actions which can be reverted
        """
        try:
            await self._commit_revertable(connection, logger)
        except Exception as e:
            await self.revert(connection, logger)
            raise e

        await self._commit_unrevertable(connection, logger)

    async def revert(self, connection: SQLConnectionInterface, logger: Logger):
        """
            Revert changes of executed batches.
        """
        raise NotImplementedError
