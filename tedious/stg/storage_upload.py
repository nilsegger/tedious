import io
from uuid import UUID

from PIL import Image
from tedious.sql.interface import SQLConnectionInterface
from tedious.stg.storage import Storage, MimeTypes
from tedious.util import create_uuid
import tedious.config
import os.path
import aiofiles
import hashlib


class ReservationNotFound(Exception):
    """Raised if reservation uuid is invalid."""
    pass


class InvalidByteSize(Exception):
    """Raised if bytes length do not match expected bytes size."""
    pass


class InvalidBytes(Exception):
    """Raised if tedious is unable to verify content of bytes."""
    pass


class InvalidMimeType(Exception):
    """Raised if mime type is not supported."""
    pass


class InvalidFileHash(Exception):
    """Raised when actual md5 hash does not match the expected hash."""
    pass


class StorageUploadController:
    """Uploads file in chunks."""

    CREATE_FILE_CHUNKS_TABLE = """
        CREATE TABLE IF NOT EXISTS file_reservations(
            uuid UUID NOT NULL PRIMARY KEY,
            owner UUID NOT NULL,
            md5 bytea NOT NULL,
            size int4 NOT NULL,
            mime Mime NOT NULL,
            FOREIGN KEY (owner) REFERENCES logins (uuid)
        );
        CREATE TABLE IF NOT EXISTS file_chunks(
            id SERIAL2 NOT NULL PRIMARY KEY,
            reservation UUID NOT NULL,
            index int2 NOT NULL,
            path varchar(100) NOT NULL,
            FOREIGN KEY (reservation) REFERENCES  file_reservations (uuid)
        );
    """

    def __init__(self):
        self.storage = Storage()

    async def _insert_reservation(self, connection: SQLConnectionInterface, uuid: UUID, owner: UUID, md5_hash, byte_size: int, mime: MimeTypes):
        """Insert given values into file_reservations table."""
        stmt = "INSERT INTO file_reservations(uuid, owner, md5, size, mime) VALUES ($1, $2, $3, $4, $5)"
        await connection.execute(stmt, uuid, owner, md5_hash, byte_size, mime.value)

    async def _insert_chunk(self, connection: SQLConnectionInterface, reservation: UUID, index: int, path: str):
        """Inserts new chunk into file_chunks table."""
        stmt = "INSERT INTO file_chunks(reservation, index, path) VALUES ($1, $2, $3)"
        await connection.execute(stmt, reservation, index, path)

    async def query_reservation(self, connection: SQLConnectionInterface, uuid: UUID):
        """Fetches reservation where uuid=uuid"""
        stmt = "SELECT owner, md5, size, mime FROM file_reservations WHERE uuid=$1 LIMIT 1"
        return await connection.fetch_row(stmt, uuid)

    async def _query_chunks(self, connection: SQLConnectionInterface, reservation: UUID):
        """Returns all rows ordered by index with matching reservation fk."""
        stmt = "SELECT path FROM file_chunks WHERE reservation=$1 ORDER BY index"
        return await connection.fetch_rows(stmt, reservation)

    async def _write_to_temporary(self, _bytes) -> str:
        """Writes bytes into temporary file and returns path to file"""
        directory = tedious.config.CONFIG["STG"]["temporary-directory"]
        path = os.path.join(directory, create_uuid().hex)

        async with aiofiles.open(path, mode='wb+') as file:
            await file.write(_bytes)

        return path

    async def reserve(self, connection: SQLConnectionInterface, owner: UUID, md5_hash: bytes, byte_size: int, mime: MimeTypes):
        """Creates reservation in database.

        Args:
            connection: Connection to database.
            owner: Owner of reservation. UUID reference to logins table.
            md5_hash: Expected hash of final product.
            byte_size: Expected byte_size of final image.
            mime: Mime type of bytes.

        Returns:
            UUID of reservation.
        """

        uuid = create_uuid()
        await self._insert_reservation(connection, uuid, owner, md5_hash, byte_size, mime)
        return uuid

    async def write_chunk(self, connection: SQLConnectionInterface, reservation: UUID, _bytes, index: int):
        """Writes chunk into temporary file and uploads reference to database.

        Args:
            connection: Connection to database.
            reservation: UUID of reservation.
            _bytes: Bytes of this chunk.
            index: Index of chunk. Used to order all final chunks.
        """

        path = await self._write_to_temporary(_bytes)
        await self._insert_chunk(connection, reservation, index, path)
        return path

    async def verify_hash(self, _bytes, expected_md5):
        """Compares the md5 hash of bytes and the expected m5 hash.

        Args:
            _bytes: Raw image bytes to be hashed.
            expected_md5: expected md5 hash

        Raises:
            :class:`~.InvalidFileHash`
        """
        md5_hash = hashlib.md5(_bytes).digest()
        if expected_md5 != md5_hash:
            raise InvalidFileHash("Hashes do not match. Actual {} != Expected {}".format(md5_hash, expected_md5))

    async def verify_image(self, _bytes):
        """Verifies if bytes is indeed an image.

        Args:
            _bytes: Image bytes.

        Raises:
            :class:`~.InvalidBytes` if unable to decode bytes.
        """

        try:
            image = Image.open(io.BytesIO(_bytes))
            image.verify()
            image.close()
        except Exception as e:
            raise InvalidBytes("Unable to verify image. {}".format(e))

    async def _combine_chunks(self, connection: SQLConnectionInterface, reservation: UUID, size: int, last_chunk: bytes=None) -> bytearray:
        """Fetches and combines chunks matching reservation. Raises InvalidBytesSize if bytearray exceeds size.

        Args:
            connection: Connection to database.
            reservation: UUID of reservation of which to merge chunks.
            size: Expected size.
            last_chunk: Raw bytes of last chunk which has not been uploaded.

        Returns:
            Final image.

        Raises:
            :class:`~.InvalidByteSize` if merged chunks size does not match expected size.
        """

        _bytes = bytearray()
        for chunk in await self._query_chunks(connection, reservation):
            async with aiofiles.open(chunk["path"], "rb") as file:
                _bytes += await file.read()
                if len(_bytes) > size:
                    raise InvalidByteSize("Bytes exceeds maximum size")
            os.remove(chunk["path"])
        if last_chunk is not None:
            _bytes += last_chunk
        return _bytes

    async def delete_chunk(self, path):
        """Removes chunk from directory."""

        try:
            os.remove(path)
        except FileNotFoundError:
            pass

    async def delete_reservation(self, connection: SQLConnectionInterface, reservation: UUID):
        """Deletes reservation row and associated chunks and their temporary files if they exist.

        Args:
            connection: Connection to database.
            reservation: UUID of reservation.
        """

        stmt = "DELETE FROM file_chunks WHERE reservation=$1 RETURNING path"
        chunks = await connection.fetch_rows(stmt, reservation)
        for chunk in chunks:
            await self.delete_chunk(chunk["path"])

        stmt = "DELETE FROM file_reservations WHERE uuid=$1"
        await connection.execute(stmt, reservation)

    async def finalize(self, connection: SQLConnectionInterface, reservation: UUID, public: bool, last_chunk:bytes=None) -> UUID:
        """Reads chunks, puts them together, validates hash and mime type and returns new uuid of file.

        Args:
            connection: Connection to database.
            reservation: UUID of reservation to finalize.
            public: if true, file will be saved in public directory.
            last_chunk: If available, will be added to the end of the merged chunks.

        Raises:
            ReservationNotFound: if reservation was not found.
            InvalidByteSize: if length of merged chunks does not match the expected length.
            InvalidBytes: if unable to decode content of bytes.
            InvalidMimeType: if mime type is not supported.
            InvalidFileHash: if md5 hash of combined chunks do not match expected md5
        """

        reservation_row = await self.query_reservation(connection, reservation)

        if reservation_row is None:
            raise ReservationNotFound("Reservation with {} could not be found.".format(reservation_row))

        try:
            _bytes = await self._combine_chunks(connection, reservation, reservation_row["size"], last_chunk)
            if len(_bytes) != reservation_row["size"]:
                raise InvalidByteSize("{} does not match the size of {}.".format(len(_bytes), reservation_row["size"]))
            await self.verify_hash(_bytes, reservation_row["md5"])
            await self.verify_image(_bytes)
            return await self.storage.save(connection, reservation_row["owner"], _bytes, MimeTypes(reservation_row["mime"]), public)

        finally:
            await self.delete_reservation(connection, reservation)
