# Contributing

Pull requests are welcome.

After adding tests in `tests` for a new feature or a bug fix, please run the test suite.
To do so, the only additional dependencies (beyond those needed for the package itself) can be
installed with:

```{bash}
pip install -r requirements/requirements-dev.txt
```

Once those are installed, the tests can be run with `pytest`. Alternatively, `python setup.py test` can be used.
