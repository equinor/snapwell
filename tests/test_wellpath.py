import unittest
from datetime import datetime
from io import StringIO
from os.path import abspath, dirname, join

import numpy as np
import pytest
from snapwell import Inf, WellPath

from .testcase import TestCase


def test_well_path_file_extension_warning(caplog):
    WellPath(filename="config.sc")
    assert any("Potentially a Snapwell config" in r.message for r in caplog.records)


def test_well_path_wrong_set_rkb_tuple():
    wp = WellPath(filename="well.w")
    with pytest.raises(ValueError, match="Need x,y,z to be floats"):
        wp.setRkb(("r", "k", "b"))


def test_well_path_duplicate_column():
    wp = WellPath(filename="well.w")
    with pytest.raises(KeyError, match="Key x exists in table."):
        wp.addColumn("x")


def test_well_path_wrong_update_rkb_tuple():
    wp = WellPath(filename="well.w")

    wp.addRaw([1, 1, 1])
    wp.addColumn("MD", [np.nan])
    assert not wp.updateRkb()


def test_well_path_update():
    wp = WellPath(filename="well.w")
    wp.addRaw([1, 1, 1])
    wp.update(2, 0, 2)
    assert wp["z"] == [2]
    with pytest.raises(IndexError, match="index out of range"):
        wp.update(4, 0, 0)


def test_parse_wrong_num_columns():
    with pytest.raises(ValueError, match="<num_logs>"):
        WellPath.parse(StringIO("1.0.0\nA - B\nname 0 0 0\nnumber_of_columns\n"))


def test_write_unspecified_file():
    wp = WellPath(filename=None)
    with pytest.raises(ValueError, match="filename is unspecified"):
        wp.write()


test_data_path = join(dirname(__file__), "testdata", "snapwell")


@pytest.fixture
def well_path():
    return WellPath.parse(join(test_data_path, "well.w"))


def test_write_as_resinsight(snapshot, well_path):
    out = StringIO()
    well_path.write_to_stream(out, resinsight=True)
    snapshot.assert_match(out.getvalue())


def test_well_path_str(well_path):
    assert str(well_path) == "TEST_WELL"


def test_well_path_different_columns_not_eq():
    wp1 = WellPath()
    wp2 = WellPath()
    wp1.addColumn("MP")
    wp2.addColumn("OMG")

    assert wp1 != wp2


def test_well_path_different_rows_not_eq():
    wp1 = WellPath()
    wp2 = WellPath()
    wp1.addRaw([1, 1, 1])
    wp2.addRaw([2, 2, 2])

    assert wp1 != wp2


def test_well_path_not_eq_str():
    assert WellPath() != ""


class WellpathTest(TestCase):
    def setUp(self):
        self._base = join(self.TEST_ROOT_PATH, "testdata/snapwell")

    def test_WellpathParse(self):
        fpath = join(self._base, "well.w")
        apath = abspath(fpath)
        wp = WellPath.parse(apath)
        self.assertEqual("4.2", wp.version())
        self.assertEqual(122, len(wp))
        self.assertEqual("TEST_WELL", wp.wellname())
        self.assertEqual("A - B", wp.welltype())
        self.assertEqual(apath, wp.filename())
        r5 = [1067.0, 144.0, 0.0, 188.0, 94.0, 359.0]
        self.assertEqual(r5, wp[5])

        cols = ["x", "y", "z", "MD", "Incl", "Az"]
        self.assertEqual(cols, wp.headers())
        self.assertEqual((1068.0, 0.0, 0.0), wp.rkb())

    def test_WellpathEquality(self):
        wp1 = WellPath()
        wp2 = WellPath()
        self.assertEqual(wp1, wp2)
        wp1.addRaw((2, 4, 6))
        self.assertNotEqual(wp1, wp2)
        wp2.addColumn("c")
        self.assertNotEqual(wp1, wp2)
        wp2.addRaw((2, 4, 6, 8))
        self.assertNotEqual(wp1, wp2)
        wp1.addColumn("c", [8])
        self.assertEqual(wp1, wp2)

        fpath = join(self._base, "well.w")
        apath = abspath(fpath)
        wp1 = WellPath.parse(apath)
        wp2 = WellPath.parse(apath)
        self.assertEqual(wp1, wp2)

    def test_WellpathManipulation(self):
        wp = WellPath()
        ver = "1.1"
        typ = "TEST_typ"
        nam = "my_NAM"
        wp.setVersion(ver)
        wp.setWelltype(typ)
        wp.setWellname(nam)

        t_rkb = (1.0, 2.0, 3.0)
        wp.setRkb((1.0, 2.0, "3.0"))
        self.assertEqual(t_rkb, wp.rkb())
        wp.setRkb((1.0, 2.0, "3.0"))
        self.assertEqual(t_rkb, wp.rkb())
        with self.assertRaises(IndexError):
            wp.setRkb((1.0, 2.0))

        self.assertEqual(ver, wp.version())
        self.assertEqual(typ, wp.welltype())
        self.assertEqual(nam, wp.wellname())

        self.assertEqual(["x", "y", "z"], wp.headers())

        self.assertEqual(len(wp), 0)
        wp.addRaw((13, 17, 19))
        self.assertEqual(len(wp), 1)
        with self.assertRaises(IndexError):
            wp.addColumn("d", [])  # needs data of size 1

        # adding column 'd'
        wp.addColumn("d", [23])
        self.assertEqual(["x", "y", "z", "d"], wp.headers())
        with self.assertRaises(IndexError):
            wp.addRaw((50, 51, 52))
        wp.addRaw((50, 51, 52, 53))
        self.assertEqual(len(wp), 2)
        data = [d for d in wp.rows()]
        self.assertEqual([[13, 17, 19, 23], [50, 51, 52, 53]], data)

        # update cell
        with self.assertRaises(IndexError):
            wp.update(-1, 3, 1729)
        with self.assertRaises(IndexError):
            wp.update(0, 4, 1729)
        with self.assertRaises(KeyError):
            wp.update("a", 1, 1729)
        data = [d for d in wp.rows()]
        self.assertEqual([[13, 17, 19, 23], [50, 51, 52, 53]], data)
        wp.update("d", 1, 1729)
        data = [d for d in wp.rows()]
        self.assertEqual([[13, 17, 19, 23], [50, 51, 52, 1729]], data)

        # removal of column
        with self.assertRaises(ValueError):
            wp.removeColumn("x")
        wp.removeColumn("d")
        self.assertEqual(["x", "y", "z"], wp.headers())
        with self.assertRaises(IndexError):
            wp.addRaw((90, 91, 92, 93))
        wp.addRaw((90, 91, 92))
        self.assertEqual(len(wp), 3)
        data = [d for d in wp.rows()]
        self.assertEqual([[13, 17, 19], [50, 51, 52], [90, 91, 92]], data)
        self.assertEqual(wp[1], [50, 51, 52])

        # setting info
        wp[2] = [80, 81, 82]
        data = [d for d in wp.rows()]
        self.assertEqual([[13, 17, 19], [50, 51, 52], [80, 81, 82]], data)

    def test_WellpathDepth(self):
        wp = WellPath()
        self.assertIsNone(wp.depthType())
        self.assertEqual(-Inf, wp.windowDepth())
        wp.setDepthType("MD")
        self.assertEqual("MD", wp.depthType())
        self.assertEqual(-Inf, wp.windowDepth())
        wp.setWindowDepth(250)
        self.assertEqual(250.0, wp.windowDepth())
        with self.assertRaises(ValueError):
            wp.setDepthType("X")
        with self.assertRaises(ValueError):
            wp.setDepthType(4)
        self.assertEqual(250.0, wp.windowDepth())
        wp.setDepthType(None)
        self.assertIsNone(wp.depthType())
        self.assertEqual(-Inf, wp.windowDepth())

    def test_WellpathRkb(self):
        wp = WellPath()
        self.assertFalse(wp.updateRkb())
        wp.addColumn("MD")
        x1, y1, z1, md1 = 530609.50, 6749152.00, 1563.00, 1602.39
        x2, y2, z2, md2 = 530608.91, 6749150.04, 1565.00, 1632.39
        wp.addRaw((x1, y1, z1, md1))
        rkb_expect = (x1, y1, md1 - z1)
        rkb_actual = wp.rkb()
        self.assertAlmostEqualList(rkb_expect, rkb_actual)
        self.assertTrue(wp.updateRkb())
        rkb_actual = wp.rkb()
        self.assertAlmostEqualList(rkb_expect, rkb_actual)
        wp.addRaw((x2, y2, z2, md2))
        rkb_actual = wp.rkb()
        self.assertAlmostEqualList(rkb_expect, rkb_actual)

        # update e.g. y1
        y1 = 6749052.00
        wp[0] = (x1, y1, z1, md1)
        rkb_expect = (x1, y1, md1 - z1)
        rkb_actual = wp.rkb()
        self.assertEqual(rkb_expect, rkb_actual)

        # provided data wanted
        fpath = join(self._base, "rkb.w")
        apath = abspath(fpath)
        wp = WellPath.parse(apath)
        # RKB should be 1602.39-1563.00=39.39.
        self.assertAlmostEqualList(wp.rkb(), (530609.5, 6749152.0, 39.39))


if __name__ == "__main__":
    unittest.main()
