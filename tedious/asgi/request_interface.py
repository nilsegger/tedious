import enum
from typing import Tuple
from tedious.auth.auth import Requester


class Methods(enum.Enum):
    """Enum of HTTP Methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    OPTIONS = "OPTIONS"


class RequestInterface:
    """The request interface is an abstract class which will be used by :class:`~tedious.asgi.resource_interface.ResourceInterface`
        instances to extract all necessary information about who the requester is and what he wants to do.
    """

    @property
    def client(self) -> Tuple[str, int]:
        """The client identifies the users ip address and port.

            Returns:
                ``Tuple(client ip, client port)``
        """
        raise NotImplementedError

    @property
    def requester(self) -> Requester:
        """The requester identifies the signed in user.

        Returns:
            If the user is signed in an instance of :class:`~tedious.auth.auth.Requester`, else ``None``
        """
        raise NotImplementedError

    @property
    def cookies(self) -> dict:
        """Returns dict of requesters cookies."""
        raise NotImplementedError

    @property
    def method(self) -> Methods:
        """Identifies the HTTP methods used by the requester.

        Returns:
            A static attribute of :class:`~tedious.asgi.request_interface.Methods`
        """
        raise NotImplementedError

    @property
    def url(self) -> str:
        """The complete url accessed by the user.

        Returns:
            URL as str.
        """
        raise NotImplementedError

    async def get_body_bytes(self) -> bytes:
        """Reads the requests body as bytes.
        Returns:
            Body as bytes
        """
        raise NotImplementedError

    async def get_body_json(self) -> dict:
        """Ready the requests body and decodes it as json.

        Returns:
            Body decoded as dict.
        """
        raise NotImplementedError

    def get_header(self, key, default=None):
        """Retrieve single header value.

        Returns:
            Header value as str.
        """
        raise NotImplementedError

    def get_param(self, key, default=None):
        """Retrieve single parameter value.
        Returns:
            Parameter value as str.
        """
        raise NotImplementedError
