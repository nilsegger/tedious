from tedious.asgi.resource_interface import HTTPNotFound, HTTPForbidden
from tedious.asgi.response_interface import JSONResponse, SuccessfulResponse
from tedious.auth.auth import Requester
from tedious.res.form_resource import FormResource
from tedious.tests.util import MockRequest
from tedious.tests.res.mocks import MockUser, MockUserController, MockRoles
from tedious.util import create_uuid
import pytest
from tedious.tests.util import compare, randomize


@pytest.mark.asyncio
async def test_on_get():
    user = randomize(MockUser())
    controller = MockUserController()
    await controller.create(None, user)

    resource = FormResource(MockUser, controller, 'uuid')

    request = MockRequest(requester=Requester(role=MockRoles.ADMIN.value))
    response = await resource.on_get(request, None, None, MockUser(user["uuid"].value))
    assert isinstance(response, JSONResponse)
    assert response.body["uuid"] == user["uuid"].value.hex

    with pytest.raises(HTTPNotFound):
        await resource.on_get(request, None, None, MockUser(create_uuid()))

    with pytest.raises(HTTPForbidden):
        await resource.on_get(MockRequest(), None, None, MockUser(user["uuid"].value))

    with pytest.raises(HTTPForbidden):
        await resource.on_get(MockRequest(requester=Requester(role=MockRoles.USER.value, uuid=create_uuid())), None, None, MockUser(user["uuid"].value))


@pytest.mark.asyncio
async def test_on_post():
    user = randomize(MockUser())
    controller = MockUserController()
    resource = FormResource(MockUser, controller, 'uuid')

    request = MockRequest(requester=Requester(role=MockRoles.ADMIN.value), body_json=await user.output(user.keys()))
    response = await resource.on_post(request, None, None, MockUser(user["uuid"].value))
    assert isinstance(response, JSONResponse)
    assert response.body["uuid"] == user["uuid"].value.hex
    assert user["uuid"].value in controller.db
    compare(controller.db[user["uuid"].value], user)


@pytest.mark.asyncio
async def test_on_put():
    user = randomize(MockUser())
    controller = MockUserController()
    await controller.create(None, user)

    tmp_uuid = user["uuid"].value
    randomize(user)
    user["uuid"].value = tmp_uuid

    resource = FormResource(MockUser, controller, 'uuid')

    request = MockRequest(requester=Requester(role=MockRoles.ADMIN.value), body_json=await user.output(user.keys()))
    response = await resource.on_put(request, None, None, MockUser(user["uuid"].value))
    assert isinstance(response, SuccessfulResponse)
    assert user["uuid"].value in controller.db
    compare(controller.db[user["uuid"].value], user)


@pytest.mark.asyncio
async def test_on_delete():
    user = randomize(MockUser())
    controller = MockUserController()
    await controller.create(None, user)

    resource = FormResource(MockUser, controller, 'uuid')
    request = MockRequest(requester=Requester(role=MockRoles.ADMIN.value))
    response = await resource.on_delete(request, None, None, MockUser(user["uuid"].value))
    assert isinstance(response, SuccessfulResponse)
    assert user["uuid"].value not in controller.db
