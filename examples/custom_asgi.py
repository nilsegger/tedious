"""
    This example shows how you would implement your own ASGI framework.
    First you must override the RequestInterface followed by the
    ResourceControllerInterface.
"""

from tedious.asgi.request_interface import RequestInterface
from tedious.asgi.resource_controller_interface import \
    ResourceControllerInterface
from tedious.asgi.resource_interface import ResourceInterface
from tedious.asgi.response_interface import ResponseInterface, \
    PlainTextResponse, JSONResponse


class CustomRequest(RequestInterface):

    def __init__(self, requested_url):
        self._url = requested_url

    @property
    def url(self) -> str:
        return self._url

    # TODO override all properties and methods.


class CustomResourceController(ResourceControllerInterface):

    async def handle_exceptions(self, exception) -> ResponseInterface:
        pass

    async def handle(self, received_request, resource: ResourceInterface) -> \
            ResponseInterface:

        # Convert the request received by your framework into a CustomRequest
        request = CustomRequest(received_request.url)
        logger = None # TODO create a proper logger
        connection = None # TODO create a proper connection
        response = await resource.on_request(request, connection, logger)

        if isinstance(response, PlainTextResponse):
            # TODO return as text
            pass
        elif isinstance(response, JSONResponse):
            # TODO return as json
            pass

