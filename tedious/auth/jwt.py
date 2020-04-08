import base64
from typing import Dict, Tuple, List
import jwt
from jwt import InvalidTokenError, DecodeError
from datetime import datetime, timedelta

import tedious.config
import os
import random
import aiofiles
from Crypto.Cipher import AES


class InvalidToken(Exception):
    """Raised if token is token is invalid."""
    pass


class JWTAuth:
    """Implementation for JSON Web Tokens."""

    __slots__ = ('_cached_private_keys',)

    _IDENTIFIER_CYPHER = None

    def __init__(self):
        self._cached_private_keys = None

    @property
    def _private_keys(self) -> List[Tuple[str, str]]:
        """Caches list of private key files to decrease use of os.listdir. Filename of private key will also be identifier for public key.

        Returns:
            List of tuples containing filename and relative path to file.

        Raises:
            ValueError if directory is empty.
        """

        directory = tedious.config.CONFIG["KEYS"]['private-keys']
        if self._cached_private_keys is None:
            self._cached_private_keys = [(file, os.path.join(directory, file)) for file in os.listdir(directory) if
                                         os.path.isfile(os.path.join(directory, file))]
        if len(self._cached_private_keys) == 0:
            raise ValueError("'{}' does not contains any private keys.".format(directory))
        return self._cached_private_keys

    @staticmethod
    def _get_identifier_cypher():
        """Caches cypher to improve performance.

        Returns:
            Cypher which is used to encrypt and decrypt identifier.
        """

        if JWTAuth._IDENTIFIER_CYPHER is None:
            JWTAuth._IDENTIFIER_CYPHER = AES.new(tedious.config.CONFIG["KEYS"]["identifier-secret"].encode('utf-8'), AES.MODE_ECB)
        return JWTAuth._IDENTIFIER_CYPHER

    @staticmethod
    def _create_public_key_identifier(filename):
        """Encodes filename into public key identifier.

        Args:
            filename (str): Filename to be encoded.

        Returns:
            Encoded filename using a secret according to this answer_.

        .. _answer https://stackoverflow.com/a/2490376

        Raises:
            ValueError if length of filename is not a multiple of 16. (Required by AES)
        """

        if len(filename) % 16 != 0:
            raise ValueError("Length of '{}' is not a multiple of 16.".format(filename))
        return base64.b64encode(JWTAuth._get_identifier_cypher().encrypt(filename.encode('utf-8'))).decode('utf-8')

    @staticmethod
    def _decode_public_key_identifier(identifier):
        """Decodes encoded identifier using the cypher.

        Args:
            identifier: Encoded identifier to be decoded.

        Returns:
            Decrypted identifier -> filename.
        """

        return JWTAuth._get_identifier_cypher().decrypt(base64.b64decode(identifier)).decode('utf-8')

    async def retrieve_private_key(self) -> Tuple[str, str]:
        """Selects random private key from directory, reads it and returns it as string. The filename will be converted into a public key identifier.

        Returns:
            Private key as string and public key identifier.
        """

        filename, file_path = random.choice(self._private_keys)
        async with aiofiles.open(file_path, mode='r') as file:
            private_key = await file.read()
        return private_key, self._create_public_key_identifier(filename)

    async def retrieve_public_key(self, kid: str) -> str:
        """Retrieves public key from directory.

        Returns:
            Public key as string.
        """

        directory = tedious.config.CONFIG['KEYS']['public-keys']
        async with aiofiles.open(os.path.join(directory, kid), mode='r') as file:
            public_key = await file.read()
        return public_key

    async def create_token(self, audience=None, claims=None) -> bytes:
        """Creates access token.

        Args:
            audience (str): Identifier for whom this token is meant to be used by.
            claims (dict): Custom claims which will be added to token payload.

        Returns:
            Freshly created token as bytes.
        """

        private_key, public_key_identifier = await self.retrieve_private_key()
        now = datetime.utcnow()
        payload = {
            'exp': now + timedelta(seconds=int(tedious.config.CONFIG["TOKEN"]["expire"])),
            'iss': tedious.config.CONFIG["TOKEN"]["issuer"],
            'iat': now
        }
        if audience is not None:
            payload['aud'] = audience
        if claims is not None:
            payload.update(claims)
        return jwt.encode(payload, private_key, algorithm='RS256', headers={'kid': public_key_identifier})

    async def validate_token(self, token: bytes, audience=None) -> Dict[str, str]:
        """Firstly validates header of token and retrieves public key identifier, then verifies signature and decodes payload.

        Args:
            token (bytes): Encoded token.
            audience: Self identifier. If tokens audience does not match an exception will get thrown.

        Returns:
            Payload of token as dict.
        """

        try:
            header = jwt.get_unverified_header(token)
            if "kid" not in header:
                raise InvalidToken("Missing kid in header")
            return jwt.decode(token, await self.retrieve_public_key(self._decode_public_key_identifier(header["kid"])), algorithms='RS256', issuer=tedious.config.CONFIG["TOKEN"]["issuer"], audience=audience)
        except DecodeError:
            raise InvalidToken("Unable to decode token.")
        except Exception as e:
            raise InvalidToken(str(type(e)) + " " + str(e))
