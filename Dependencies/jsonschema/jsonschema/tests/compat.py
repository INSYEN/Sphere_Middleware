import sys

if sys.version_info[:2] < (2, 7):  # pragma: no cover
    pass
else:
    pass

try:
    from unittest import mock
except ImportError:
    import mock


# flake8: noqa
