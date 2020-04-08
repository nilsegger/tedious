import pytest

from tedious.stg.storage import Storage, MimeTypes
from tedious.tests.util import TestConnection, AuthUtil, read_file

import tedious.config
import aiofiles
import os.path

tedious.config.load_config('tedious/tests/config.ini')
asset = 'tedious/tests/stg/assets/image1.jpg'


@pytest.mark.asyncio
async def test_save():

    temp_file = await read_file(asset)

    async with TestConnection() as connection:
        owner = await AuthUtil.create_user(connection)
        storage = Storage()
        uuid = await storage.save(connection, owner.uuid, temp_file, MimeTypes.IMAGE_JPEG, True)

        assert uuid is not None
        assert os.path.exists(os.path.join(tedious.config.CONFIG["STG"]["public-directory"], uuid.hex))

        entry = "SELECT owner, public, mime FROM files WHERE uuid=$1"
        row = await connection.fetch_row(entry, uuid)
        assert row['owner'] == owner.uuid
        assert row['public']
        assert row['mime'] == MimeTypes.IMAGE_JPEG.value


@pytest.mark.asyncio
async def test_retrieve():

    temp_file = await read_file(asset)
    async with TestConnection() as connection:
        owner = await AuthUtil.create_user(connection)
        storage = Storage()
        uuid = await storage.save(connection, owner.uuid, temp_file, MimeTypes.IMAGE_JPEG, True)
        _bytes, owner, mime, public = await storage.retrieve(connection, uuid)
        assert _bytes is not None
        assert mime is not None

        async with aiofiles.open(asset, 'rb') as f:
            expected_bytes = await f.read()

        assert expected_bytes == _bytes
        assert mime == MimeTypes.IMAGE_JPEG


@pytest.mark.asyncio
async def test_remove():

    temp_file = await read_file(asset)
    async with TestConnection() as connection:
        owner = await AuthUtil.create_user(connection)
        storage = Storage()
        uuid = await storage.save(connection, owner.uuid, temp_file, MimeTypes.IMAGE_JPEG, True)

        await storage.remove(connection, uuid)

        with pytest.raises(FileNotFoundError):
            await storage.retrieve(connection, uuid)
