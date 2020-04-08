import pytest
import asyncio
from tedious.mdl.fields import StrField
from tedious.mdl.model import Model, ValidationError, Permissions


class MockAddressModel(Model):

    def __init__(self, name: str):
        super().__init__(name, [
            StrField('street', min_len=1, max_len=30),
            StrField('country', min_len=1, max_len=30)
        ])


class MockUserModel(Model):

    def __init__(self, name: str = None):
        super().__init__(name, [
            StrField('name', min_len=3, max_len=15),
            MockAddressModel('address')
        ])


def test_empty():
    mock = MockUserModel()
    assert mock.empty


def test_keys():
    mock = MockUserModel()
    keys = mock.keys()
    assert len(keys) == 3
    assert 'name' in keys
    assert 'address.street' in keys
    assert 'address.country' in keys


@pytest.mark.asyncio
async def test_validate_not_empty():
    mock = MockUserModel()
    mock["name"] = "Valid name"
    mock["address"]["street"] = "Valid street"
    mock["address"]["country"] = "Valid country"
    await mock.validate_not_empty(['name', 'address.street', 'address.country'])
    mock["name"] = None
    mock["address"]["country"] = None

    with pytest.raises(ValidationError) as exception:
        await mock.validate_not_empty(['address.country', 'name'])

    assert 'name' in exception.value.fields
    assert 'address.country' in exception.value.fields

    with pytest.raises(ValidationError) as exception:
        await mock.validate_not_empty(['address.street', 'address.country'])

    assert 'address.country' in exception.value.fields


@pytest.mark.asyncio
async def test_validate():
    mock = MockUserModel()
    mock["name"] = "Valid name"
    mock["address"]["street"] = "Valid street"
    mock["address"]["country"] = "Valid country"
    await mock.validate_content()

    with pytest.raises(ValidationError) as exception:
        mock["name"] = "Invalid name that is way too long!"
        mock["address"]["street"] = "Invalid street that is way too long!"
        mock["address"]["country"] = "Invalid country that is way too long!"
        await mock.validate_content()

    assert 'name' in exception.value.fields
    assert 'address.street' in exception.value.fields
    assert 'address.country' in exception.value.fields


@pytest.mark.asyncio
async def test_input():
    inp = {
        'name': 'John Doe',
        'address': {
            'street': 'Dorfstrasse',
            'country': 'Schweiz'
        }
    }
    mock = await MockUserModel().input(inp)
    assert mock["name"].value == inp["name"], "Actual {} does not equal expected {}".format(mock["name"], inp["name"])
    assert mock["address"]["street"].value == inp["address"]["street"], "Actual {} does not equal expected {}".format(mock["address"]["street"],
                                                                                                                      inp["address"]["street"])
    assert mock["address"]["country"].value == inp["address"]["country"], "Actual {} does not equal expected {}".format(mock["address"]["country"],
                                                                                                                        inp["address"]["country"])

    mock = await MockUserModel().input(inp, permissions={'name': Permissions.NONE, 'address': {'street': Permissions.WRITE, 'country': Permissions.READ}})
    assert mock["name"].value is None
    assert mock["address"]["street"].value == inp["address"]["street"]
    assert mock["address"]["country"].value is None


@pytest.mark.asyncio
async def test_output():
    mock = MockUserModel()
    mock["name"] = "Valid name"
    mock["address"]["street"] = "Valid street"
    mock["address"]["country"] = "Valid country"
    response = await mock.output(['name', 'address.street', 'address.country'])
    assert response == {"name": mock["name"].value,
                        "address": {"country": mock["address"]["country"].value, "street": mock["address"]["street"].value}}


@pytest.mark.asyncio
async def test_copy():
    mock = MockUserModel()
    mock["name"] = "Valid name"
    mock["address"]["street"] = "Valid street"
    mock["address"]["country"] = "Valid country"
    copy = MockUserModel()
    await copy.copy(mock, True)
    assert copy["name"].value == mock["name"].value
    assert copy["address"]["street"].value == mock["address"]["street"].value
    assert copy["address"]["country"].value == mock["address"]["country"].value

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(test_keys())