
import logging

import pytest
import flask


def pytest_runtest_setup(item):
    """Global setup for tests in this directory."""
    logger = logging.getLogger()
    logger.setLevel(logging.NOTSET)


def pytest_runtest_teardown(item, nextitem):
    """Global teardown for tests in this directory."""
    logger = logging.getLogger()
    logging.shutdown()
    del logger.handlers[:]
    del logging._handlerList[:]
