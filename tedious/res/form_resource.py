from typing import List, Tuple, Dict
from tedious.asgi.request_interface import RequestInterface
from tedious.asgi.resource_interface import ResourceInterface
from tedious.asgi.response_interface import ResponseInterface, JSONResponse, SuccessfulResponse
from tedious.auth.auth import Requester
from tedious.logger import Logger
from tedious.mdl.model import Model
from tedious.mdl.model_controller import ModelController, ManipulationPermissions, VIEW_PERMISSIONS, CREATE_PERMISSIONS, UPDATE_PERMISSIONS, \
    DELETE_PERMISSIONS
from tedious.sql.interface import SQLConnectionInterface


class FormResource(ResourceInterface):
    """Uses a model controller to create, update and delete a model."""

    __slots__ = ('_model_class', '_controller', '_identifier_key')

    def __init__(self, model_class: type(Model), controller: ModelController, identifier_key: str):
        self._model_class = model_class
        self._controller = controller
        self._identifier_key = identifier_key

    async def _check_permission(self, connection: SQLConnectionInterface, model: Model, columns: List[str], requester: Requester,
                                allowed_permissions:List[ManipulationPermissions], skip_existence_check=False) -> Tuple[Model, Dict]:

        if requester is None:
            self.raise_forbidden()

        _global = None

        if not skip_existence_check:
            _global = self._model_class()
            _global[self._identifier_key].value = model[self._identifier_key].value
            _global = await self._controller.get(connection, _global, join_foreign_keys=True)
            if _global is None:
                self.raise_not_found()

        manipulation_permission = await self._controller.get_manipulation_permission(requester, model)
        field_permissions = await self._controller.get_permissions(requester, model)

        if len(field_permissions) == 0 or manipulation_permission not in allowed_permissions:
            self.raise_forbidden("{} permission does not meet CREATE permission.".format(manipulation_permission))

        return _global, field_permissions

    async def _read_body_to_model(self, request: RequestInterface, model: Model, field_permissions):
        """Creates model if it is None and reads body bytes from request as json and reads them in for model."""
        if model is None:
            model = self._model_class()
        await model.input(await request.get_body_json(), permissions=field_permissions)
        await model.validate_content()
        return model

    async def on_get(self, request: RequestInterface, connection: SQLConnectionInterface, logger: Logger, model: Model = None) -> ResponseInterface:
        """
            Checks permission of requesting user and returns requested model from database.

        Args:
            request: Route request.
            connection: Connection to database.
            logger: Activity logger.
            model: Model to retrieve

        Returns:
              JSONResponse containing model.

        Raises:
            HTTPNotFound if model does not exist.
            HTTPForbidden if requester is None or is not allowed to view model.
        """

        _global, field_permissions = await self._check_permission(connection, model, None, request.requester, VIEW_PERMISSIONS)

        return JSONResponse(body=await _global.output(fields=_global.keys(), permissions=field_permissions))

    async def on_post(self, request: RequestInterface, connection: SQLConnectionInterface, logger: Logger, model: Model = None) -> ResponseInterface:
        """Create model.

        Args:
            request: Route request.
            connection: Connection to database.
            logger: Activity logger.
            model: Most likely None if uuid can not be set in advance, otherwise this model with given uuid should be created.

        Returns:
            JSONResponse containing all identifiers of model.

        """

        _, field_permissions = await self._check_permission(connection, model, self._controller.identifiers, request.requester,
                                                            allowed_permissions=CREATE_PERMISSIONS, skip_existence_check=True)

        model = await self._read_body_to_model(request, model, field_permissions)
        await self._controller.create(connection, model)
        return JSONResponse(await model.output(self._controller.identifiers))

    async def on_put(self, request: RequestInterface, connection: SQLConnectionInterface, logger: Logger, model: Model = None) -> ResponseInterface:
        """Update model.

        Args:
            request: Route request.
            connection: Connection to database.
            logger: Activity logger.
            model: Model to update.
        """
        _global, field_permissions = await self._check_permission(connection, model, self._controller.identifiers, request.requester,
                                                                  allowed_permissions=UPDATE_PERMISSIONS, skip_existence_check=True)

        model = await self._read_body_to_model(request, model, field_permissions)
        await self._controller.update(connection, model, _global)

        return SuccessfulResponse()

    async def on_delete(self, request: RequestInterface, connection: SQLConnectionInterface, logger: Logger, model: Model = None) -> ResponseInterface:
        """Delete model.

        Args:
            request: Route request.
            connection: Connection to database.
            logger: Activity logger.
            model: Model to delete.
        """
        _global, field_permissions = await self._check_permission(connection, model, self._controller.identifiers, request.requester,
                                                                  allowed_permissions=DELETE_PERMISSIONS, skip_existence_check=True)
        await self._controller.delete(connection, model, _global)
        return SuccessfulResponse()
