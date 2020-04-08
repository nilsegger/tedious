from typing import Dict, List
from tedious.asgi.request_interface import RequestInterface
from tedious.asgi.resource_interface import ResourceInterface
from tedious.asgi.response_interface import ResponseInterface, JSONResponse
from tedious.logger import Logger
from tedious.mdl.list_controller import ListController
from tedious.sql.interface import SQLConnectionInterface


class ListResource(ResourceInterface):
    """This resource fetches multiple models from the database and lists them."""

    __slots__ = (
    '_allowed_roles', '_limit', '_join_foreign_keys', '_output_fields')

    def __init__(self, allowed_roles: List, output_fields, limit=25,
                 join_foreign_keys=False):
        self._allowed_roles = allowed_roles
        self._output_fields = output_fields
        self._limit = limit
        self._join_foreign_keys = join_foreign_keys

    async def get_controller(self, request, **kwargs) -> ListController:
        """Returns list controller."""
        raise NotImplementedError

    async def get_output_fields(self, requester, **kwargs) -> Dict:
        """Returns fields to output. Return None if requester is not allowed to view anything.."""
        return self._output_fields

    async def on_get(self, request: RequestInterface,
                     connection: SQLConnectionInterface, logger: Logger,
                     **kwargs) -> ResponseInterface:
        """Fetches multiple models and lists them in response.

        Args:
            request: Route request.
            connection: Connection to database.
            logger: Activity logger.

        Returns:
            JSONResponse containing the used offset, if there are no more models and the list itself.
        """

        role = request.requester.role if request.requester is not None else None

        if role not in self._allowed_roles:
            self.raise_forbidden(
                "A requester of role {} is not allowed to view this resource.".format(
                    role))

        offset = int(request.get_param('offset', 0))

        fields = await self.get_output_fields(request.requester, **kwargs)

        if fields is None:
            self.raise_forbidden(
                "Sorry, you are not allowed to view this list.")

        models = await (await self.get_controller(request, **kwargs)).get(
            connection, self._limit, offset, self._join_foreign_keys)

        return JSONResponse(body={'offset': offset + len(models),
                                  'is_end': len(models) < self._limit,
                                  'list': [await model.output(fields=fields)
                                           for model in models]})


class StaticListResource(ListResource):

    def __init__(self, controller: ListController, allowed_roles: List,
                 output_fields, limit=25,
                 join_foreign_keys=False):
        super().__init__(allowed_roles, output_fields, limit,
                         join_foreign_keys)
        self.controller = controller

    async def get_controller(self, request, **kwargs) -> ListController:
        return self.controller
