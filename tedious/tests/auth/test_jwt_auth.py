from datetime import datetime, timedelta
import tedious.config
import pytest
from tedious.auth.jwt import JWTAuth, InvalidToken

tedious.config.load_config('tedious/tests/config.ini', required_keys=tedious.config.AUTH_REQUIRED_KEYS)


def test_encrypt_decrypt_public_key_identifier():
    auth = JWTAuth()
    filename = 'rsa.test_file000'
    encrypted = auth._create_public_key_identifier(filename)
    decoded = auth._decode_public_key_identifier(encrypted)
    assert filename == decoded, "{} != {}".format(filename, decoded)

    with pytest.raises(ValueError):
        auth._create_public_key_identifier('not a multiple of 16 characters')


@pytest.mark.asyncio
async def test_create_token():
    auth = JWTAuth()
    token = await auth.create_token()
    assert token is not None and len(token) > 0


@pytest.mark.asyncio
async def test_validate_token():
    auth = JWTAuth()
    uid = "test_uid"
    audience = "api.tedious.ch"
    token = await auth.create_token(audience=audience, claims={'uid': uid})
    assert token is not None and len(token) > 0
    payload = await auth.validate_token(token, audience=audience)
    assert payload is not None
    assert 'uid' in payload and payload['uid'] == uid

    with pytest.raises(InvalidToken):
        auth = JWTAuth()
        token = "very incorrect token.".encode('utf-8')
        await auth.validate_token(token, audience=audience)

    with pytest.raises(InvalidToken):
        auth = JWTAuth()
        token = await auth.create_token(audience="incorrect.tedious.ch", claims={'uid': uid})
        await auth.validate_token(token, audience=audience)

    with pytest.raises(InvalidToken):
        auth = JWTAuth()
        token = await auth.create_token(audience=audience, claims={'exp': datetime.utcnow() - timedelta(seconds=60)})
        await auth.validate_token(token, audience=audience)