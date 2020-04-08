from datetime import datetime, timedelta

from tedious.auth.auth import Auth, UserNotFound, InvalidPassword, RefreshTokenNotFound, RefreshTokenExpired, RefreshTokenRevoked

import tedious.config
import pytest
import asyncio

from tedious.tests.util import TestConnection, AuthUtil
from tedious.util import create_uuid

tedious.config.load_config('tedious/tests/config.ini')


@pytest.mark.asyncio
async def test_register_authentication():

    user = create_uuid().hex[:30]
    password = '123456'
    role = 'user'

    async with TestConnection() as connection:
        auth = Auth()
        requester = await auth.register(connection, user, password, role)
        assert requester.uuid is not None
        authenticated_requester = await auth.authenticate(connection, user, password)
        assert authenticated_requester.uuid == requester.uuid, "Authenticated '{}' != Registered '{}'".format(authenticated_requester.uuid,
                                                                                                              requester.uuid)
        assert authenticated_requester.role == requester.role
        with pytest.raises(UserNotFound):
            await auth.authenticate(connection, "notuser", password)
        with pytest.raises(InvalidPassword):
            await auth.authenticate(connection, user, "notpassword")


@pytest.mark.asyncio
async def test_save_refresh_token():


    async with TestConnection() as connection:
        requester = await AuthUtil.create_user(connection)
        auth = Auth()
        refresh_token = await auth.create_refresh_token(connection, requester)
        predicted_length = int(4 * (int(tedious.config.CONFIG["TOKEN"]["refresh-token-bytes"]) / 3)) + 1
        assert predicted_length == len(refresh_token), "Predicted: {} != Real: {}".format(predicted_length, len(refresh_token))
        assert refresh_token is not None and len(refresh_token) > 0
        refreshed_requester = await auth.validate_refresh_token(connection, refresh_token)
        assert requester.uuid == refreshed_requester.uuid, "Refreshed '{}' != Registered '{}'".format(refreshed_requester.uuid, requester.uuid)
        assert requester.role == refreshed_requester.role, "Refreshed '{}' != Registered '{}'".format(refreshed_requester.role, requester.role)


@pytest.mark.asyncio
async def test_validate_refresh_token():

    async with TestConnection() as connection:
        requester = await AuthUtil.create_user(connection)
        auth = Auth()
        refresh_token = "fake-refresh-token"
        await auth.save_refresh_token(connection, requester, refresh_token, datetime.now() - timedelta(seconds=60))
        with pytest.raises(RefreshTokenNotFound):
            await auth.validate_refresh_token(connection, "invalid refresh token")
        with pytest.raises(RefreshTokenExpired):
            await auth.validate_refresh_token(connection, refresh_token)


@pytest.mark.asyncio
async def test_revoke_refresh_token():


    async with TestConnection() as connection:
        requester = await AuthUtil.create_user(connection)
        auth = Auth()
        refresh_token = await auth.create_refresh_token(connection, requester)
        await auth.revoke_refresh_token(connection, requester)
        with pytest.raises(RefreshTokenRevoked):
            await auth.validate_refresh_token(connection, refresh_token)


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(test_save_refresh_token())
