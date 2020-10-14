import functools
from ecl.util.test import ExtendedTestCase
import os
import py_compile


class TestCase(ExtendedTestCase):
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    TEST_ROOT_PATH = os.path.dirname(__file__)

    def __init__(self, *args, **kwargs):
        super(TestCase, self).__init__(*args, **kwargs)
