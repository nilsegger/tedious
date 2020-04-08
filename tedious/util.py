import uuid
import typing


def create_uuid():
    return uuid.uuid4()


class KeyPathsIter:
    __slots__ = ('_dict_paths', '_keys', '_index')

    @staticmethod
    def _convert_to_dict(key_paths: typing.List[str]) -> dict:
        """
            Converts key paths to dict, example ['address.street', 'address.plz', 'helloworld'] => {'address': {'street': None, 'plz': None},
                                                                                                    'helloworld': None}
        :param key_paths:
        :return:
        """

        duplicate_msg = "Duplicate key path '{}'."
        invalid_depths_msg = "Do not mix key paths with different depths, example: ['address.street', 'address'] should either be  ['address.street'] or  ['address.street', 'address.plz']"

        response = {}

        for key_path in key_paths:
            steps = key_path.split('.')

            if len(steps) == 1:
                # key_path does not contain any '.'
                assert not (key_path in response and response[key_path] is None), duplicate_msg.format(key_path)
                assert not (key_path in response and isinstance(response[key_path], dict)), invalid_depths_msg
                response[key_path] = None
                continue

            path = response
            for step in steps[:-1]:
                if step not in path:
                    path[step] = {}
                path = path[step]

            assert not (steps[-1] in path and path[steps[-1]] is None), duplicate_msg.format(key_path)
            assert not (steps[-1] in path and isinstance(path[steps[-1]],
                                                         dict)), invalid_depths_msg

            path[steps[-1]] = None
        return response

    def __init__(self, key_paths: typing.List[str] = None, dict_paths=None):
        """

        :param key_paths: List of key paths: example: ['address.street', 'address.plz]
        :param dict_paths: Key paths already formed as dict path

        This class is meant to be used recursively.
        """

        assert (key_paths is None or dict_paths is None) and (
                key_paths is not None or dict_paths is not None), "Please supply either key or dict paths."
        assert key_paths is None or isinstance(key_paths, list), "Please make sure that keypaths is a list not {}.".format(type(key_paths))

        self._dict_paths = KeyPathsIter._convert_to_dict(key_paths) if dict_paths is None else dict_paths
        self._keys = [key for key in self._dict_paths]
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._index >= len(self._keys):
            raise StopIteration

        key = self._keys[self._index]
        self._index += 1
        if self._dict_paths[key] is None:
            return key, None
        else:
            return key, KeyPathsIter(dict_paths=self._dict_paths[key])
