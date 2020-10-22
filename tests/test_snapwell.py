import os
import unittest
from datetime import date
from os.path import abspath, join
from unittest.mock import MagicMock

import pytest
import yaml
from ecl.eclfile import EclFile

# utils
from snapwell import SnapConfig, findKeyword, findRestartStep, roundAwayFromEven

from .testcase import TestCase


def test_keyword_out_of_range():
    restart = MagicMock()
    restart.num_report_steps.return_value = 100
    with pytest.raises(ValueError, match="restart step out of range"):
        findKeyword("SWAT", restart, None, 100)


class SnapwellUtilTest(TestCase):
    def setUp(self):
        self._base = "testdata/snapwell"
        self._ecl_base = "testdata/eclipse"

    def assertAtMost(self, x, y):
        epsilon = 0.000001
        self.assertTrue(x <= y + epsilon, "%f <= %f failed" % (x, y))

    def assertBetween(self, low, x, high):
        self.assertAtMost(low, x)
        self.assertAtMost(x, high)

    def test_date(self):
        rfname = os.path.join(self.TEST_ROOT_PATH, "testdata/eclipse/SPE3CASE1.UNRST")
        rfile = EclFile(rfname)
        step = findRestartStep(rfile, date(1996, 1, 1))
        self.assertEqual(0, step)

        step = findRestartStep(rfile, date(2021, 1, 1))
        self.assertEqual(4, step)

        step = findRestartStep(rfile, date(2028, 1, 29))
        self.assertEqual(12, step)

        step = findRestartStep(rfile, date(2028, 6, 1))
        self.assertEqual(12, step)

        step = findRestartStep(rfile, date(2030, 1, 1))
        self.assertEqual(13, step)

    def test_rounding(self):
        x = 1556.0
        rx = roundAwayFromEven(x)
        self.assertBetween(0.1, (rx % 2.0), 1.9)
        self.assertAlmostEqual(x, rx, delta=0.1)

        x = 1557.0
        rx = roundAwayFromEven(x)
        self.assertAlmostEqual(x, rx)

        x = 1558.05
        rx = roundAwayFromEven(x)
        self.assertBetween(0.1, (rx % 2.0), 1.9)
        self.assertAlmostEqual(x, rx, delta=0.1)

        x = 1559.95
        rx = roundAwayFromEven(x)
        self.assertBetween(0.1, (rx % 2.0), 1.9)
        self.assertAlmostEqual(x, rx, delta=0.1)

        x = 1497.0
        for i in range(160):
            rx = roundAwayFromEven(x)
            self.assertAlmostEqual(x, rx, delta=0.1)
            x += 0.05


class SnapwellTest(TestCase):
    def setUp(self):
        self._base = join(self.TEST_ROOT_PATH, "testdata/snapwell")
        self._ecl_base = join(self.TEST_ROOT_PATH, "testdata/eclipse")

    def assertEqualPaths(self, p1, p2):
        """Unit test assert equal paths"""
        self.assertEqual(abspath(p1), abspath(p2))

    def test_ParseRegression(self):
        snap_path = join(self._base, "test.yaml")
        snap = None
        with open(snap_path) as config_file:
            config_dict = yaml.safe_load(config_file)
            snap = SnapConfig(**config_dict)

        snap.set_base_path(self._base)

        gridfile = join(self._ecl_base, "SPE3CASE1.EGRID")
        self.assertEqualPaths(gridfile, snap.grid_file)

        restartfile = join(self._ecl_base, "SPE3CASE1.UNRST")
        self.assertEqualPaths(restartfile, snap.restart_file)
        self.assertEqual(1, len(snap.wellpath_files))

        wellpath = snap.wellpath_files[0]
        self.assertEqualPaths(join(self._base, "well1.w"), wellpath.well_file)
        self.assertEqual(date(2025, 1, 1), wellpath.date)

        self.assertIsNotNone(snap.grid)
        self.assertIsNotNone(snap.restart)


if __name__ == "__main__":
    unittest.main()
