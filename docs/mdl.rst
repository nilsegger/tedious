=====
Model
=====

.. contents:: :local:

Introduction
============

The model module brings fourth classes which makes it easier to handle and manipulate data.

Examples
========

----------------
Creating a model
----------------

.. literalinclude:: ../examples/mdl.py
    :lines: 5-29

------------
Setting data
------------

.. literalinclude:: ../examples/mdl.py
    :lines: 5-48

---------------
Retrieving data
---------------

.. literalinclude:: ../examples/mdl.py
    :lines: 5-29, 51-64

---------------
Validating data
---------------

.. literalinclude:: ../examples/mdl.py
    :emphasize-lines: 20
    :lines: 5-29, 68-72

-----------------------
Using model controllers
-----------------------
A model controller helps you create, update and delete models from a database.
Simple override the :class:`~tedious.mdl.model_controller.ModelController` class. A controller for the User class could look like the following.

::

    def __init__(self):
        super().__init__('users', 'uuid', {})

    async def _model_to_sql_values(self, model: User):
        return model["uuid"].value, model["address"]["street"].value, model["address"]["country"].value

    async def _insert_stmt(self):
        return "INSERT INTO users(uuid, address_street, address_country) VALUES($1, $2, $3)"

    async def _update_stmt(self):
        return "UPDATE users SET address_street=COALESCE($2, address_street), address_country=COALESCE($3, address_country) WHERE uuid=$1

    async def get_manipulation_permissions(self, requester: Requester, model: Model) -> Tuple[ManipulationPermissions, Dict[str, Any]]:
        # The second response value, is a dict containing manipulation permissions for sub fields, like the profile picture of a user
        if requester.role == "admin" or requester.uuid == model["uuid"].value:
            return ManipulationPermissions.CREATE_UPDATE_DELETE, {}
        return ManipulationPermissions.NONE, {}

    async def get_permissions(self, requester: Requester, model: Model):
        if requester.role == "admin" or requester.uuid == model["uuid"].value:
            return {'uuid': Permissions.READ, 'address': {'street': Permissions.READ_WRITE, 'country': Permissions.READ_WRITE}}
        return {}

    async def get_permissions_for_role(self, role: Roles):
        if role == "admin":
            return {'uuid': Permissions.READ, 'address': {'street': Permissions.READ_WRITE, 'country': Permissions.READ_WRITE}}
        else:
            return {}

    async def validate(self, model: Model, _type: ValidationTypes):
        if _type == ValidationTypes.CREATE:

            if model["uuid"].value is None:
                model["uuid"].value = create_uuid()

            await model.validate_not_empty(['display_name', 'address.street', 'address.country'])

    # Now you can simply call
    controller = UserController()
    user = User() # Set values first of course.
    connection = SQLConnectionInterface() # Create proper connection
    await controller.create(connection, user)
    await controller.update(connection, user)
    await controller.delete(connection, user)

Classes
=======

-----------
Permissions
-----------

.. autoclass:: tedious.mdl.model.Permissions
    :members:

-------
IOModel
-------

.. autoclass:: tedious.mdl.model.IOModel
    :members:

---------
Model
---------

.. autoclass:: tedious.mdl.model.Model
    :members:

-------
Field
-------

.. autoclass:: tedious.mdl.model.Field
    :members:

---------------
ModelController
---------------

.. autoclass:: tedious.mdl.model.Field
    :members:


------------------
StrField
------------------

.. autoclass:: tedious.mdl.fields.StrField
    :members:

---------
IntField
---------

.. autoclass:: tedious.mdl.fields.IntField
    :members:

---------
UUIDField
---------

.. autoclass:: tedious.mdl.fields.UUIDField
    :members:

-------------
DateTimeField
-------------

.. autoclass:: tedious.mdl.fields.DateTimeField
    :members:

---------
EnumField
---------

.. autoclass:: tedious.mdl.fields.EnumField
    :members:

---------
BoolField
---------

.. autoclass:: tedious.mdl.fields.BoolField
    :members:
