from typing import List

import pytest

from tedious.auth.auth import Requester
from tedious.mdl.list_controller import ListController
from tedious.mdl.model import Model
from tedious.mdl.model_controller import ModelController
from tedious.res.list_resource import ListResource, StaticListResource
from tedious.tests.res.mocks import MockUser, MockRoles, MockUserController
from tedious.tests.util import randomize, MockRequest
import tedious.config

tedious.config.load_config('tedious/tests/config.ini')


def remove_from_list(to_remove, _list):
    for uuid in to_remove:
        found = False
        for i in range(len(_list) - 1, -1, -1):
            if uuid == _list[i]:
                _list.pop(i)
                found = True
                break
        assert found


class MockListController(ListController):

    def __init__(self, values):
        self.values = values
        super().__init__(None)

    async def get(self, connection, limit=25, offset=0, join_foreign_keys=False) -> List[Model]:
        return self.values[offset: offset + limit]

@pytest.mark.asyncio
async def test_list_resource():
    mocks = [randomize(MockUser()) for _ in range(25)]
    controller = MockListController(mocks)

    uuids = [user["uuid"].value.hex for user in mocks]

    resource = StaticListResource(controller, [MockRoles.ADMIN], ['uuid'], limit=15)
    request = MockRequest(requester=Requester(role=MockRoles.ADMIN))
    resp = (await resource.on_get(request, None, None)).body["list"]
    remove_from_list([user["uuid"] for user in resp], uuids)

    request = MockRequest(requester=Requester(role=MockRoles.ADMIN), params={'offset': '15'})
    resp = (await resource.on_get(request, None, None)).body["list"]
    remove_from_list([user["uuid"] for user in resp], uuids)

    assert len(uuids) == 0