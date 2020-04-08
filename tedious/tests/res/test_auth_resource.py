from datetime import datetime, timedelta

from tedious.asgi.resource_interface import HTTPBadRequest, HTTPForbidden


from tedious.asgi.response_interface import JSONResponse

from tedious.auth.auth import Auth, InvalidPassword, UserNotFound, RefreshTokenExpired, RefreshTokenRevoked, RefreshTokenNotFound

import tedious.config
import pytest

from tedious.res.auth_resource import AuthResource, AuthUser
from tedious.tests.util import AuthUtil, TestConnection, MockRequest, MockLogger

tedious.config.load_config('tedious/tests/config.ini')


@pytest.mark.asyncio
async def test_on_post():

    async with TestConnection() as connection:
        requester = await AuthUtil.create_user(connection)
        resource = AuthResource(Auth())

        response = await resource.on_post(
            MockRequest(body_json=await AuthUser(username=requester.username, password="12345678").output(['username', 'password'])), connection, MockLogger())

        assert isinstance(response, JSONResponse)
        assert 'token' in response.body
        assert 'refresh_token' in response.body
        assert 'uid' in response.body and response.body['uid'] == requester.uuid.hex

        with pytest.raises(UserNotFound):
            await resource.on_post(
                MockRequest(body_json=await AuthUser(username="wrong username", password="12345678").output(['username', 'password'])), connection, MockLogger())

        with pytest.raises(InvalidPassword):
            await resource.on_post(
                MockRequest(body_json=await AuthUser(username=requester.username, password="not my password").output(
                    ['username', 'password'])), connection, MockLogger())


@pytest.mark.asyncio
async def test_on_put():

    async with TestConnection() as connection:
        requester = await AuthUtil.create_user(connection)

        refresh_token = await Auth().create_refresh_token(connection, requester)

        resource = AuthResource()

        response = await resource.on_put(MockRequest(body_bytes=refresh_token.encode('utf-8')), connection, MockLogger())

        assert isinstance(response, JSONResponse)
        assert 'token' in response.body
        assert 'uid' in response.body and response.body['uid'] == requester.uuid.hex

        with pytest.raises(RefreshTokenNotFound):
            await resource.on_put(MockRequest(body_bytes=b'Definitely not a refresh token'), connection, MockLogger())

        await Auth().revoke_refresh_token(connection, requester)
        with pytest.raises(RefreshTokenRevoked):
            await resource.on_put(MockRequest(body_bytes=refresh_token.encode('utf-8')), connection, MockLogger())

        await Auth().save_refresh_token(connection, requester, "refresh_token", datetime.now() - timedelta(seconds=60))

        with pytest.raises(RefreshTokenExpired):
            await resource.on_put(MockRequest(body_bytes="refresh_token".encode('utf-8')), connection, MockLogger())

        with pytest.raises(HTTPBadRequest):
            await resource.on_put(MockRequest(), connection, MockLogger())


@pytest.mark.asyncio
async def test_on_delete():


    async with TestConnection() as connection:
        requester = await AuthUtil.create_user(connection)
        resource = AuthResource()

        refresh_token = await Auth().create_refresh_token(connection, requester)

        await resource.on_delete(MockRequest(requester=requester), connection, MockLogger())

        with pytest.raises(RefreshTokenRevoked):
            await Auth().validate_refresh_token(connection, refresh_token)

        with pytest.raises(HTTPForbidden):
            await resource.on_delete(MockRequest(), connection, MockLogger())
