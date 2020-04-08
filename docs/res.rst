=========
Resources
=========

.. contents:: :local:

Introduction
============

A resource is an object which handles a request from a user.
In this module there are a few handy implementations.

Examples
==============

--------------
Authentication
--------------

The :class:`~tedious.res.auth_resource.AuthResource` is capable of signing in users and refreshing their tokens.
Create a main.py file, paste the code below into it and run it using ``uvicorn main:app``

::

    import tedious.config
    from tedious.asgi.starlette import ResourceController, StarletteApp
    from tedious.res.auth_resource import AuthResource
    from tedious.sql.postgres import PostgreSQLDatabase
    from starlette.routing import Route

    tedious.config.load_config('config.ini')

    controller = ResourceController(PostgreSQLDatabase(**tedious.config.CONFIG["DB_CREDENTIALS"]))

    async def login(request):
        return await controller.handle(request, AuthResource())

    app = StarletteApp(controller, [Route('/login', login, methods=["POST", "PUT", "DELETE"])]).app

Now if you simply run a ``POST`` request onto ``http://localhost:8000/login`` containing the json beneath you will receive the access and refresh token for the user.
This obviously requires that the user exists, otherwise :ref:`learn here how to do it<registering_user>`.

::

    {
        "username": "test-user",
        "password": "12345678"
    }

Now if you want to refresh an access token, send the refresh token with a ``PUT`` request onto ``http://localhost:8000/login``.
The refresh token must be in the body of the request, not formatted into json or anything.

-------------
Form resource
-------------

The :class:`~tedious.res.form_resource.FormResource` is used to create, update and delete models using the :class:`~tedious.mdl.model_controller.ModelController`.

::

    import tedious.config
    from tedious.asgi.starlette import ResourceController, StarletteApp
    from tedious.sql.postgres import PostgreSQLDatabase
    from starlette.routing import Route
    from tedious.res.form_resource import FormResource

    tedious.config.load_config('config.ini')

    controller = ResourceController(PostgreSQLDatabase(**tedious.config.CONFIG["DB_CREDENTIALS"]))

    # Use your model and matching model controller here.
    resource = FormResource(User, UserController(), 'uuid')

    async def model_form(request):
        return await controller.handle(request, resource)

    app = StarletteApp(controller, [
        # This route can only create models, not fetch or update them
        Route('/form', model_form, methods=["POST"])
        # Same route but the uuid is already known, therefore fetching and updating is also possible.
        Route('/form/<uuid>', model_form, methods=["GET", "POST", "PUT", "DELETE"])
    ]).app

Now with a ``POST`` onto ``http://localhost/form`` containing the model as json in the body, you can create your model. Make sure your model controller
sets the uuid if it is missing and that the requester is granted the :class:`tedious.model.model_controller.ManipulationPermission.CREATE` permission.

Then if you want to update the same model, use the UUID received from the ``POST`` request to make a ``PUT`` call onto the same request appended by the UUID, like ``http://localhost/form/model_uuid_here``.
The request should again, contain the values as json in the body.

At last, the model can be deleted by a ``DELETE`` request onto ``http://localhost/form/model_uuid_here``

-------------
List resource
-------------

The :class:`~tedious.res.list_resource.ListResource` helps you to list your models from the database.

::

    import tedious.config
    from tedious.asgi.starlette import ResourceController, StarletteApp
    from tedious.sql.postgres import PostgreSQLDatabase
    from starlette.routing import Route
    from tedious.res.list_resource import ListResource

    tedious.config.load_config('config.ini')

    controller = ResourceController(PostgreSQLDatabase(**tedious.config.CONFIG["DB_CREDENTIALS"]))

    # Use your model and matching model controller here.
    # Only requester's with the role admin will be able to see the columns uuid and display_name.
    resource = ListResource(UserListController(), {'admin': ['uuid', 'display_name']}

    async def model_list(request):
        return await controller.handle(request, resource)

    app = StarletteApp(controller, [
        Route('/list', model_list, methods=["GET"])
    ]).app

Now to list your models, call ``http://localhost/list``.

------
Images
------

There are two important resources for images.
The first one :class:`~tedious.res.image_resource.ImageResource` is solely to retrieve and delete images.
The other one :class:`~tedious.res.image_form_resource.ImageFormResource` is for uploading images as one or as chunks.

::

    import tedious.config
    from tedious.asgi.starlette import ResourceController, StarletteApp
    from tedious.sql.postgres import PostgreSQLDatabase
    from starlette.routing import Route
    from tedious.res.image_resource import ImageResource
    from tedious.res.image_form_resource import ImageFormResource
    from tedious.stg.storage import Storage, MimeTypes
    from tedious.stg.storage_upload import StorageUploadController

    tedious.config.load_config('config.ini')

    controller = ResourceController(PostgreSQLDatabase(**tedious.config.CONFIG["DB_CREDENTIALS"]))

    # Switch UserController to your model controller.
    # For a requester to be allowed to view the image, he must have a READ permission on profile_picture.uuid.
    resource = ImageResource(Storage(), UserController(), 'profile_picture.uuid')
    # A requester must have the ManipulationPermissions.CREATE_UPDATE_DELETE for creating images.
    form_resource = ImageFormResource(StorageUploadController(), UserController(), 'profile_picture', [MimeTypes.IMAGE_JPEG, MimeTypes.IMAGE_PNG], True)

    async def image(request):
        return await controller.handle(request, resource)

    async def form(request):
        return await controller.handle(request, form_resource)

    app = StarletteApp(controller, [
        Route('/image/<uuid>', image, methods=["GET", "DELETE"])
        Route('/form/image', form, methods=["POST"])
        Route('/form/image/<uuid>', form, methods=["POST", "PUT", "DELETE"])
    ]).app

First if you want to create an image, send a ``POST`` request onto ``http://localhost/form/image?finalize=true``,
the request must contain the Content-MD5, Content-Type and Final-Content-Length HTTP headers. Simply put the image bytes into the body, you will receive the images uuid in the response.
Now if you want to retrieve the image call ``http://localhost/image/image_uuid_here`` with ``GET``.
If you do not want to send the image as one, but rather as chunks, firstly send a ``POST`` request onto ``http://localhost/form/image?finalize=false`` with the first chunk of your preferred size in the body, you will receive a reservation uuid in the response,
then ``PUT`` onto ``http://localhost/form/image/reservation_uuid_here?finalize=false`` until there are no chunks left, on the last chunk set finalize to true.


Classes
=======

------------
AuthResource
------------

.. autoclass:: tedious.res.auth_resource.AuthResource
    :members:

-------------
ImageResource
-------------

.. autoclass:: tedious.res.image_resource.ImageResource
    :members:

-----------------
ImageFormResource
-----------------

.. autoclass:: tedious.res.image_form_resource.ImageFormResource
    :members:

------------
FormResource
------------

.. autoclass:: tedious.res.form_resource.FormResource
    :members:

------------
ListResource
------------

.. autoclass:: tedious.res.list_resource.ListResource
    :members:
