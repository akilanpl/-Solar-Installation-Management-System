"""Run the same backend suite in reverse collection order in a fresh process."""

import sys

import pytest


class ReverseCollection:
    @staticmethod
    def pytest_collection_modifyitems(items):
        items.reverse()


if __name__ == "__main__":
    raise SystemExit(pytest.main(sys.argv[1:], plugins=[ReverseCollection()]))
