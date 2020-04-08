"""
    This example shows how you would create you own model.
"""

from tedious.mdl.model import Model, Permissions
from tedious.mdl.fields import *
from tedious.util import create_uuid


class Address(Model):

    def __init__(self, name):
        super().__init__(name, [
            StrField('street'),
            StrField('country')
        ])


class User(Model):

    def __init__(self, name=None):
        super().__init__(name, [
            UUIDField('uuid'),
            StrField('display_name', min_len=5, max_len=30),
            Address('address')
        ])


user = User()

# Setting data
user["uuid"].value = create_uuid()


async def input_example():
    # Setting data from JSON
    json = {
        'uuid': '794812a6db27744f9773d82009a1c808',
        'display_name': 'Hello World!',
        'address': {
            'street': 'Dorfstrasse',
            'country': 'Schweiz'
            }
    }
    await user.input(json)

    # Setting permission for fields, now only display_name will be set.
    await user.input(json, {'display_name': Permissions.WRITE})

# Retrieving data
uuid = user["uuid"].value

async def output_example():
    output = await user.output(['uuid', 'display_name', 'address.street',
                                'address.country'])
    # This will result in:
    # {
    #   'uuid': '794812a6db27744f9773d82009a1c808',
    #   'display_name': 'Hello World!',
    #   'address': {
    #       'street': 'Dorfstrasse',
    #       'country': 'Schweiz'
    #    }
    # }

# Validating Data

async def validation_example():
    # Will throw error because of min_len=5
    inp = {'display_name': 'Ted'}
    user = await User().input(inp, permissions={
        'display_name': Permissions.READ}, validate_fields=['display_name'])

