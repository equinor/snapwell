import pytest
from datetime import datetime
from os.path import join, abspath
import unittest

from .testcase import TestCase
from snapwell import WellPath, SnapConfig, Inf


class SnapConfigTest(TestCase):
    def setUp(self):
        self._base = join(self.TEST_ROOT_PATH, "testdata/snapwell")
        self._ecl_base = join(self.TEST_ROOT_PATH, "testdata/eclipse")

    def assertEqualPaths(self, p1, p2):
        """Unit test assert equal paths"""
        self.assertEqual(abspath(p1), abspath(p2))

    def test_FileNotFound(self):
        snap = SnapConfig.parse(join(self._base, "nosuchwell.sc"))
        wp_f = snap.filename(0)
        with self.assertRaises(IOError):
            WellPath.parse(wp_f)

    def test_ParseMissingGridOrRestart(self):
        with self.assertRaises(ValueError):
            SnapConfig.parse(join(self._base, "test-missing-grid.sc"))
        with self.assertRaises(ValueError):
            SnapConfig.parse(join(self._base, "test-missing-restart.sc"))

    def test_ParseConf(self):
        snap = SnapConfig.parse(join(self._base, "littered.sc"))
        self.assertIsNone(snap.getInit())

        snapinit = SnapConfig.parse(join(self._base, "littered-w-init.sc"))
        self.assertIsNotNone(snapinit.getInit())
        self.assertEqualPaths(
            join(self._ecl_base, "SPE3CASE1.INIT"), snapinit.initFile()
        )

        gridpath = join(self._base, "grid.EGRID")
        self.assertEqualPaths(gridpath, snap.gridFile())

        restartpath = join(self._base, "a_restart_file.UNRST")
        self.assertEqualPaths(restartpath, snap.restartFile())

        self.assertEqual(2, len(snap))
        wellpath = join(self._base, "well.w")
        self.assertEqualPaths(wellpath, snap.filename(0))
        self.assertEqual(datetime(2022, 1, 1), snap.date(0))
        self.assertEqual(datetime(2019, 5, 1), snap.date(1))

    @pytest.mark.xfail(reason="Does not pass, need to figure out why")
    def test_ParseLOGS(self):
        # Test default values
        snap = SnapConfig.parse(join(self._base, "test-full.sc"))
        self.assertEqual(len(snap.logKeywords()), 5)
        _logKeywords = ("LENGTH", "TVD_DIFF", "OLD_TVD", "OWC", "PERMX")

        for i in range(len(_logKeywords)):
            self.assertEquals(
                _logKeywords[i],
                snap.logKeywords()[i],
                "Expected LOG keyword: %s, got: %s"
                % (_logKeywords[i], snap.logKeywords()[i]),
            )

    def test_addKeyWord(self):
        log_kw = "LENGTH"
        snap = SnapConfig("", "")
        self.assertFalse(snap.logKeywords())
        snap.addLogKeyword(log_kw)
        self.assertTrue(log_kw in snap.logKeywords())

    @pytest.mark.xfail(reason="Does not pass, need to figure out why")
    def test_ParseConfFull(self):
        # Test default values
        snap_def = SnapConfig.parse(join(self._base, "test.sc"))
        self.assertAlmostEqual(0.5, snap_def.owcOffset())
        self.assertAlmostEqual(Inf, snap_def.deltaZ())  # Infinite delta z allowed

        grid_fname = join(self._ecl_base, "SPE3CASE1.EGRID")
        self.assertEqualPaths(grid_fname, snap_def.gridFile())

        rest_fname = join(self._ecl_base, "SPE3CASE1.UNRST")
        self.assertEqualPaths(rest_fname, snap_def.restartFile())

        well1 = join(self._base, "well1.w")
        self.assertEqualPaths(well1, snap_def.filename(0))
        self.assertEqual(datetime(2025, 1, 1), snap_def.date(0))
        self.assertIsNone(snap_def.getInit())
        self.assertEqual(".", snap_def.output())
        self.assertFalse(snap_def.overwrite())
        with self.assertRaises(IndexError):
            snap_def.filename(1)
        with self.assertRaises(IndexError):
            snap_def.date(1)

        # Test parsing of all possible values
        snap = SnapConfig.parse(join(self._base, "test-full.sc"))
        self.assertAlmostEqual(0.88, snap.owcOffset())
        self.assertAlmostEqual(0.55, snap.deltaZ())

        self.assertEqualPaths(grid_fname, snap.gridFile())
        self.assertEqualPaths(rest_fname, snap.restartFile())

        init_fname = join(self._ecl_base, "SPE3CASE1.INIT")
        self.assertEqualPaths(init_fname, snap.initFile())

        well = join(self._base, "well.w")
        self.assertEqualPaths(well, snap.filename(0))
        # self.assertEqual(datetime(2025,03,31), snap.date(0))
        self.assertEqualPaths(well1, snap.filename(1))
        # self.assertEqual(datetime(2022,12,03), snap.date(1))
        with self.assertRaises(IndexError):
            snap_def.filename(2)
        with self.assertRaises(IndexError):
            snap_def.date(2)

        self.assertTrue(snap.overwrite())
        self.assertEqualPaths(self._ecl_base, snap.output())

    @pytest.mark.xfail(reason="Does not pass, need to figure out why")
    def test_ParseSettings(self):
        snap_path = join(self._base, "test-full.sc")
        snap = SnapConfig.parse(abspath(snap_path))
        well_fnames = ["well.w"] + ["well%d.w" % i for i in range(1, 8)]
        self.assertEqual(len(well_fnames), len(snap))
        depthtypes = (
            None,
            "TVD",
            "MD",
            "MD",
            "MD",
            None,
            "MD",
            "MD",
        )  # see test-full.sc
        depths = (-Inf, 2000.00, 158.20, 1680.00, 1680.00, -Inf, 1884, 4000)
        for i in range(len(snap)):
            self.assertEqual(depths[i], snap.windowDepth(i))
            self.assertEqual(depthtypes[i], snap.depthType(i))

        definition = (None, None, None, None, 0.71828, 0.1828, 0.828, 0.0)
        for i in range(len(snap)):
            self.assertEqual(definition[i], snap.igetOwcDefinition(i))

        offset = (None, None, None, None, None, 0.5115, 0.115, None)
        for i in range(len(snap)):
            self.assertEqual(offset[i], snap.igetOwcOffset(i))

        wp = snap.getWellpath(6)
        # WELLPATH well6.w 2025-12-03 OWC_OFFSET 0.115 OWC_DEFINITION 0.828 MD 1884
        self.assertEqual(wp.owcDefinition(), 0.828)
        self.assertEqual(wp.owcOffset(), 0.115)
        self.assertEqual(wp.depthType(), "MD")
        self.assertEqual(wp.windowDepth(), 1884)

    @pytest.mark.xfail(reason="Does not pass, need to figure out why")
    def test_OwcDefinition(self):
        # test-full has OWC_DEFINITION SGAS 0.31415
        snap_path = join(self._base, "test-full.sc")
        snap = SnapConfig.parse(abspath(snap_path))
        self.assertEqual(2, len(snap.owcDefinition()))
        self.assertEqual("SGAS", snap.owcDefinition()[0])
        self.assertAlmostEqual(0.31415, snap.owcDefinition()[1])

        snap.setOwcDefinition(("SWAT", 0.57721))
        self.assertEqual("SWAT", snap.owcDefinition()[0])
        self.assertAlmostEqual(0.57721, snap.owcDefinition()[1])


if __name__ == "__main__":
    unittest.main()
