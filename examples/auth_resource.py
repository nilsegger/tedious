"""
    This Example shows how one would implement your own resource and
    connect to your database.
    Run this file by executing: `uvicorn auth_resource:app`
"""

import tedious.config
from tedious.asgi.request_interface import RequestInterface
from tedious.asgi.resource_interface import ResourceInterface
from tedious.asgi.response_interface import PlainTextResponse
from tedious.asgi.starlette import ResourceController, StarletteApp
from tedious.sql.postgres import PostgreSQLDatabase
from starlette.routing import Route
from starlette.requests import Request

# Read config file
tedious.config.load_config('config.ini')

# ResourceController automatically connects to database.
# use controller.database to access database.
controller = ResourceController(PostgreSQLDatabase(**tedious.config.CONFIG["DB_CREDENTIALS"]))


class HelloWorldResource(ResourceInterface):

    async def on_get(self, request: RequestInterface, connection, logger,
                     **kwargs):
        """Returns Hello World if user is not signed in,
            otherwise returns custom greeting message.
            If you want to sign in your user, check this. TODO add link
        """

        if request.requester is None:
            return PlainTextResponse('Hello World!')
        else:
            # Fetch any row from your database.
            row = await connection.fetch_row("SELECT display_name FROM users "
                                                "WHERE uuid=$1",
                                                request.requester.uuid)
            return PlainTextResponse('Hello {}!'.format(row["display_name"]))


# Actual route which listens to http request.
async def hello_world_route(request: Request):
    return await controller.handle(request, HelloWorldResource())


app = StarletteApp(controller, [Route('/hello_world', hello_world_route, methods=["GET"])]).app

