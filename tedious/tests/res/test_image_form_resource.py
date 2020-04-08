import pytest
import tedious.config
from tedious.asgi.response_interface import JSONResponse, SuccessfulResponse
from tedious.res.image_form_resource import ImageFormResource
import hashlib

from tedious.stg.storage import MimeTypes, Storage
from tedious.stg.storage_upload import StorageUploadController
from tedious.tests.res.mocks import MockUserController, MockUser
from tedious.tests.util import read_file, TestConnection, AuthUtil, MockRequest, MockLogger

tedious.config.load_config('tedious/tests/config.ini')

asset = 'tedious/tests/assets/test.jpeg'
chunk_size = 256


@pytest.mark.asyncio
async def test_on_post():
    _bytes = await read_file(asset)
    md5 = hashlib.md5(_bytes).hexdigest()
    headers = {'Content-MD5': md5, 'Content-Type': MimeTypes.IMAGE_JPEG.value, 'Final-Content-Length': len(_bytes)}

    async with TestConnection() as connection:
        requester = await AuthUtil.create_user(connection)
        resource = ImageFormResource(StorageUploadController(), MockUserController(), 'image', [MimeTypes.IMAGE_JPEG], False)

        response = await resource.on_post(MockRequest(requester=requester, body_bytes=_bytes, params={'finalize': 'true'},
                                                      headers=headers), connection, MockLogger(), model=MockUser(uuid=requester.uuid))
        assert isinstance(response, JSONResponse)
        assert 'uuid' in response.body
        assert _bytes == (await Storage().retrieve(connection, response.body['uuid']))[0]

        response = await resource.on_post(MockRequest(requester=requester, body_bytes=_bytes[:chunk_size], params={'finalize': 'false', 'index': '0'},
                                                      headers=headers), connection, MockLogger(), model=MockUser(uuid=requester.uuid))
        assert 'uuid' in response.body
        assert await StorageUploadController().query_reservation(connection, response.body['uuid']) is not None


@pytest.mark.asyncio
async def test_on_put():
    _bytes = await read_file(asset)

    md5 = hashlib.md5(_bytes).hexdigest()
    headers = {'Content-MD5': md5, 'Content-Type': MimeTypes.IMAGE_JPEG.value, 'Final-Content-Length': len(_bytes)}

    async with TestConnection() as connection:
        requester = await AuthUtil.create_user(connection)
        resource = ImageFormResource(StorageUploadController(), MockUserController(), 'image', [MimeTypes.IMAGE_JPEG], False)

        response = await resource.on_post(MockRequest(requester=requester, body_bytes=_bytes[:chunk_size], params={'finalize': 'false', 'index': '0'},
                                                      headers=headers), connection, MockLogger(), model=MockUser(uuid=requester.uuid))

        reservation_uuid = response.body['uuid']
        chunks = int(len(_bytes) / chunk_size)  # dont increase by one because otherwise first one will not be counted

        for i in range(chunks):
            start_at = (i + 1) * chunk_size
            response = await resource.on_put(MockRequest(requester=requester, body_bytes=_bytes[start_at:start_at + chunk_size],
                                                         params={'finalize': 'false' if i < chunks - 1 else 'true', 'index': str(i + 1)},
                                                         headers=headers), connection, MockLogger(), model=MockUser(uuid=requester.uuid), reservation_uuid=reservation_uuid)
        assert 'uuid' in response.body
        file_uuid = response.body['uuid']
        assert _bytes == (await Storage().retrieve(connection, file_uuid))[0]


@pytest.mark.asyncio
async def test_on_delete():
    _bytes = await read_file(asset)

    md5 = hashlib.md5(_bytes).hexdigest()
    headers = {'Content-MD5': md5, 'Content-Type': MimeTypes.IMAGE_JPEG.value, 'Final-Content-Length': len(_bytes)}

    async with TestConnection() as connection:
        requester = await AuthUtil.create_user(connection)
        resource = ImageFormResource(StorageUploadController(), MockUserController(), 'image', [MimeTypes.IMAGE_JPEG], False)

        response = await resource.on_post(MockRequest(requester=requester, body_bytes=_bytes[:chunk_size], params={'finalize': 'false', 'index': '0'},
                                                      headers=headers), connection, MockLogger(), model=MockUser(uuid=requester.uuid))

        reservation_uuid = response.body['uuid']
        response = await resource.on_delete(MockRequest(requester=requester), connection, MockLogger(), model=MockUser(uuid=requester.uuid), reservation_uuid=reservation_uuid)
        assert isinstance(response, SuccessfulResponse)

        assert await StorageUploadController().query_reservation(connection, reservation_uuid) is None
