from tedious.asgi.request_interface import RequestInterface
from tedious.asgi.resource_interface import ResourceInterface
from tedious.asgi.response_interface import ResponseInterface, PlainTextResponse

from tedious.asgi.starlette import ResourceController, StarletteApp
from tedious.res import AuthResource

import tedious.config
import asyncio
from starlette.routing import Route

from tedious.auth.auth import Auth
from tedious.sql.postgres import PostgreSQLDatabase

tedious.config.load_config('tests/config.ini')

controller = ResourceController(PostgreSQLDatabase(**tedious.config.CONFIG["DB_CREDENTIALS"]))


async def login(request):
    return await controller.handle(request, AuthResource())


class HelloWorldResource(ResourceInterface):

    async def on_get(self, request: RequestInterface, **kwargs) -> ResponseInterface:

        if request.requester is None:
            # User is not signed in
            return PlainTextResponse('Hello World!')
        else:
            # user is signed in
            return PlainTextResponse('Hello {}!'.format(request.requester.uuid))


async def hello_world(request):
    return await controller.handle(request, HelloWorldResource())


app = StarletteApp(controller, [Route('/login', login, methods=["POST", "PUT", "DELETE"]), Route('/helloworld', hello_world, methods=["GET"])]).app


async def create_user(username, password, role):
    async with PostgreSQLDatabase(**tedious.config.CONFIG['DB_CREDENTIALS']) as db:
        async with await db.acquire() as connection:
            await Auth(connection).register(username, password, role)


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(create_user('nils', '12345678', 'user'))
