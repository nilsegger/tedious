import typing
from typing import Tuple
import ujson
from starlette.applications import Starlette
from starlette.authentication import BaseUser, AuthenticationBackend, \
    AuthenticationError, AuthCredentials
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.routing import Route

from tedious.auth.jwt import InvalidToken
from tedious.mdl.fields import StrField, IntField
from tedious.auth.auth import UserNotFound, InvalidPassword, \
    RefreshTokenNotFound, RefreshTokenExpired, RefreshTokenRevoked, Auth, \
    Requester
from tedious.mdl.model import Model, ValidationError

from tedious.sql.interface import SQLInterface, SQLConnectionInterface

from tedious.asgi.request_interface import RequestInterface, Methods
from starlette.requests import Request as StarletteRequest
from starlette.responses import \
    PlainTextResponse as StarlettePlainTextResponse, \
    Response as StarletteResponse, \
    UJSONResponse as StarletteUJSONResponse

import tedious.config
from tedious.asgi.resource_controller_interface import \
    ResourceControllerInterface
from tedious.asgi.resource_interface import ResourceInterface, HTTPBadRequest, \
    HTTPForbidden, HTTPNotFound
from tedious.asgi.response_interface import PlainTextResponse, BytesResponse, \
    JSONResponse, SuccessfulResponse


class InvalidJSON(Exception):
    """Raised if JSON can not be decoded."""
    pass


class BodyBytesTooLarge(Exception):
    """Raised  if body bytes exceed maximum size of body bytes allowed."""
    pass


class RequestUser(BaseUser):
    """The request user is solely for Starlette to know if user has been authenticated."""

    def __init__(self, requester: Requester):
        self.requester = requester

    @property
    def is_authenticated(self) -> bool:
        """If true, user was successfully authenticated."""
        return self.requester.uuid is not None

    @property
    def display_name(self) -> str:
        """Display name of requester."""
        return self.requester.username

    @property
    def identity(self) -> str:
        """Returns uuid of requester."""
        return self.requester.uuid


class Request(RequestInterface):
    """This class makes Starlette_ requests readable by the tedious framework.
    .. Starlette https://www.starlette.io/requests/
    """

    __slots__ = ('request',)

    def __init__(self, request: StarletteRequest):
        self._request = request

    @property
    def requester(self) -> Requester:
        """

        Returns:
            Instance of :class:`~tedious.auth.auth.Requester` if authenticated else None.
        """
        if isinstance(self._request.user, RequestUser):
            return self._request.user.requester
        return None

    @property
    def url(self) -> str:
        """Returns complete url as str."""
        return self._request.url.path

    @property
    def method(self) -> Methods:
        """Returns HTTP methods as static attribute of :class:`~tedious.asgi.request_interface.Methods`."""
        if self._request.method == "GET":
            return Methods.GET
        elif self._request.method == "POST":
            return Methods.POST
        elif self._request.method == "PUT":
            return Methods.PUT
        elif self._request.method == "DELETE":
            return Methods.DELETE
        else:
            raise ValueError(
                "Unknown method '{}'".format(self._request.method))

    @property
    def client(self) -> Tuple[str, int]:
        """Returns tuple of client ip and port."""
        return self._request.client.host, self._request.client.port

    @property
    def cookies(self) -> dict:
        """Returns dict of cookies."""
        return self._request.cookies

    async def get_body_bytes(self) -> bytes:
        """Reads in body bytes from stream.

        Returns:
            Body bytes.

        Raises:
            :class:`.BodyBytesTooLarge` if body bytes size exceeds maximum.
        """
        _bytes = b''
        async for chunk in self._request.stream():
            _bytes += chunk
            if len(_bytes) > int(
                    tedious.config.CONFIG["ASGI"]["max-body-size"]):
                raise BodyBytesTooLarge()
        return _bytes if len(_bytes) > 0 else None

    async def get_body_json(self) -> dict:
        """Reads in body bytes using :class:`~.Request.get_body_bytes` and decodes them do dict.

        Returns:
            Dict containing body values.

        Raises:
            :class:`~.InvalidJSON` if body can not be decoded from JSON.
        """
        _bytes = await self.get_body_bytes()

        if _bytes is None:
            raise InvalidJSON("Body is empty.")

        try:
            return ujson.loads(_bytes)
        except ValueError:
            raise InvalidJSON("Unable to convert body to JSON.")

    def get_header(self, key, default=None):
        """Retrieves header by key.

        Returns:
            Header value as string or default if header does not contain key.
        """

        return self._request.headers[
            key] if key in self._request.headers else default

    def get_param(self, key, default=None):
        """Retrieves parameter by key.

        Returns:
            Parameter value as string or default if parameter does not contain key.
        """

        return self._request.query_params[
            key] if key in self._request.query_params else default


class _ExceptionResponse(Model):

    def __init__(self, msg=None, code=None):
        super().__init__(None, [
            StrField('msg', value=msg),
            IntField('code', value=code)
        ])


class BearerAuthorization(AuthenticationBackend):
    """Used to authenticate requester using HTTP header Authorization."""

    __slots__ = ('db',)

    def __init__(self, auth: Auth = Auth()):
        self._auth = auth

    async def authenticate(self, request):
        """Extracts Authorization header, checks if Bearer token is given and signs in user.

        Args:
            request: Starlette request.

        Returns:
              Tuple containing :class:`.~AuthCredentials` and :class:`.~RequestUser` instances.

        Raises:
            :class:`.~AuthenticationError`
        """

        if "Authorization" not in request.headers:
            return

        auth = request.headers["Authorization"]

        scheme, token = auth.split()
        if scheme.lower() != 'bearer':
            raise AuthenticationError(
                "Please use Bearer as authorization scheme.")

        try:
            payload = await self._auth.validate_token(token, audience=
            tedious.config.CONFIG["TOKEN"]["audience"])
            requester = Requester(uuid=payload['uid'],
                                  username=payload['name'],
                                  role=payload['role'])
            return AuthCredentials(["authenticated"]), RequestUser(requester)
        except InvalidToken as e:
            raise AuthenticationError(str(e))


def on_auth_error(request: Request, exc: Exception):
    return StarletteUJSONResponse("Please sign in.", status_code=401)


class ResourceController(ResourceControllerInterface):
    """Implementation of :class:`~tedious.asgi.resource_controller_interface.ResourceControllerInterface` for Starlette."""

    __slots__ = ('database',)

    def __init__(self, database: SQLInterface):
        self.database = database

    async def handle_exceptions(self, exception):
        """Handles various exceptions and converts them into :class:`~tedious.asgi.response_interface.ResponseInterface`"""

        response = None

        if isinstance(exception, ValidationError):
            response = _ExceptionResponse(msg=exception.fields, code=422)
        elif isinstance(exception, ValueError):
            response = _ExceptionResponse(msg="Unexpected server error.",
                                          code=500)
        elif isinstance(exception, (UserNotFound, InvalidPassword)):
            response = _ExceptionResponse(msg="Unable to find user.", code=404)
        elif isinstance(exception, (
        RefreshTokenNotFound, RefreshTokenExpired, RefreshTokenRevoked)):
            response = _ExceptionResponse(msg="Invalid refresh token.",
                                          code=400)
        elif isinstance(exception, InvalidJSON):
            response = _ExceptionResponse(msg="JSON could not be parsed.",
                                          code=400)
        elif isinstance(exception, HTTPBadRequest):
            response = _ExceptionResponse(msg="{}".format(exception), code=400)
        elif isinstance(exception, HTTPForbidden):
            response = _ExceptionResponse(msg="{}".format(exception), code=403)
        elif isinstance(exception, HTTPNotFound):
            response = _ExceptionResponse(msg="{}".format(exception), code=404)
        elif isinstance(exception, InvalidToken):
            response = _ExceptionResponse(msg="{}".format(exception), code=401)
        if response is None:
            raise exception
        else:
            return JSONResponse(body=await response.output(['msg', 'code']),
                                status_code=response["code"].value)

    async def handle(self, request: StarletteRequest,
                     resource: ResourceInterface,
                     **kwargs) -> StarletteResponse:
        """Converts the StarletteRequest into a RequestInterface, passes this new object to the resource and converts the returned response into
            a Starlette acceptable response.

        Args:
            request: Starlette request passed by route.
            resource (:class:`~tedious.asgi.resource_interface.ResourceInterface`): Instance of resource which will be tasked with handling request.
            **kwargs: Named parameters to be passed to :class:`~tedious.asgi.resource_interface.ResourceInterface.handle_request`
        """

        connection = await self.database.acquire()

        try:
            response = await self.run_safe(resource.on_request,
                                           Request(request),
                                           connection=connection, logger=None,
                                           **kwargs)
        finally:
            await connection.close()

        if isinstance(response, (BytesResponse, PlainTextResponse)):
            response_class = StarlettePlainTextResponse
        elif isinstance(response, JSONResponse):
            response_class = StarletteUJSONResponse
        elif isinstance(response, SuccessfulResponse):
            return StarlettePlainTextResponse('ok')
        else:
            raise NotImplementedError(
                "{} are not supported.".format(type(response)))

        return response_class(content=response.body, headers=response.headers,
                              media_type=response.media_type,
                              status_code=response.status_code)


class StarletteApp:
    """Complete implementation for the Starlette framework."""

    def __init__(self, controller: ResourceController,
                 routes: typing.List[Route]):
        self.controller = controller

        middleware = [
            Middleware(CORSMiddleware, allow_origins=['*'],
                       allow_methods=["*"], allow_headers=["authorization"]),
            Middleware(GZipMiddleware, minimum_size=1024),
            Middleware(AuthenticationMiddleware, backend=BearerAuthorization(), on_error=on_auth_error)
        ]

        self.app = Starlette(
            debug=True,
            routes=routes,
            middleware=middleware,
            on_startup=[self.on_startup],
            on_shutdown=[self.on_shutdown]
        )

    async def on_startup(self):
        """Waits for database to connect."""
        await self.controller.database.connect()

    async def on_shutdown(self):
        """Waits for database to disconnect."""
        await self.controller.database.close()
