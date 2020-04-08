import pytest
import tedious.config
from tedious.asgi.response_interface import BytesResponse, SuccessfulResponse
from tedious.auth.auth import Auth, Requester
from tedious.res.image_resource import ImageResource
from tedious.stg.storage import Storage, MimeTypes
from tedious.tests.res.mocks import MockUserController, MockUser
from tedious.tests.util import TestConnection, read_file, MockRequest, MockLogger
from tedious.util import create_uuid

tedious.config.load_config('tedious/tests/config.ini')

asset = "tedious/tests/assets/test.jpeg"

@pytest.mark.asyncio
async def test_get():

    async with TestConnection() as connection:
        requester = await Auth().register(connection, create_uuid().hex[30], "12345678", "user")
        _bytes = await read_file(asset)
        file_uuid = await Storage().save(connection, requester.uuid, _bytes, MimeTypes.IMAGE_JPEG, False)

        resource = ImageResource(Storage(), MockUserController(), "image")

        response = await resource.on_get(MockRequest(requester=Requester(uuid=requester.uuid)), connection, MockLogger(), MockUser(uuid=requester.uuid), file_uuid)
        assert isinstance(response, BytesResponse)
        assert response.body == _bytes
        assert response.media_type == MimeTypes.IMAGE_JPEG.value


@pytest.mark.asyncio
async def test_delete():

    async with TestConnection() as connection:
        requester = await Auth().register(connection, create_uuid().hex[30], "12345678", "user")
        storage = Storage()
        file_uuid = await storage.save(connection, requester.uuid, await read_file(asset), MimeTypes.IMAGE_JPEG, False)

        resource = ImageResource(storage, MockUserController(), "image")
        response = await resource.on_delete(MockRequest(requester=requester), connection, MockLogger(), model=MockUser(uuid=requester.uuid), file_uuid=file_uuid)
        assert isinstance(response, SuccessfulResponse)

        with pytest.raises(FileNotFoundError):
            await storage.retrieve(connection, file_uuid)

