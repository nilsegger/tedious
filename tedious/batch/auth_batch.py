from datetime import datetime
from tedious.batch.interface import BatchInterface
from tedious.auth.auth import Auth, Requester
from tedious.logger import Logger
from tedious.sql.interface import SQLConnectionInterface


class AuthBatch(Auth, BatchInterface):
    """
        Batch implementation of auth. Group together multiple insert and update to execute at once.
    """
    __slots__ = ('_registered_queue', '_update_queue', '_delete_queue')

    def __init__(self):
        super().__init__()
        self._register_queue = []
        self._update_queue = []
        self._delete_queue = []

    async def _insert_authentication(self, connection: SQLConnectionInterface, requester: Requester, hashed_password: bytes, salt: bytes, mem_cost: int, rounds: int) -> Requester:
        self._register_queue.append((requester.uuid, requester.username, requester.role, hashed_password, salt, mem_cost, rounds))
        return requester

    async def _update_authentication(self, connection: SQLConnectionInterface, requester: Requester, hashed_password: bytes = None, salt: bytes = None, mem_cost: int = None,
                                     rounds: int = None, refresh_token: str = None, refresh_token_expires: datetime = None,
                                     refresh_token_revoked: bool = None) -> None:
        self._update_queue.append((requester.username, requester.role, hashed_password, salt, mem_cost, rounds, refresh_token, refresh_token_expires, refresh_token_revoked, requester.uuid))

    async def delete(self, connection: SQLConnectionInterface, requester: Requester) -> None:
        """
            Appends uuid to array of requester to be deleted.
        Args:
            requester: User identification. UUID must be set.
        """
        assert requester.uuid is not None
        self._delete_queue.append((requester.uuid, ))

    async def _commit_revertable(self, connection: SQLConnectionInterface, logger: Logger):
        stmt = "INSERT INTO logins(uuid, username, role, password, salt, mem_cost, rounds) VALUES ($1, $2, $3, $4, $5, $6, $7);"
        await connection.execute_many(stmt, self._register_queue)

    async def _commit_unrevertable(self, connection: SQLConnectionInterface, logger: Logger):
        stmt = "UPDATE logins SET username=COALESCE($1, username), role=COALESCE($2, role), password=COALESCE($3, password), salt=COALESCE($4, salt), mem_cost=COALESCE($5, mem_cost), rounds=COALESCE($6, rounds), refresh_token=COALESCE($7, refresh_token), refresh_token_expires=COALESCE($8, refresh_token_expires), refresh_token_revoked=COALESCE($9, refresh_token_revoked) WHERE uuid=$10"
        await connection.execute_many(stmt, self._update_queue)

        stmt = "DELETE FROM logins WHERE uuid=$1"
        await connection.execute_many(stmt, self._delete_queue)

    async def revert(self, connection: SQLConnectionInterface, logger: Logger):
        """
            Deletes all users which have been queued by insert.
        """
        for queued in self._register_queue:
            await super().delete(connection, Requester(uuid=queued[0]))

