=======
Storage
=======

.. contents:: :local:

Introduction
============

The storage module helps you safely store and upload files and foremost images.

Examples
========

------------------
Uploading an image
------------------

::

    from tedious.stg.storage import Storage
    from tedious.sql.postgres import PostgresSQLDatabase, Connection

    # Create a connection to the database.
    database = PostgreSQLDatabase(database='tedious', user='postgres', password='postgres')
    await database.connect()
    connection = await database.acquire()

    storage = Storage()

    with open('test.jpeg', 'rb') as f:
        _bytes = f.read()

    # To remember who saved this file, pass along the owner_uuid referencing the users login.

    file_uuid = await storage.save(connection, owner_uuid, _bytes, MimeTypes.IMAGE_JPEG, True)

-------------------
Retrieving an image
-------------------

::

    _bytes, mime_type, is_public = await storage.retrieve(connection, file_uuid)

-----------------
Deleting an image
-----------------

::

    await storage.remove(connection, file_uuid)

---------------------------
Uploading images from users
---------------------------

If you have to work with images from users, sometimes the preferred way to upload images is by splitting it up into chunks.
To do this use the :class:`~tedious.stg.storage_upload.StorageUploadController`.

::

    controller = StorageUploadController()

    # The md5_hash is the hash of the file to upload. This is saved to check that the merge of the chunks was successful.
    reservation_uuid = await controller.reserve(self, connection, owner, md5_hash, byte_size, mime)

    # Start saving chunks
    await controller.write_chunk(self, connection, reservation_uuid, _bytes, index)

    # Then finalize by calling
    file_uuid = await controller.finalize(connection, reservation_uuid, is_public)

    # If you want to retrieve the final image
    _bytes, mime_type, is_public = await Storage().retrieve(connection, file_uuid)

Classes
=======
----------
Mime Types
----------

.. autoclass:: tedious.stg.storage.MimeTypes

-------
Storage
-------

.. autoclass:: tedious.stg.storage.Storage
    :members:

-----------------------
StorageUploadController
-----------------------

.. autoclass:: tedious.stg.storage_upload.StorageUploadController
    :members:

----------
Exceptions
----------

.. autoclass:: tedious.stg.storage_upload.ReservationNotFound
.. autoclass:: tedious.stg.storage_upload.InvalidByteSize
.. autoclass:: tedious.stg.storage_upload.InvalidBytes
.. autoclass:: tedious.stg.storage_upload.InvalidMimeType
.. autoclass:: tedious.stg.storage_upload.InvalidFileHash
