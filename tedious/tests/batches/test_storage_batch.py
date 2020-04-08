import pytest
import tedious.config
from tedious.batch.storage_batch import StorageBatch
from tedious.stg.storage import Storage, MimeTypes
from tedious.tests.util import read_file, TestConnection, AuthUtil, MockLogger

tedious.config.load_config('tedious/tests/config.ini')

asset_file = 'tedious/tests/stg/assets/image1.jpg'


@pytest.mark.asyncio
async def test_commit():
    save_temp_file = await read_file(asset_file)
    remove_temp_file = await read_file(asset_file)


    async with TestConnection() as connection:
        owner = await AuthUtil.create_user(connection)
        storage = Storage()
        to_be_removed = await storage.save(connection, owner.uuid, remove_temp_file, MimeTypes.IMAGE_JPEG, True)

        batch = StorageBatch()
        uuid = await batch.save(connection, owner.uuid, save_temp_file, MimeTypes.IMAGE_JPEG, True)
        await batch.remove(connection, to_be_removed)

        await batch._commit_revertable(connection, MockLogger())
        await batch._commit_unrevertable(connection, MockLogger())

        await storage.retrieve(connection, uuid)

        with pytest.raises(FileNotFoundError):
            await storage.retrieve(connection, to_be_removed)


@pytest.mark.asyncio
async def test_revert():
    save_temp_file = await read_file(asset_file)

    async with TestConnection() as connection:
        owner = await AuthUtil.create_user(connection)
        batch = StorageBatch()
        uuid = await batch.save(connection, owner.uuid, save_temp_file, MimeTypes.IMAGE_JPEG, True)
        await batch._commit_revertable(connection, MockLogger())

        await batch.revert(connection, MockLogger())

        with pytest.raises(FileNotFoundError):
            await Storage().retrieve(connection, uuid)
