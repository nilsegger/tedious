import typing
from enum import Enum
from typing import Iterator

from tedious.util import KeyPathsIter


class ValidationError(Exception):
    """Raised if model or field is invalid. Contains list of all invalid fields."""

    def __init__(self, fields, *args):
        self.fields = fields
        super().__init__(*args)


class UnsupportedError(Exception):
    pass


class Permissions(Enum):
    """Enum of permissions for IO.

    NONE, READ, WRITE, READ_WRITE
    """
    NONE = 0
    READ = 1
    WRITE = 2
    READ_WRITE = 3


class IOModel:
    """An IOModel is the base class for models and fields."""

    __slots__ = ('name', 'value')

    def __init__(self, name):
        self.name = name

    @property
    def empty(self):
        """

        Returns:
            A bool if model / field is empty.
        """
        raise NotImplementedError

    async def validate(self, fields):
        """Combines :class:`~tedious.mdl.model.IOModel.validate_not_empty` and :class:`~tedious.mdl.model.IOModel.validate_content`

        Args:
            fields: List of fields to be checked if they are empty.

        Raises:
            ValidationError if either a field of ``fields`` is empty of a fields content is invalid.
        """

        empty_fields = None
        invalid_fields = None
        try:
            await self.validate_not_empty(fields)
        except ValidationError as e:
            empty_fields = e.fields
        try:
            await self.validate_content()
        except ValidationError as e:
            invalid_fields = e.fields

        if empty_fields is not None and invalid_fields is not None:
            raise ValidationError(empty_fields + invalid_fields)
        elif empty_fields is not None:
            raise ValidationError(empty_fields)
        elif invalid_fields is not None:
            raise ValidationError(invalid_fields)

    async def validate_not_empty(self, fields):
        """Validates that content of IOModel is not None.

        Args:
            fields: Fields to check value for None

        Raises:
            ValidationError containing invalid fields.
        """

        raise NotImplementedError

    async def validate_content(self):
        """Validates field, but only if fields is not None

        Raises:
            ValidationError containing the invalid field / fields
        """

        raise NotImplementedError

    async def input(self, inp, permissions: typing.Dict = None, validate_fields=None):
        """ Reads input and sets fields accordingly.

        Args:
            inp: Value of dict of values to be set.
            permissions: dict containing :class:`~.Permissions` for each fields.
            validate_fields: List of fields to check if empty, list can be empty and only content will be checked.

        Returns:
            self
        """

        raise NotImplementedError

    async def output(self, fields=None, permissions: typing.Dict = None):
        """ Outputs either value or dict of values.

        Args:
            fields: List of key paths.
            permissions: dict containing :class:`~.Permissions` for each fields.

        Returns:
            Dict of values or single value.
        """

        raise NotImplementedError

    async def copy(self, other, overwrite=True):
        """ Copies value of other model or field.

        Args:
            other: Instance of same class.
            overwrite: If false, only None values will be overwritten, otherwise all.

        Returns:
            self
        """

        raise NotImplementedError

    def __getitem__(self, item):
        raise NotImplementedError

    def __setitem__(self, key, value):
        raise NotImplementedError


class _FieldsIterator:
    """Iterator to user for IOInterfaces fields. Returns field name.

    Args:
        fields: List of key paths to iterate.
        only: If None all fields and models will be returned, otherwise only instances of ``only``.
    """

    __slots__ = ('_fields', '_only', '_index')

    def __init__(self, fields: typing.List[IOModel], only=None):
        self._fields = fields
        self._only = only
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._index >= len(self._fields):
            # Stop iterating if index is too big
            raise StopIteration

        _next = self._fields[self._index]
        if self._only is not None:
            while not isinstance(_next, self._only):
                # iterates fields attribute until field of class 'only' has been found
                self._index += 1
                if self._index >= len(self._fields):
                    raise StopIteration
                _next = self._fields[self._index]
        self._index += 1
        return _next.name


class Model(typing.Mapping[str, IOModel], IOModel):
    """The Model class implements all methods of IOModel."""

    def __init__(self, name: str, fields: typing.List[IOModel]):
        IOModel.__init__(self, name)
        self._fields = fields
        self._key_to_index = {fields[i].name: i for i in range(len(self._fields))}

    def __getitem__(self, k):
        return self._fields[self._key_to_index[k]]

    def __setitem__(self, key, value):
        assert isinstance(self[key], Field), "{} is not a field.".format(key)
        self[key].value = value

    def __len__(self) -> int:
        return len(self._fields)

    def __iter__(self) -> Iterator:
        return _FieldsIterator(self._fields)

    def keys(self):
        """Returns all models and fields as key paths."""
        key_paths = []
        for field in self:
            if isinstance(self[field], typing.Mapping):
                key_paths += ['{}.{}'.format(self.name, _field) if self.name is not None else _field for _field in self[field].keys()]
            else:
                key_paths.append('{}.{}'.format(self.name, field) if self.name is not None else field)
        return key_paths

    @property
    def empty(self):
        """Recursively checks if fields are empty.

        Returns:
            True if all fields are empty, otherwise False.
        """

        empty = True
        for field in self:
            empty = self[field].empty
            if not empty:
                break
        return empty

    async def validate_not_empty(self, fields):
        """Recursively validates that each field in fields is not empty.

        Args:
            fields: List of key paths to validate.

        Raises:
            :class:`~tedious.mdl.model.ValidationError` if any field is empty.
        """

        assert fields is not None, "To validate {} {} please include fields".format(self.name, type(self))
        if isinstance(fields, list):
            fields = KeyPathsIter(fields)

        flawed_fields = []

        for key, _iter in fields:
            try:
                await self[key].validate_not_empty(_iter)
            except ValidationError as e:
                assert isinstance(e.fields, list), "Results from validations must return list not {}".format(type(e.fields))
                flawed_fields += ["{}.{}".format(self.name, field) if self.name is not None else field for field in e.fields]

        if len(flawed_fields) > 0:
            raise ValidationError(flawed_fields)

    async def validate_content(self):
        """Recursively validates each field.

        Raises:
            :class:`~tedious.mdl.model.ValidationError` if any field is invalid.
        """

        flawed_fields = []

        for field in self:
            try:
                await self[field].validate_content()
            except ValidationError as e:
                assert isinstance(e.fields, list), "Results from validations must return list not {}".format(type(e.fields))
                flawed_fields += ["{}.{}".format(self.name, field) if self.name is not None else field for field in e.fields]

        if len(flawed_fields) > 0:
            raise ValidationError(flawed_fields)

    async def input(self, inp: dict, permissions: typing.Dict = None, validate_fields=None):
        """Recursively reads inp. If permission is given, only reads in fields which have a permission of WRITE or READ_WRITE.

        Args:
            inp: Dict of values.
            permissions: dict containing :class:`~.Permissions` for each fields.
            validate_fields: If given, even if empty, :class:`~tedious.mdl.model.IOModel.validate` is chained to this method.

        Returns:
            self
        """

        for field in inp:

            _permissions = None

            if permissions is not None and field not in permissions:
                continue
            elif permissions is not None and field in permissions:
                if isinstance(permissions[field], Permissions) and permissions[field] != Permissions.WRITE and permissions[field] != Permissions.READ_WRITE:
                    continue
                elif isinstance(permissions[field], dict):
                    _permissions = permissions[field]

            if field not in self._key_to_index:
                raise ValueError("{} does not contain field {}.".format(type(self), field))

            await self[field].input(inp[field], permissions=_permissions)

        if validate_fields is not None:
            await self.validate(validate_fields)

        return self

    async def output(self, fields=None, permissions: typing.Dict = None):
        """Recursively builds output dict using KeyPathsIterators.

        Args:
            fields: List of key paths to output.
            permissions: dict containing :class:`~.Permissions` for each fields.

        Returns:
            Dict containing none null values.
        """

        assert fields is not None, "Please include either a list of key paths or a KeyPathsIter"

        # if fields is list it gets converted to a KeyPathsIter, if type is not supported a ValueError is raised
        if isinstance(fields, list):
            fields = KeyPathsIter(fields)
        elif not isinstance(fields, KeyPathsIter):
            raise ValueError("{} is unsupported.".format(type(fields)))

        if permissions is None:
            response = {key: await self[key].output(_iter) for key, _iter in fields}
        else:
            response = {}
            for key, _iter in fields:
                if key not in permissions:
                    continue
                elif isinstance(permissions[key], Permissions) and permissions[key] != Permissions.READ and permissions[key] != Permissions.READ_WRITE:
                    continue
                else:
                    _output = await self[key].output(_iter, permissions[key])
                    if _output is not None and (not isinstance(_output, dict) or len(_output) > 0):
                        response[key] = _output

        return response

    async def copy(self, other, overwrite=True):
        """Recursively copies other.

        Args:
            other: Instance of same class.
            overwrite: If False, only None fields will be overwritten.

        Returns:
            self
        """

        assert isinstance(other, type(self)), "{} cannot copy {}".format(type(self), type(other))

        for field in self:
            await self[field].copy(other[field], overwrite)

        return self


class Field(IOModel):
    """Fields are used for models to hold values."""

    def __init__(self, name, value=None):
        super().__init__(name)
        self.value = value

    @property
    def empty(self):
        """Returns True if value is not None"""

        return self.value is None

    async def validate_not_empty(self, fields):
        """Validates if self.value is None

        Args:
            fields: fields must always be None, since a field only contains a single value.

        Raises:
            ValidationError if self.value is None
        """

        assert fields is None, "A field does not contain any children. Fields {} are therefore invalid on {} {}".format(fields, self.name, type(self))
        if self.value is None:
            raise ValidationError([self.name], "{} is None".format(self.name))

    async def input(self, inp, permissions=None, validate_fields=None):
        """Reads in single value.

        Args:
            inp: Must be single value.
            permissions: Always None
            validate_fields: Always None
        """

        self.value = inp
        return self

    async def output(self, fields=None, permissions: typing.Dict = None):
        """Returns single value.

        Args:
            fields: Always None
            permissions: Always None
        """

        assert fields is None, "Fields can only return their single value, therefore given fields {} can not be used.".format(fields)
        return self.value

    async def copy(self, other, overwrite=True):
        """Copies value of other field if self.value is None or overwrite is true and the other field is not empty.

        Args:
            other: Instance of same field.
            overwrite: If true field will always be overwritten, otherwise only if field value is None.
        """

        assert isinstance(other, type(self)), "{} cannot copy {}".format(type(self), type(other))
        if (self.value is None or overwrite) and other.value is not None:
            self.value = other.value
        return self

    def __setitem__(self, key, value):
        raise UnsupportedError("Field {} can not __setitem__".format(self.name))

    def __getitem__(self, item):
        raise UnsupportedError("Can not get item from field {}.".format(self.name))
