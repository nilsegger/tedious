from datetime import datetime
from enum import Enum
from uuid import UUID
import typing

from tedious.mdl.model import ValidationError, Field


def _check_type(name, value, expected_type):
    if not isinstance(value, expected_type):
        raise ValidationError([name], "'{}' with a value of '{}' is not of type {}.".format(name, value, expected_type))


class StrField(Field):
    """Fields which contains a value of type string."""

    __slots__ = ('min_len', 'max_len')

    def __init__(self, name, value=None, min_len=None, max_len=None):
        super().__init__(name, value)
        self.min_len = min_len
        self.max_len = max_len

    async def validate_content(self):
        """Checks min_len and max_len if value is not None."""

        if self.value is not None:

            _check_type(self.name, self.value, str)

            if self.min_len is not None and len(self.value) < self.min_len:
                raise ValidationError([self.name],
                                      "{} does not meet min length of {} with a length of {}".format(self.name, self.min_len, len(self.value)))
            elif self.max_len is not None and len(self.value) > self.max_len:
                raise ValidationError([self.name],
                                      "{} does not exceeds max length of {} with a length of {}".format(self.name, self.max_len, len(self.value)))

    async def input(self, inp, permissions=None, validate_fields=None):
        """Checks if length of String is greater than 0."""
        if inp is None or len(inp) == 0:
            self.value = None
        else:
            return await super().input(inp, permissions, validate_fields)


class IntField(Field):
    """Fields which contains a value of type int or double."""

    __slots__ = ('min_val', 'max_val')

    def __init__(self, name, value=None, min_val=None, max_val=None):
        super().__init__(name, value)
        self.min_val = min_val
        self.max_val = max_val

    async def validate_content(self):
        """Compare value to min_val and max_val if value is not None."""

        if self.value is not None:

            _check_type(self.name, self.value, int)

            if self.min_val is not None and self.value < self.min_val:
                raise ValidationError([self.name], "'{}' is smaller than min value for field {}".format(self.value, self.name))
            elif self.max_val is not None and self.value < self.max_val:
                raise ValidationError([self.name], "'{}' is larger than max value for field {}".format(self.value, self.name))


class UUIDField(Field):
    """Fields which contains a value of type UUID."""

    def __init__(self, name, value=None):
        super().__init__(name, value)

    async def input(self, inp, permissions: typing.Dict = None, validate_fields=None):
        """Reads input as UUID hex and returns self."""
        if isinstance(inp, UUID):
            self.value = inp
        elif inp is not None:
            self.value = UUID(hex=inp)
        else:
            self.value = None
        return self

    async def output(self, fields=None, permissions: typing.Dict = None):
        """

        Args:
            fields: None for field.
            permissions: None for field.

        Returns:
            Field value
        """
        output = await super().output(fields)
        if output is not None:
            return output.hex
        return None

    async def validate_content(self):
        """Checks if value is indeed a UUID."""
        if self.value is not None:
            _check_type(self.name, self.value, UUID)


class DateTimeField(Field):
    """Holds a value of type datetime."""
    __slots__ = ('must_be_future', 'min_age', 'max_age')

    def __init__(self, name, value=None, must_be_future=False, min_age: int = None, max_age: int = None):
        """

        Args;
            must_be_future: If true, validate will raise ValidationError if timestamp does not lay in future.
            min_age: Min age in seconds which timestamp must possess.
            max_age: Max age in seconds which timestamp is allowed to posses.
        """
        super().__init__(name, value)
        self.must_be_future = must_be_future
        self.min_age = min_age
        self.max_age = max_age

    async def input(self, inp, permissions: typing.Dict = None, validate_fields=None):
        """Reads input as posix timestamp and returns self."""
        if isinstance(inp, datetime):
            self.value = inp
        elif inp is not None:
            self.value = datetime.fromtimestamp(inp)
        else:
            self.value = None
        return self

    async def output(self, fields=None, permissions: typing.Dict = None):
        """Outputs value as timestamp."""
        output = await super().output(fields)
        if output is not None:
            return output.timestamp()
        return None

    async def validate_content(self):
        """Validates to check age."""
        if self.value is not None:
            _check_type(self.name, self.value, datetime)

            if self.must_be_future and datetime.now().timestamp() > self.value.timestamp():
                raise ValidationError([self.name], "{} does not lay in future.".format(self.name))
            elif self.min_age is not None and datetime.now().timestamp() - self.value.timestamp() < self.min_age:
                raise ValidationError([self.name], "{} does not posses min age of {} seconds.".format(self.name, self.min_age))
            elif self.max_age is not None and datetime.now().timestamp() - self.value.timestamp() > self.max_age:
                raise ValidationError([self.name], "{} does exceeds max age of {} seconds.".format(self.name, self.max_age))


class EnumField(Field):
    """Contains a value which must be a type of an enu,."""

    __slots__ = ('enum_class',)

    def __init__(self, name, enum_class: type(Enum) = None, value=None):
        super().__init__(name, value)
        self.enum_class = enum_class

    async def input(self, inp, permissions: typing.Dict = None, validate_fields=None):
        """Converts input into enum."""
        if isinstance(inp, self.enum_class):
            self.value = inp
        elif isinstance(inp, str):
            self.value = self.enum_class(inp)
        else:
            self.value = inp

        return self

    async def output(self, fields=None, permissions: typing.Dict = None):
        """Output enum as string."""
        output = await super().output(fields)
        if output is not None:
            return output.value
        return None

    async def validate_content(self):
        """Validates to check value that it is really a type of enum."""
        if self.value is not None:
            _check_type(self.name, self.value, self.enum_class)


class BoolField(Field):
    """Contains a value of boolean."""

    async def validate_content(self):
        """Validates value to be a type of bool."""
        if self.value is not None:
            _check_type(self.name, self.value, bool)