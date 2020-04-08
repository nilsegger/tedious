# Testing

All tests should be compatible with **pytest**. To mark tests as async, mark them with `@pytest.mark.asyncio`.  
Tests should be named following the pattern `test_*()`.

**Running tests**
1. Install library  
    * Windows: `python setup.py -q sdist && pip install dist/tedious-1.0.tar.gz -q`
    * Linux: `python3 setup.py -q sdist && pip3 install dist/tedious-1.0.tar.gz -q`
2. Run pytest:
    * Windows: `python -m pytest tests/ -s`
    * Linux: `python3 -m pytest tests/ -s`