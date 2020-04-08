from uuid import UUID
from tedious.asgi.request_interface import RequestInterface
from tedious.asgi.resource_interface import ResourceInterface
from tedious.asgi.response_interface import ResponseInterface, BytesResponse, SuccessfulResponse
from tedious.auth.auth import Requester
from tedious.logger import Logger
from tedious.mdl.model import Model, Permissions
from tedious.mdl.model_controller import ModelController, VIEW_PERMISSIONS, DELETE_PERMISSIONS
from tedious.sql.interface import SQLConnectionInterface
from tedious.stg.storage import Storage


class ImageResourceInterface(ResourceInterface):
    """Base class for image resources."""

    def __init__(self, controller: ModelController, permission_field):
        """manipulation_field is key path to permission from ModelController.get_manipulation_permissions()[1]"""
        self.model_controller = controller
        self.permission_field = permission_field

    async def check_permissions(self, requester: Requester, model: Model, allowed_permissions):
        """Checks if the requester has the required permissions."""
        permission = await self.model_controller.get_permission(requester, model, self.permission_field)
        if permission not in allowed_permissions:
            self.raise_forbidden("Permission not granted.")

    async def check_manipulation_permissions(self, requester: Requester, model: Model, allowed_permissions):
        """Checks if the requester has the required manipulation permissions."""
        permission = await self.model_controller.get_manipulation_permission(requester, model, self.permission_field)
        if permission not in allowed_permissions:
            self.raise_forbidden("Permission not granted.")

class ImageResource(ImageResourceInterface):
    """Image resource which is capable to retrieve and delete images."""

    def __init__(self, storage: Storage, model_controller: ModelController, file_field_key_path):
        self.controller = storage
        super().__init__(model_controller, file_field_key_path)

    async def check_request_validity(self, connection: SQLConnectionInterface, requester: Requester, file_uuid: UUID, model: Model, allowed_field_permissions):
        """Checks if requester if allowed to view given image."""
        if file_uuid is None:
            self.raise_bad_request("UUID is missing.")

        row = await self.controller.query_by_uuid(connection, file_uuid)

        if row is None:
            self.raise_not_found()

        if row["public"]:
            return row["path"], row["mime"]
        elif requester is None:
            self.raise_forbidden("File is not public.")

        await self.check_permissions(requester, model, allowed_field_permissions)

        return row["path"], row["mime"]

    async def on_get(self, request: RequestInterface, connection: SQLConnectionInterface, logger: Logger, model: Model = None, file_uuid: UUID = None) -> ResponseInterface:
        """Retrieve image based on uuid.

        Args:
            request: Route request.
            connection: Connection to database.
            logger: Activity logger.
            model: Model for which this image is meant for.
            file_uuid: File to retrieve

        Returns:
            BytesResponse
        """
        path, mime = await self.check_request_validity(connection, request.requester, file_uuid, model, [Permissions.READ, Permissions.READ_WRITE])
        _bytes = await self.controller.read_file(path, False)
        return BytesResponse(body=_bytes, media_type=mime)

    async def on_delete(self, request: RequestInterface, connection: SQLConnectionInterface, logger: Logger, model: Model = None, file_uuid: UUID = None) -> ResponseInterface:
        """Deletes Image

        Args:
            request: Route request.
            connection: Connection to database.
            logger: Activity logger.
            model: Model for which this image is meant for.
            file_uuid: Which file to delete
        """
        await self.check_request_validity(connection, request.requester, file_uuid, model, [Permissions.WRITE, Permissions.READ_WRITE])
        await self.controller.remove(connection, file_uuid)
        return SuccessfulResponse()
