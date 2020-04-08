from enum import Enum
from typing import Tuple
from uuid import UUID
import aiofiles
import asyncpg

import tedious.config
from tedious.sql.interface import SQLConnectionInterface
import os

from tedious.util import create_uuid


class MimeTypes(Enum):
    """Mime types according to this_.

    IMAGE_PNG, IMAGE_JPEG

    .. _this: https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types"""

    IMAGE_PNG = 'image/png'
    IMAGE_JPEG = 'image/jpeg'


class Storage:
    """Storage is capable of saving, retrieving and removing files."""

    CREATE_FILES_TABLE = """
        CREATE TYPE Mime AS ENUM ('image/png', 'image/jpeg');
        CREATE TABLE IF NOT EXISTS files(
            uuid UUID PRIMARY KEY NOT NULL,
            owner UUID NOT NULL REFERENCES logins(uuid),
            public boolean NOT NULL,
            path varchar(100) NOT NULL,
            mime Mime NOT NULL
        );
    """

    async def _insert(self, connection: SQLConnectionInterface, uuid: UUID, owner: UUID, path: str, mime_type: MimeTypes, is_public: bool):
        """Inserts new row into files table."""

        stmt = "INSERT INTO files(uuid, owner, public, path, mime) VALUES ($1, $2, $3, $4, $5)"
        await connection.execute(stmt, uuid, owner, is_public, path, mime_type.value)

    @staticmethod
    async def read_file(path, clean_up=False) -> bytes:
        """Reads file using aiofiles adn returns bytes.

        Args:
            path (str): Path to file.
            clean_up (bool): if true, file is removed after reading it.

        Returns:
            Bytes contained in file.
        """

        async with aiofiles.open(path, mode='rb') as file:
            _bytes = await file.read()

        # TODO users should not wait for os to delete file, create task
        if clean_up:
            await Storage._delete_file(path)

        return _bytes

    @staticmethod
    async def _delete_file(path):
        os.remove(path)

    async def query_by_uuid(self, connection: SQLConnectionInterface, uuid: UUID) -> asyncpg.Record:
        """Returns row which matches uuid.

        Args:
            connection (:class:`~tedious.sql.interface.SQLConnectionInterface`): Connection to database.
            uuid (UUID): UUID which has to match row.

        Returns:
            Row matching given UUID.
        """

        stmt = "SELECT owner, public, path, mime FROM files WHERE uuid=$1"
        return await connection.fetch_row(stmt, uuid)

    async def save(self, connection: SQLConnectionInterface, owner: UUID, _bytes: bytes, mime_type: MimeTypes, is_public: bool) -> UUID:
        """Saves bytes to directory and references it in database.

        Args:
            connection (:class:`~tedious.sql.interface.SQLConnectionInterface`): Connection to database.
            owner (UUID): UUID of user referencing login.
            _bytes: Bytes of file.
            mime_type (:class:`~.MimeTypes`): Mime type of bytes.
            is_public (bool): If true, bytes will be written to public directory.

        Returns:
            UUID referencing file in files table.
        """

        uuid = create_uuid()
        directory = tedious.config.CONFIG["STG"]["public-directory"] if is_public else tedious.config.CONFIG["STG"]["private-directory"]
        path = os.path.join(directory, uuid.hex)
        async with aiofiles.open(path, mode='wb+') as file:
            await file.write(_bytes)
        await self._insert(connection, uuid, owner, path, mime_type, is_public)
        return uuid

    async def retrieve(self, connection: SQLConnectionInterface, uuid: UUID) -> Tuple[bytes, UUID, MimeTypes, bool]:
        """Resolves uuid to path and mime and returns loaded bytes.

        Args:
            connection: Connection to database.
            uuid: UUID of file to retrieve.

        Returns:
            Tuple containing file bytes, file mime and bool stating if file is public.

        Raises:
            FileNotFound if file was not found in database.
        """

        row = await self.query_by_uuid(connection, uuid)
        if row is None:
            raise FileNotFoundError("File with uuid '{}' was not found.".format(uuid))

        return await self.read_file(row["path"]), row["owner"], MimeTypes._value2member_map_[row["mime"]], row["public"]

    async def remove(self, connection: SQLConnectionInterface, uuid: UUID):
        """Deletes file from directory and removes row referencing it.

        Args:
            connection: Connection to database.
            uuid: File UUID to remove.
        """

        row = await self.query_by_uuid(connection, uuid)
        if row is None:
            raise FileNotFoundError("File with uuid '{}' was not found.".format(uuid))

        await self._delete_file(row["path"])


