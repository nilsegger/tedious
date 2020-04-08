import pytest
import tedious.config
from tedious.batch.auth_batch import AuthBatch
from tedious.auth.auth import Auth, UserNotFound
from tedious.util import create_uuid
from tedious.tests.util import TestConnection, MockLogger

tedious.config.load_config('tedious/tests/config.ini')


@pytest.mark.asyncio
async def test_register():
    async with TestConnection() as connection:
        batch = AuthBatch()

        requester_list = []

        for _ in range(10):
            username = create_uuid().hex[:30]
            requester_list.append(await batch.register(connection, username, "12345678", 'user'))

        await batch.commit(connection, MockLogger())

        for requester in requester_list:
            await Auth().authenticate(connection, requester.username, "12345678")


@pytest.mark.asyncio
async def test_update():
    async with TestConnection() as connection:
        auth = Auth()
        requester_list = [await auth.register(connection, create_uuid().hex[:30], "12345678", "user") for _ in range(10)]

        batch = AuthBatch()
        for requester in requester_list:
            await batch.update_role(connection, requester, 'elevated_role')
        await batch.commit(connection, MockLogger())

        for requester in requester_list:
            _global = await auth.authenticate(connection, requester.username, "12345678")
            assert _global.role == 'elevated_role'


@pytest.mark.asyncio
async def test_delete():
    async with TestConnection() as connection:
        auth = Auth()
        requester_list = [await auth.register(connection, create_uuid().hex[:30], "12345678", "user") for _ in range(10)]
        batch = AuthBatch()
        for requester in requester_list:
            await batch.delete(connection, requester)
        await batch.commit(connection, MockLogger())

        for requester in requester_list:
            with pytest.raises(UserNotFound):
                await auth.authenticate(connection, requester.username, "12345678")

