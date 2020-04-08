from typing import List
from uuid import UUID

from tedious.asgi.request_interface import RequestInterface
from tedious.asgi.response_interface import ResponseInterface, JSONResponse, SuccessfulResponse
import binascii

from tedious.auth.auth import Requester
from tedious.logger import Logger
from tedious.mdl.model import Model
from tedious.mdl.model_controller import ModelController, ManipulationPermissions
from tedious.res.image_resource import ImageResourceInterface
from tedious.sql.interface import SQLConnectionInterface
from tedious.stg.storage import MimeTypes
from tedious.stg.storage_upload import StorageUploadController


class ImageFormResource(ImageResourceInterface):
    """Used to upload image as one or as chunks."""

    def __init__(self, reservation_controller: StorageUploadController, model_controller: ModelController, manipulation_field: str,
                 allowed_mimes: List[MimeTypes], is_public: bool):
        super().__init__(model_controller, manipulation_field)
        self.controller = reservation_controller
        self.allowed_mimes = allowed_mimes
        self.is_public = is_public

    async def check_request_validity(self, connection: SQLConnectionInterface, requester: Requester, model: Model, reservation_uuid: UUID = None):
        """Checks if requester is allowed to create image."""

        if requester is None:
            self.raise_forbidden("Please sign in.")

        await self.check_manipulation_permissions(requester, model, [ManipulationPermissions.CREATE_UPDATE_DELETE])

        if reservation_uuid is not None:
            reservation = await self.controller.query_reservation(connection, reservation_uuid)
            if reservation is None:
                self.raise_not_found("Can not find reservation.")

    async def link_uploaded_image(self, request: RequestInterface, connection: SQLConnectionInterface, logger: Logger, model: Model, file_uuid: UUID):
        """This method is called on finalize and is meant to reference image to model, like setting models avatar uuid to the new file_uuid."""
        pass

    async def on_post(self, request: RequestInterface, connection: SQLConnectionInterface, logger: Logger, model: Model = None) -> ResponseInterface:
        """Creates reservation for image.

        Dont forget the Content-MD5, Content-Type and Final-Content-Length headers.
        If the image is final set the finalize parameter to true, otherwise to false.

        Args:
            request: Route request.
            connection: Connection to database.
            logger: Activity logger.
            model: Model for which this image is meant for.

        Returns:
            JSONResponse either containing the file uuid or the reservation uuid.
        """
        await self.check_request_validity(connection, request.requester, model)

        md5 = request.get_header('Content-MD5')
        mime = request.get_header('Content-Type')
        size = int(request.get_header('Final-Content-Length'))

        if md5 is None or mime is None or size is None:
            self.raise_bad_request("Please include Content-MD5, Content-Type and Content-Length.")

        md5 = binascii.unhexlify(md5)
        index = int(request.get_param('index', 0))
        finalize = request.get_param('finalize', 'false') == 'true'
        _bytes = await request.get_body_bytes()

        if _bytes is None or len(_bytes) == 0:
            self.raise_bad_request("Please include body bytes.")

        if MimeTypes(mime) not in self.allowed_mimes:
            self.raise_bad_request("Allowed mime types are {}.".format(', '.join([mime.value for mime in self.allowed_mimes])))

        if finalize:
            # Image is not split up into chunks.
            await self.controller.verify_hash(_bytes, md5)
            await self.controller.verify_image(_bytes)
            file_uuid = await self.controller.storage.save(connection, request.requester.uuid, _bytes, MimeTypes(mime), self.is_public)
            await self.link_uploaded_image(request, connection, logger, model, file_uuid)
            return JSONResponse({'uuid': file_uuid.hex})
        else:
            # Image is split up into multiple chunks.
            reservation = await self.controller.reserve(connection, request.requester.uuid, md5, size, MimeTypes(mime))
            await self.controller.write_chunk(connection, reservation, _bytes, index)
            return JSONResponse({'uuid': reservation.hex})

    async def on_put(self, request: RequestInterface, connection: SQLConnectionInterface, logger: Logger, model: Model = None,
                     reservation_uuid=None) -> ResponseInterface:
        """Uploads chunks for reservations.

       If the image is final set the finalize parameter to true, otherwise to false.

        Args:
            request: Route request.
            connection: Connection to database.
            logger: Activity logger.
            model: Model for which this image is meant for.

        Returns:
            JSONResponse containing the file uuid if it is the last chunk.
        """
        if reservation_uuid is None:
            self.raise_bad_request("Please add reservation uuid to request.")

        await self.check_request_validity(connection, request.requester, model, reservation_uuid)

        index = int(request.get_param('index', 0))
        finalize = request.get_param('finalize', 'false') == 'true'

        _bytes = await request.get_body_bytes()

        if not finalize:
            await self.controller.write_chunk(connection, reservation_uuid, _bytes, index)
            return SuccessfulResponse()
        else:
            file_uuid = await self.controller.finalize(connection, reservation_uuid, self.is_public, _bytes)
            await self.link_uploaded_image(request, connection, logger, model, file_uuid)
            return JSONResponse({'uuid': file_uuid.hex})

    async def on_delete(self, request: RequestInterface, connection: SQLConnectionInterface, logger: Logger, model: Model = None,
                        reservation_uuid=None) -> ResponseInterface:
        """Deletes a reservation.

        Args:
            request: Route request.
            connection: Connection to database.
            logger: Activity logger.
            model: Model for which this image is meant for.
        """
        if reservation_uuid is None:
            self.raise_bad_request("Please add reservation uuid to request.")

        await self.check_request_validity(connection, request.requester, model, reservation_uuid)

        await self.controller.delete_reservation(connection, reservation_uuid)

        return SuccessfulResponse()
