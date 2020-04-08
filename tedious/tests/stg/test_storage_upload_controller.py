import pytest
import tedious.config
from tedious.auth.auth import Auth
from tedious.stg.storage import MimeTypes, Storage
from tedious.stg.storage_upload import StorageUploadController
from tedious.util import create_uuid
import hashlib
import os

from tedious.tests.util import TestConnection, read_file

tedious.config.load_config('tedious/tests/config.ini')

test_asset = 'tedious/tests/assets/test.jpeg'
CHUNK_SIZE = 512


@pytest.mark.asyncio
async def test_reserve():
    async with TestConnection() as connection:
        requester = await Auth().register(connection, create_uuid().hex[:30], "12345678", 'admin')
        _bytes = await read_file(test_asset)
        md5 = hashlib.md5(_bytes).digest()

        controller = StorageUploadController()
        uuid = await controller.reserve(connection, requester.uuid, md5, len(_bytes), MimeTypes.IMAGE_JPEG)
        assert uuid is not None


@pytest.mark.asyncio
async def test_write_chunk():
    async with TestConnection() as connection:
        requester = await Auth().register(connection, create_uuid().hex[:30], "12345678", 'admin')
        _bytes = await read_file(test_asset)
        md5 = hashlib.md5(_bytes).digest()
        controller = StorageUploadController()
        uuid = await controller.reserve(connection, requester.uuid, md5, len(_bytes), MimeTypes.IMAGE_JPEG)

        path = await controller.write_chunk(connection, uuid, _bytes[:CHUNK_SIZE], 0)
        assert os.path.exists(path)


@pytest.mark.asyncio
async def test_finalize():
    async with TestConnection() as connection:
        requester = await Auth().register(connection, create_uuid().hex[:30], "12345678", 'admin')
        _bytes = await read_file(test_asset)
        md5 = hashlib.md5(_bytes).digest()
        controller = StorageUploadController()
        reservation_uuid = await controller.reserve(connection, requester.uuid, md5, len(_bytes), MimeTypes.IMAGE_JPEG)

        chunk_paths = []
        for i in range(int(len(_bytes) / CHUNK_SIZE) + 1):
            path = await controller.write_chunk(connection, reservation_uuid, _bytes[i * CHUNK_SIZE:i * CHUNK_SIZE + CHUNK_SIZE], 0)
            chunk_paths.append(path)

        final_uuid = await controller.finalize(connection, reservation_uuid, True)

        finalized_bytes, owner, mime, public = await Storage().retrieve(connection, final_uuid)

        assert mime == MimeTypes.IMAGE_JPEG
        assert _bytes == finalized_bytes

        for path in chunk_paths:
            assert not os.path.exists(path)
