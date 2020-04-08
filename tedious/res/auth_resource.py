import tedious.config
from tedious.logger import Logger
from tedious.mdl.fields import StrField
from tedious.auth.auth import Auth
from tedious.mdl.model import Model
from tedious.sql.interface import SQLConnectionInterface
from tedious.asgi.request_interface import RequestInterface
from tedious.asgi.resource_interface import ResourceInterface
from tedious.asgi.response_interface import ResponseInterface, JSONResponse, SuccessfulResponse


class AuthUser(Model):
    """
        Model for user requests.
    """

    def __init__(self, name: str = None, username=None, password=None):
        super().__init__(name, [
            StrField('username', min_len=1, max_len=30, value=username),
            StrField('password', min_len=8, max_len=1024, value=password)
        ])


class AuthResource(ResourceInterface):
    """
        on_post: Sign in.
        on_put: Retrieve access token with refresh token in body.
        on_delete: Revoke all refresh tokens of users.
    """

    __slots__ = ('_auth',)

    def __init__(self, auth: Auth = Auth()):
        self._auth = auth

    async def on_post(self, request: RequestInterface, connection: SQLConnectionInterface, logger: Logger, *kwargs) -> ResponseInterface:
        """
            Loads an AuthUser from body json, checks validity and signs user in.
            If the user does not have any valid refresh tokens, a new one is created.

        Args:
            request: Route request.
            connection: Connection to database.

        Returns:
            JSONResponse containing token, refresh_token and uuid.

        Raises:
            RequesterAlreadySignedIn
        """

        if request.requester is not None:
            self.raise_bad_request("Already signed in.")

        user = await AuthUser().input(await request.get_body_json(), validate_fields=['username', 'password'])
        requester = await self._auth.authenticate(connection, user["username"].value, user["password"].value)
        token = await self._auth.create_token(audience=tedious.config.CONFIG["TOKEN"]["audience"],
                                              claims={'uid': requester.uuid.hex, 'name': requester.username, 'role': requester.role})
        refresh_token = await self._auth.retrieve_refresh_token(connection, requester)
        if refresh_token is None:
            refresh_token = await self._auth.create_refresh_token(connection, requester)
        return JSONResponse(body={'token': token, 'refresh_token': refresh_token, 'uid': requester.uuid.hex})

    async def on_put(self, request: RequestInterface, connection: SQLConnectionInterface, logger: Logger, *kwargs) -> ResponseInterface:
        """
            Extract refresh token from body and provides new access token.

        Args:
            request: Route request.
            connection: Connection to database.

        Returns:
            JSONResponse containing new access token.

        Raises:
            MissingRefreshToken
        """

        refresh_token = await request.get_body_bytes()

        if refresh_token is None:
            self.raise_bad_request("Refresh Token must be sent along in body of request")

        requester = await self._auth.validate_refresh_token(connection, refresh_token.decode('utf-8'))
        token = await self._auth.create_token(audience=tedious.config.CONFIG["TOKEN"]["audience"], claims={'uid': requester.uuid.hex, 'name': requester.username, 'role': requester.role})

        return JSONResponse(body={'token': token})

        # TODO implement scenario
        """
            if request.requester is not None and refreshed_requester.uuid != request.requester.uuid:
                # If requester isn't admin this would be a very weird scenario
        """

    async def on_delete(self, request: RequestInterface, connection: SQLConnectionInterface, logger: Logger, *kwargs) -> ResponseInterface:
        """
            Revokes active refresh tokens.

        Args:
            request: Route request
            connection: Connection to database.

        Returns:
            SuccessfulResponse
        """
        if request.requester is None:
            self.raise_forbidden("Please sign in to delete your refresh tokens.")

        await self._auth.revoke_refresh_token(connection, request.requester)

        return SuccessfulResponse()
