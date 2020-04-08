from enum import Enum
from typing import List, Dict, Tuple, Any

from tedious.auth.auth import Requester
from tedious.mdl.model import Model, Permissions
from tedious.sql.interface import SQLConnectionInterface
from tedious.util import KeyPathsIter


class ValidationTypes(Enum):
    CREATE = 1
    UPDATE = 2
    DELETE = 3


class ManipulationPermissions(Enum):
    NONE = 0
    CREATE = 1
    UPDATE = 2
    DELETE = 3
    CREATE_UPDATE = 4
    CREATE_UPDATE_DELETE = 5


CREATE_PERMISSIONS = [ManipulationPermissions.CREATE,
                      ManipulationPermissions.CREATE_UPDATE,
                      ManipulationPermissions.CREATE_UPDATE_DELETE]
UPDATE_PERMISSIONS = [ManipulationPermissions.UPDATE,
                      ManipulationPermissions.CREATE_UPDATE,
                      ManipulationPermissions.CREATE_UPDATE_DELETE]
DELETE_PERMISSIONS = [ManipulationPermissions.DELETE,
                      ManipulationPermissions.CREATE_UPDATE_DELETE]
VIEW_PERMISSIONS = CREATE_PERMISSIONS + UPDATE_PERMISSIONS


class ModelController:
    """The model controller simplifies create, updating and deleting models from a database."""
    __slots__ = ('table', 'identifier_key')

    def __init__(self, table: str, identifier_key: str):
        self.table = table
        self.identifier_key = identifier_key

    async def _select_stmt(self, model: Model, join_foreign_keys=False):
        """Returns statement used to fetch row.

        Args:
            model: Model to fetch.
            join_foreign_keys: if true, joins all foreign keys.

        Returns:
            String of SQL statement.
        """

        raise NotImplementedError

    async def _insert_stmt(self):
        """Returns statement used to insert row into table."""
        raise NotImplementedError

    async def _insert_values(self, model: Model):
        """Returns tuple of values needed for insert.

        Returns:
            All values in a tuple required to create and update models.
        """

        raise NotImplementedError

    async def _update_stmt(self):
        """Returns sql statement for updating the model."""
        raise NotImplementedError

    async def _update_values(self, model: Model):
        """Returns tuple of values needed for update.

        Returns:
            All values in a tuple required to create and update models.
        """

        raise NotImplementedError

    async def _delete_stmt(self):
        """Returns sql statement for deleting a model."""
        return "DELETE FROM {} WHERE {}=$1".format(self.table,
                                                   self.identifier_key)

    async def get(self, connection: SQLConnectionInterface, model: Model,
                  join_foreign_keys=False):
        """Retrieve model from database.

        Args:
            model: Model to retrieve, identifier key can not be null.
            join_foreign_keys: If true, foreign keys will be joined.

        Returns:
            If model is found, model, else None
        """

        assert model[self.identifier_key].value is not None
        stmt = await self._select_stmt(model, join_foreign_keys)
        return await connection.fetch_model(model, stmt,
                                            model[self.identifier_key].value)

    @property
    def identifiers(self) -> List[str]:
        """Returns list of key paths for fields which are needed to identify model and submodels."""
        raise NotImplementedError

    async def create(self, connection: SQLConnectionInterface, model: Model):
        """Creates model in database."""
        await self.validate(connection, model, ValidationTypes.CREATE)
        await connection.execute(await self._insert_stmt(),
                                 *await self._insert_values(model))
        return model

    async def update(self, connection: SQLConnectionInterface, model: Model,
                     _global: Model = None):
        """Updates model in database."""
        await self.validate(connection, model, ValidationTypes.UPDATE)
        await connection.execute(await self._update_stmt(),
                                 *await self._update_values(model))

    async def delete(self, connection: SQLConnectionInterface, model: Model,
                     _global: Model = None):
        """Delete model and associated data from database."""
        await self.validate(connection, model, ValidationTypes.DELETE)
        await connection.execute(await self._delete_stmt(),
                                 model[self.identifier_key].value)

    async def get_manipulation_permissions(self, requester: Requester,
                                           model: Model) -> Tuple[
        ManipulationPermissions, Dict[str, Any]]:
        """Returns Tuple containing ManipulationPermission for model itself and Dict [str, ManipulationPermission] containing permissions for images or alike.
            ManipulationPermissions.CREATE, {
                'avatar': ManipulationPermissions.CREATE_UPDATE_DELETE
            }
        """
        raise NotImplementedError

    async def _iterate_dict(self, d, key_path, default):
        """Iterates through dict using a single key path."""
        key, _iter = KeyPathsIter([key_path]).__next__()
        while _iter is not None:
            if key not in d:
                return default
            d = d[key]
            key, _iter = _iter.__next__()
        if key not in d:
            return default
        return d[key]

    async def get_manipulation_permission(self, requester: Requester,
                                          model: Model, key_path=None):
        """Iterates through manipulation permissions dict accoring to key path, if key path is None, returns manipulation permission of complete model."""
        if key_path is None:
            return (await self.get_manipulation_permissions(requester, model))[
                0]
        permissions = \
        (await self.get_manipulation_permissions(requester, model))[1]
        return await self._iterate_dict(permissions, key_path,
                                        ManipulationPermissions.NONE)

    async def get_permissions(self, requester: Requester, model: Model):
        """Returns Dict[str, Permissions]
        {
            "uuid": Permissions.READ,
            "avatar": {
                "path": Permissions.READ,
                "public": Permissions.READ
            }
            "display_name": Permissions.READ_WRITE
            "email": Permissions.NONE
        }
        """
        raise NotImplementedError

    async def get_permissions_for_role(self, role):
        """Same as get_permissions, but permissions are simplified to roles, instead of single model."""
        raise NotImplementedError

    async def get_permission(self, requester: Requester, model: Model,
                             key_path):
        """Returns single permission for field."""
        permissions = await self.get_permissions(requester, model)
        return await self._iterate_dict(permissions, key_path,
                                        Permissions.NONE)

    async def validate(self, connection: SQLConnectionInterface, model: Model,
                       _type: ValidationTypes):
        """Validate model for given validation type."""
        raise NotImplementedError
