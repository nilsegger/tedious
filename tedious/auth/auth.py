import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from tedious.auth.jwt import JWTAuth
from tedious.sql.interface import SQLConnectionInterface
import tedious.config
import asyncpg

from tedious.util import create_uuid


class Requester:
    """An instance of requester contains all necessary data to identify a user. UUID, username and role."""

    __slots__ = ('uuid', 'username', 'role')

    def __init__(self, uuid=None, username=None, role=None):
        self.uuid = uuid
        self.username = username
        self.role = role


class UserNotFound(Exception):
    """Raised when user was not found in database."""
    pass


class InvalidPassword(Exception):
    """Thrown if passwords do not match."""
    pass


class RefreshTokenNotFound(Exception):
    """Thrown if refresh token can not be found in database."""
    pass


class RefreshTokenExpired(Exception):
    """Thrown if refresh token expired."""
    pass


class RefreshTokenRevoked(Exception):
    """Thrown if refresh token has been manually revoked."""
    pass


class Auth(JWTAuth):
    """
        Implementation of JWTAuth which uses a table of users for :class:`~.Auth.register` and :class:`~.Auth.authenticate`.
    """

    # Use formula: int(4*(int(nBytes/3)) + 1 to predict base64 size of refresh_token, 683 is prediction for a refresh token of size 512
    CREATE_LOGINS_TABLE = """
        CREATE TABLE IF NOT EXISTS logins(
            uuid UUID PRIMARY KEY NOT NULL,
            username varchar(30) NOT NULL,
            role varchar(15) NOT NULL,
            password bytea NOT NULL,
            salt bytea NOT NULL,
            mem_cost int2 NOT NULL,
            rounds int2 NOT NULL,
            refresh_token varchar(683),
            refresh_token_expires timestamp,
            refresh_token_revoked boolean
        )
    """

    DROP_AUTH_TABLE_STMT = "DROP TABLE IF EXISTS logins"

    @staticmethod
    def _hash_password(password: str, salt: bytes, memory_cost=16, rounds=8):
        """Generates hash of password + salt with scrypt, to better understand the parameters visit https://blog.filippo.io/the-scrypt-parameters/

        Args:
            password: Password of user.
            salt: Random salt to increase password strength.
            memory_cost: Memory cost to be used by SCRYPT.
            rounds: Hash iterations.

        Returns:
            Secure SCRYPT hash of password and salt.
        """

        return hashlib.scrypt(password=bytes(password, 'utf-8'), salt=salt, n=memory_cost, r=rounds, p=1)

    async def _uuid_exists(self, connection: SQLConnectionInterface, _uuid: uuid.UUID) -> bool:
        """Checks if user with uuid already exists.

        Args:
            connection (:class:`~tedious.sql.interface.SQLConnectionInterface`): Connection to database.
            _uuid: uuid to check

        Returns:
              True if user exists, else False.
        """

        stmt = "SELECT exists (SELECT 1 FROM logins WHERE uuid=$1 LIMIT 1)"
        return await connection.fetch_value(stmt, _uuid)

    async def _insert_authentication(self, connection: SQLConnectionInterface, requester: Requester, hashed_password: bytes, salt: bytes,
                                     mem_cost: int,
                                     rounds: int) -> Requester:
        """Inserts new user into logins table.

        Args:
            connection (:class:`~tedious.sql.interface.SQLConnectionInterface`): Connection to database.
            requester (:class:`~tedious.asgi.requester_interface.Requester`): User identification.
            hashed_password: Hashed password of user.
            salt: Salt which was used to generate hashed password.
            mem_cost: Memory which was used to generate hashed password.
            rounds: Hash iterations which were used to generate hashed password.

        Returns:
            requester
        """

        stmt = "INSERT INTO logins(uuid, username, role, password, salt, mem_cost, rounds) VALUES ($1, $2, $3, $4, $5, $6, $7);"
        await connection.execute(stmt, requester.uuid, requester.username, requester.role, hashed_password, salt, mem_cost, rounds)
        return requester

    async def _update_authentication(self, connection: SQLConnectionInterface, requester: Requester, hashed_password: bytes = None,
                                     salt: bytes = None,
                                     mem_cost: int = None,
                                     rounds: int = None,
                                     refresh_token: str = None, refresh_token_expires: datetime = None,
                                     refresh_token_revoked: bool = None) -> None:
        """Updates entry in table where uuid = requester.uuid,
            if param is None COALESCE chooses second option, which will be the current entry in column.

        Args:
            connection (:class:`~tedious.sql.interface.SQLConnectionInterface`): Connection to database.
            requester (:class:`~tedious.asgi.requester_interface.Requester`): User identification.
            hashed_password: Hashed password of user.
            salt: Salt which was used to generate hashed password.
            mem_cost: Memory which was used to generate hashed password.
            rounds: Hash iterations which were used to generate hashed password.
            refresh_token: Refresh token of user.
            refresh_token_expires: datetime of point in time where refresh token will expire
            refresh_token_revoked: bool if refresh token was manually revoked.

        Returns:
            None
        """

        stmt = "UPDATE logins SET username=COALESCE($1, username), role=COALESCE($2, role), password=COALESCE($3, password), salt=COALESCE($4, salt), mem_cost=COALESCE($5, mem_cost), rounds=COALESCE($6, rounds), refresh_token=COALESCE($7, refresh_token), refresh_token_expires=COALESCE($8, refresh_token_expires), refresh_token_revoked=COALESCE($9, refresh_token_revoked) WHERE uuid=$10"
        await connection.execute(stmt, requester.username, requester.role, hashed_password, salt, mem_cost, rounds, refresh_token,
                                 refresh_token_expires, refresh_token_revoked, requester.uuid)

    async def _query_where_username(self, connection: SQLConnectionInterface, username) -> asyncpg.Record:
        """Returns row of logins where username = username.

        Args:
            connection (:class:`~tedious.sql.interface.SQLConnectionInterface`): Connection to database.
            username: Username to query for.

        Returns:
            Row of username or None if row does not exist.
        """

        stmt = "SELECT uuid, role, password, salt, mem_cost, rounds FROM logins WHERE username=$1 LIMIT 1"
        return await connection.fetch_row(stmt, username)

    async def _query_where_refresh_token(self, connection: SQLConnectionInterface, refresh_token: str) -> asyncpg.Record:
        """Returns row where refresh token matches column.

        Args:
            refresh_token: Refresh token to query for.

        Returns:
            Row where refresh tokens match, if no row was found None
        """

        stmt = "SELECT uuid, username, role, refresh_token_expires, refresh_token_revoked FROM logins WHERE refresh_token=$1 LIMIT 1"
        return await connection.fetch_row(stmt, refresh_token)

    async def register(self, connection: SQLConnectionInterface, username, password, role) -> Requester:
        """Registers user and creates new access token.

       Args:
           connection (:class:`~tedious.sql.interface.SQLConnectionInterface`): Connection to database.
           username: username of user.
           password: password to hash.
           role: role of user.

        Returns:
            Returns :class:`~.Requester` containing new uuid of user.

        Raises:
            ValueError if uuid does already exist.
        """

        _uuid = create_uuid()

        if await self._uuid_exists(connection, _uuid):
            raise ValueError("UUID already exists.")

        requester = Requester(uuid=_uuid, username=username, role=role)
        salt = secrets.token_bytes(32)
        mem_cost = int(tedious.config.CONFIG["SCRYPT"]["mem_cost"])
        rounds = int(tedious.config.CONFIG["SCRYPT"]["rounds"])
        password_hash = self._hash_password(password, salt)
        await self._insert_authentication(connection, requester, password_hash, salt, mem_cost, rounds)
        return requester

    async def update(self, connection: SQLConnectionInterface, requester: Requester, username: str=None, password=None, role=None):
        """Updates non null values.

        Args:
            connection (:class:`~tedious.sql.interface.SQLConnectionInterface`): Connection to database.
            username: Username of user, if null will not be updated.
            password: If not null, will be hashed and updated.
            role: If not null, will be set as new role.
        """
        if username is not None:
            requester.username = username
        if role is not None:
            requester.role = role
        salt = None
        mem_cost = None
        rounds = None
        password_hash = None
        if password is not None:
            salt = secrets.token_bytes(32)
            mem_cost = int(tedious.config.CONFIG["SCRYPT"]["mem_cost"])
            rounds = int(tedious.config.CONFIG["SCRYPT"]["rounds"])
            password_hash = self._hash_password(password, salt)
        await self._update_authentication(connection, requester, password_hash, salt, mem_cost, rounds)

    async def update_role(self, connection: SQLConnectionInterface, requester: Requester, role: str) -> None:
        """Updates role of requester.

        Args:
            connection (:class:`~tedious.sql.interface.SQLConnectionInterface`): Connection to database.
            requester (:class:`~.Requester`): User identification.
            role: New role of requester.

        Returns:
            None
        """

        await self._update_authentication(connection, Requester(uuid=requester.uuid, role=role))

    async def delete(self, connection: SQLConnectionInterface, requester: Requester) -> None:
        """Deletes requester account.

        Args:
            connection (:class:`~tedious.sql.interface.SQLConnectionInterface`): Connection to database.
            requester (:class:`~.Requester`): User identification.
        """

        stmt = "DELETE FROM logins WHERE uuid=$1"
        await connection.execute(stmt, requester.uuid)

    async def authenticate(self, connection: SQLConnectionInterface, username: str, password: str) -> Requester:
        """Firstly tries to find username in table, if query returns empty, user does not exist and to prevent user enumeration a password is fake hashed.
            if the user is found, the salt is extracted and used to generate proper hash, this hash is then compared to the hash from the table.

        Args:
            connection (:class:`~tedious.sql.interface.SQLConnectionInterface`): Connection to database.
            username: Username given by user
            password: password given by requester.

        Returns:
            Instance of :class:`~.Requester` identifying user.

        Raises:
            InvalidPassword if password was incorrect.
            UserNotFound if given username does not exist in table

        todo:
            recognise if user is being brute-forced, if so, increase time it takes to finish request (time.sleep)
        """

        row = await self._query_where_username(connection, username)
        if row is None:
            self._hash_password(password, "fake-salt".encode('utf-8'))
            raise UserNotFound()
        else:
            untrusted_hashed_password = self._hash_password(password, row['salt'], row['mem_cost'], row['rounds'])
            if untrusted_hashed_password != row['password']:
                raise InvalidPassword()
            return Requester(uuid=row['uuid'], role=row["role"])

    async def create_refresh_token(self, connection: SQLConnectionInterface, requester: Requester) -> str:
        """Creates random string and saves refresh token.

        Args:
            connection (:class:`~tedious.sql.interface.SQLConnectionInterface`): Connection to database.
            requester (:class:`~.Requester`): User identification.

        Returns:
            Randomly generated refresh token.
        """

        token = secrets.token_urlsafe(int(tedious.config.CONFIG['TOKEN']['refresh-token-bytes']))
        lifespan = int(tedious.config.CONFIG['TOKEN']['refresh-token-lifespan'])
        await self.save_refresh_token(connection, requester, token, datetime.now() + timedelta(seconds=lifespan))
        return token

    async def save_refresh_token(self, connection: SQLConnectionInterface, requester: Requester, refresh_token: str, expires: datetime) -> None:
        """Updates row entry to include refresh token, refresh_token_expires and refresh_token_expired.

        Args:
            connection (:class:`~tedious.sql.interface.SQLConnectionInterface`): Connection to database.
            requester (:class:`~.Requester`): User identification.
            refresh_token: Actual refresh token.
            expires: Point in time when token is supposed to expire.
        """

        await self._update_authentication(connection, requester=requester, refresh_token=refresh_token,
                                          refresh_token_expires=expires,
                                          refresh_token_revoked=False)

    async def retrieve_refresh_token(self, connection: SQLConnectionInterface, requester: Requester) -> str:
        """Retrieves existing refresh token for requester.

        Args:
            connection (:class:`~tedious.sql.interface.SQLConnectionInterface`): Connection to database.
            requester (:class:`~.Requester`): User identification.

        Returns:
            Refresh token of requester.
        """

        return await connection.fetch_value(
            "SELECT refresh_token FROM logins WHERE uuid=$1 AND refresh_token_expires > $2 LIMIT 1",
            requester.uuid, datetime.now())

    async def validate_refresh_token(self, connection: SQLConnectionInterface, refresh_token: str) -> Requester:
        """Validates refresh token for expiration date or if it has been manually revoked.

        Args:
            connection (:class:`~tedious.sql.interface.SQLConnectionInterface`): Connection to database.
            refresh_token: refresh token received by user

        Raises:
            RefreshTokenNotFound: if token does not exist
            RefreshTokenExpired: if token has expired
            RefreshTokenRevoked: if token has been manually revoked
        """

        row = await self._query_where_refresh_token(connection, refresh_token)
        if row is None:
            raise RefreshTokenNotFound()
        elif datetime.now() > row['refresh_token_expires']:
            raise RefreshTokenExpired()
        elif row['refresh_token_revoked']:
            raise RefreshTokenRevoked()
        return Requester(uuid=row['uuid'], username=row['username'], role=row["role"])

    async def revoke_refresh_token(self, connection: SQLConnectionInterface, requester: Requester) -> None:
        """Revokes refresh token by setting refresh_token_revoked to true.

        Args:
            connection (:class:`~tedious.sql.interface.SQLConnectionInterface`): Connection to database.
            requester (:class:`~.Requester`): User identification.
        """

        await self._update_authentication(connection, requester, refresh_token_revoked=True)
