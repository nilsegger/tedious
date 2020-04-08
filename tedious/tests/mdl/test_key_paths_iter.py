from tedious.util import KeyPathsIter


def test_iterator():
    paths = ['address.street', 'address.plz', 'address.country.en', 'address.country.de']
    expected = {
        'address': {
            'street': None,
            'plz': None,
            'country': {
                'en': None,
                'de': None
            }
        }
    }
    actual = KeyPathsIter._convert_to_dict(paths)
    assert expected == actual, "{} != {}".format(expected, actual)

    for key, _iter in KeyPathsIter(paths):

        # First item must be KeyPathsIter since theres only the nested 'address'
        assert isinstance(_iter, KeyPathsIter)

        for _nested_key, __iter in _iter:

            if isinstance(__iter, KeyPathsIter):
                for _sub_nested_key, ___iter in __iter:
                    assert _sub_nested_key == 'en' or _sub_nested_key == 'de'
            else:
                assert _nested_key == 'street' or _nested_key == 'plz'


if __name__ == '__main__':
    test_iterator()
