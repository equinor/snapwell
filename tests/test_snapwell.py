import os
import unittest
from datetime import datetime

from .testcase import TestCase
from snapwell import SnapConfig

# utils
from snapwell import findRestartStep, roundAwayFromEven
from snapwell import parse_date

from ecl.eclfile import EclFile
from os.path import join, abspath


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
        step = findRestartStep(rfile, parse_date("1996-01-01"))
        self.assertEqual(0, step)

        step = findRestartStep(rfile, parse_date("2021-01"))
        self.assertEqual(4, step)

        step = findRestartStep(rfile, parse_date("2028-01-29"))
        self.assertEqual(12, step)

        step = findRestartStep(rfile, parse_date("2028-06"))
        self.assertEqual(12, step)

        step = findRestartStep(rfile, parse_date("2030"))
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

    def test_BasicConf(self):
        p = SnapConfig("", "")
        p.setDeltaZ(1.1)
        self.assertEqual(1.1, p.deltaZ())
        p.setOwcOffset(3.3)
        self.assertEqual(3.3, p.owcOffset())

        p.setOverwrite(True)
        self.assertTrue(p.overwrite())
        p.setOverwrite(False)
        self.assertFalse(p.overwrite())

        p.setOutput("snapout")
        self.assertEqual("snapout", p.output())

    def test_ParseRegression(self):
        snap_path = join(self._base, "test.sc")
        snap = SnapConfig.parse(abspath(snap_path))

        gridfile = join(self._ecl_base, "SPE3CASE1.EGRID")
        self.assertEqualPaths(gridfile, snap.gridFile())

        restartfile = join(self._ecl_base, "SPE3CASE1.UNRST")
        self.assertEqualPaths(restartfile, snap.restartFile())
        self.assertEqual(1, len(snap))

        wellpath = snap[0]
        self.assertEqualPaths(join(self._base, "well1.w"), wellpath[0])
        self.assertEqual(datetime(2025, 1, 1), wellpath[1])

        self.assertIsNotNone(snap.getGrid())
        self.assertIsNotNone(snap.getRestart())


if __name__ == "__main__":
    unittest.main()
