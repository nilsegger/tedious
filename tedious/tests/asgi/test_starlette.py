from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.routing import Route
from starlette.testclient import TestClient
from tedious.sql.postgres import PostgreSQLDatabase

from tedious.asgi.request_interface import RequestInterface
from tedious.asgi.resource_interface import ResourceInterface
from tedious.asgi.response_interface import ResponseInterface, PlainTextResponse, JSONResponse, BytesResponse
from tedious.asgi.starlette import ResourceController, BearerAuthorization

import tedious.config

tedious.config.load_config('tedious/tests/config.ini', required_keys=tedious.config.AUTH_REQUIRED_KEYS)


class MockResource(ResourceInterface):

    async def on_get(self, request: RequestInterface, connection, logger, **kwargs) -> ResponseInterface:
        return PlainTextResponse(body="Hello World!")

    async def on_post(self, request: RequestInterface, connection, logger, **kwargs) -> ResponseInterface:
        return JSONResponse(body={'Hello': 'World!'})

    async def on_put(self, request: RequestInterface, connection, logger, **kwargs) -> ResponseInterface:
        return BytesResponse(body=b'Hello World!')


controller = ResourceController(PostgreSQLDatabase(**tedious.config.CONFIG["DB_CREDENTIALS"]))


async def mock_route(request):
    await controller.database.connect()
    return await controller.handle(request, MockResource())


app = Starlette(debug=True, middleware=[Middleware(AuthenticationMiddleware, backend=BearerAuthorization(controller.database))],
                routes=[Route('/', mock_route, methods=['GET', 'POST', 'PUT'])])


def test_resource_controller():
    client = TestClient(app)
    response = client.get('/')
    assert response.status_code == 200
    assert response.text == "Hello World!"
    response = client.post('/')
    assert response.status_code == 200
    assert response.json()["Hello"] == "World!"
    response = client.put('/')
    assert response.status_code == 200
    assert response.content == b'Hello World!'


if __name__ == '__main__':
    test_resource_controller()
