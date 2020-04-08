from tedious.asgi.request_interface import RequestInterface, Methods
from tedious.asgi.response_interface import ResponseInterface
from tedious.logger import Logger
from tedious.sql.interface import SQLConnectionInterface


class RoutingError(Exception):
    """Raised if on_* are called but not implemented."""
    pass

class HTTPForbidden(Exception):
    """Raised if requester is not signed in."""
    pass


class HTTPBadRequest(Exception):
    """Raised if request is not understandable by resource."""
    pass


class HTTPNotFound(Exception):
    """Raised if requested resource was not found."""
    pass


class ResourceInterface:
    """The resource interface executes the requested actions."""

    async def on_request(self, request: RequestInterface, connection: SQLConnectionInterface, logger: Logger, **kwargs) -> ResponseInterface:
        """Routes request according to HTTP method to either :class:`~.ResourceInterface.on_get`,
            :class:`~.ResourceInterface.on_post`, :class:`~.ResourceInterface.on_put`, :class:`~.ResourceInterface.on_delete`

        Args:
            request (:class:`~tedious.asgi.request_interface.RequestInterface`): The request containing all information about the requester and what he would like to do.
            connection (:class:`~tedious.sql.interface.SQLConnectionInterface`): Short lived connection to database.
            logger (:class:`~tedious.logger.Logger`): Logger used to track activity of requester.
            **kwargs: Additional instances which will be passed along to the members mentioned above.

        Returns:
            Instance of type :class:`~tedious.asgi.response_interface.ResponseInterface`
        """
        if request.method == Methods.GET:
            return await self.on_get(request, connection, logger, **kwargs)
        elif request.method == Methods.POST:
            return await self.on_post(request, connection, logger, **kwargs)
        elif request.method == Methods.PUT:
            return await self.on_put(request, connection, logger, **kwargs)
        elif request.method == Methods.DELETE:
            return await self.on_delete(request, connection, logger, **kwargs)
        else:
            raise ValueError("Method '{}' is not supported.".format(request.method))

    async def on_get(self, request: RequestInterface, connection: SQLConnectionInterface, logger: Logger, **kwargs) -> ResponseInterface:
        """Called on HTTP GET requests.

        Args:
            request (:class:`~tedious.asgi.request_interface.RequestInterface`): The request containing all information about the requester and what he would like to do.
            connection (:class:`~tedious.sql.interface.SQLConnectionInterface`): Short lived connection to database.
            logger (:class:`~tedious.logger.Logger`): Logger used to track activity of requester.
            **kwargs:
        """
        raise RoutingError("on_get is not implemented.")

    async def on_post(self, request: RequestInterface, connection: SQLConnectionInterface, logger: Logger, **kwargs) -> ResponseInterface:
        """Called on HTTP POST requests.

        Args:
            request (:class:`~tedious.asgi.request_interface.RequestInterface`): The request containing all information about the requester and what he would like to do.
            connection (:class:`~tedious.sql.interface.SQLConnectionInterface`): Short lived connection to database.
            logger (:class:`~tedious.logger.Logger`): Logger used to track activity of requester.
            **kwargs:
        """
        raise RoutingError("on_post is not implemented.")

    async def on_put(self, request: RequestInterface, connection: SQLConnectionInterface, logger: Logger, **kwargs) -> ResponseInterface:
        """Called on HTTP PUT requests.

        Args:
            request (:class:`~tedious.asgi.request_interface.RequestInterface`): The request containing all information about the requester and what he would like to do.
            connection (:class:`~tedious.sql.interface.SQLConnectionInterface`): Short lived connection to database.
            logger (:class:`~tedious.logger.Logger`): Logger used to track activity of requester.
            **kwargs:
        """
        raise RoutingError("on_put is not implemented.")

    async def on_delete(self, request: RequestInterface, connection: SQLConnectionInterface, logger: Logger, **kwargs) -> ResponseInterface:
        """Called on HTTP DELETE requests.

        Args:
            request (:class:`~tedious.asgi.request_interface.RequestInterface`): The request containing all information about the requester and what he would like to do.
            connection (:class:`~tedious.sql.interface.SQLConnectionInterface`): Short lived connection to database.
            logger (:class:`~tedious.logger.Logger`): Logger used to track activity of requester.
            **kwargs:
        """
        raise RoutingError("on_delete is not implemented.")

    def raise_not_found(self, msg="404 Not Found"):
        """Raises :class:`~.HTTPNotFound`."""
        raise HTTPNotFound(msg)

    def raise_forbidden(self, msg="403 Forbidden"):
        """Raises :class:`~.HTTPForbidden`."""
        raise HTTPForbidden(msg)

    def raise_bad_request(self, msg="404 Bad Request"):
        """Raises :class:`~.HTTPBadRequest`."""
        raise HTTPBadRequest(msg)
