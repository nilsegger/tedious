class ResponseInterface:
    """The response interface simply tells the :class:`~tedious.asgi.resource_controller_interface.ResourceControllerInterface`
        what it would like to return and with what HTTP response headers.
    """

    __slots__ = ('body', 'headers', 'status_code', 'media_type')

    def __init__(self, body=None, headers=None, status_code=200, media_type=None):
        self.body = body
        self.headers = headers
        self.status_code = status_code
        self.media_type = media_type


class BytesResponse(ResponseInterface):
    """Returns body as bytes."""
    pass


class PlainTextResponse(ResponseInterface):
    """Returns body as text. Doesnt really have a difference compared to BytesResponse."""
    pass


class JSONResponse(ResponseInterface):
    """Returns body encoded in json."""
    pass


class SuccessfulResponse(ResponseInterface):
    """Returns simple OK."""
    pass
