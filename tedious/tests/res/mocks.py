from enum import Enum
from typing import Tuple, Dict, Any, List

from tedious.auth.auth import Requester
from tedious.mdl.fields import UUIDField, StrField
from tedious.mdl.model import Model, Permissions
from tedious.mdl.model_controller import ModelController, ManipulationPermissions


class MockRoles(Enum):
    USER = 'user'
    ADMIN = 'admin'


class MockUser(Model):

    def __init__(self, uuid=None):
        super().__init__(None, [UUIDField('uuid', value=uuid), StrField('name'), StrField('image')])


class MockUserController(ModelController):

    def __init__(self):
        super().__init__(None, 'uuid', None)
        self.db = {}

    async def get(self, connection, model: Model, columns=None, join_foreign_keys=False):
        if model["uuid"].value in self.db:
            return self.db[model["uuid"].value]
        else:
            return None

    @property
    def identifiers(self) -> List[str]:
        return ['uuid']

    async def create(self, connection, model: Model):
        self.db[model["uuid"].value] = model
        return model

    async def update(self, connection, model: Model, _global: Model = None):
        await self.db[model["uuid"].value].copy(model, True)
        return model

    async def delete(self, connection, model: Model, _global: Model = None):
        del self.db[model["uuid"].value]

    async def get_manipulation_permissions(self, requester: Requester, model: Model) -> Tuple[ManipulationPermissions, Dict[str, Any]]:
        if requester.role == MockRoles.ADMIN.value:
            return ManipulationPermissions.CREATE_UPDATE_DELETE, {'image': ManipulationPermissions.CREATE_UPDATE_DELETE}
        elif requester.uuid == model["uuid"].value:
            return ManipulationPermissions.UPDATE, {'image': ManipulationPermissions.CREATE_UPDATE_DELETE}
        else:
            return ManipulationPermissions.NONE, {}

    async def get_permissions(self, requester: Requester, model: Model):

        if requester.role == MockRoles.ADMIN.value or requester.uuid == model["uuid"].value:
            return {'uuid': Permissions.READ, 'name': Permissions.READ_WRITE, 'image': Permissions.READ_WRITE}
        else:
            return {'name': Permissions.READ, 'image': Permissions.READ}

    async def get_permissions_for_role(self, role):
        if role == MockRoles.ADMIN.value:
            return {'uuid': Permissions.READ, 'name': Permissions.READ_WRITE, 'image': Permissions.READ_WRITE}
        else:
            return {'name': Permissions.READ, 'image': Permissions.READ}

