import unittest.mock

import pytest
from ecl import EclTypeEnum
from ecl.eclfile import Ecl3DKW, EclKW
from ecl.grid import EclGridGenerator

from snapwell import WellPath, snapecl

from .testcase import TestCase


def test_interpolate_from_zero_raises():
    with pytest.raises(IndexError, match="interpolate down"):
        snapecl.interpolate(None, 0, None, None)


def test_no_threshold_returns_none():
    assert snapecl.first_swat_below_treshold([(0, 0, 0, 0, 1)] * 100) is None


def test_no_active_above_z_returns_none():
    grid = unittest.mock.MagicMock()
    grid.get_xyz.return_value = (1, 1, 1)
    assert snapecl.find_center_z(grid, [[1] * 5] * 100, 0.0) is None


def test_no_active_logs_warning(caplog):
    grid = unittest.mock.MagicMock()
    grid.get_xyz.return_value = (1, 1, 1)
    grid.find_cell.return_value = (0, 0, 0)
    grid.get_active_index.return_value = -1
    snapecl.find_owc(grid, [0], 0, 0, 0)
    assert any("No active cell for" in r.message for r in caplog.records)


def test_no_treshold_logs_warning(caplog):
    grid = unittest.mock.MagicMock()
    grid.get_xyz.return_value = (1, 1, 1)
    grid.find_cell.return_value = (0, 0, 0)
    grid.get_active_index.return_value = 1
    snapecl.find_owc(grid, [1, 1], 0, 0, 0)
    assert any("No active cell has swat below" in r.message for r in caplog.records)


def test_no_cell_above_logs_warning(caplog):
    grid = unittest.mock.MagicMock()
    grid.get_xyz.return_value = (1, 1, 1)
    grid.find_cell.return_value = (0, 0, 0)
    grid.get_active_index.return_value = 1
    owc, tvd = snapecl.find_owc(grid, [1, 0.7], 0, 0, 0)
    assert any("Depth is above active" in r.message for r in caplog.records)
    assert owc == 1
    assert tvd == 1


def test_enter_snap_mode_no_depth_error():
    wp = WellPath(wellname="my well", filename="test.w")
    wp.depth_type = "MD"
    with pytest.raises(ValueError):
        snapecl.in_snap_mode(False, wp, 0)


class SnapAlgorithmTest(TestCase):
    def setUp(self):
        self.epsilon = 0.0001
        self.dataset = (0.1, 0.271828, 0.333, 0.4, 0.55, 0.65, 0.7, 0.73, 0.86, 0.9)

    def generateUniformGridAndSwat(self, ni=10, nj=10, nk=10, x=1.0, y=1.0, z=1.0):
        """Generate an ni*nj*nk grid where each cell has size x,y,z.  Return grid."""
        g = EclGridGenerator.createRectangular((ni, nj, nk), (x, y, z))
        kw = EclKW("SWAT", g.getNumActive(), EclTypeEnum.ECL_FLOAT_TYPE)
        kw3 = Ecl3DKW.castFromKW(kw, g)
        for i in range(g.getNX()):
            for j in range(g.getNY()):
                for k in range(g.getNZ()):
                    kw3[i, j, k] = k / float(nk)
        return g, kw, kw3

    def test_findOwcAlgorithm(self):
        g, kw, kw3 = self.generateUniformGridAndSwat()

        for idx in range(1, 10):
            # idxth layer from top
            self.assertAlmostEqual(idx / 10.0, kw3[5, 5, idx], delta=self.epsilon)

        # in this grid, the cell centers are at half-meters, so the 3rd cell
        # center (idx k=2) from the top is 2.5m from the top.  Since SWAT
        # values are given at cell centers, the SWAT values and their depths
        # (findOwc return value) differ with 0.5m.  Hence OWC=0.30 at 3.5m

        for t in self.dataset:
            owc, _ = snapecl.find_owc(g, kw, 5, 5, 1, threshold=t)
            self.assertAlmostEqual((t * 10) + 0.5, owc, delta=self.epsilon)

    def test_findOwcAlgorithmHighCell(self):
        g, kw, kw3 = self.generateUniformGridAndSwat(z=2.0)  # 2m high Troll

        for idx in range(1, 10):
            # idxth layer from top
            self.assertAlmostEqual(idx / 10.0, kw3[5, 5, idx], delta=self.epsilon)

        # in this grid, the cell centers are at even integer meters, so the 3rd
        # cell center (idx k=2) from the top is 4m from the top.  Since SWAT
        # values are given at cell centers, the SWAT values and their depths
        # (findOwc return value) differ with m.  Hence OWC=20xthresh+1m?

        for t in self.dataset:
            owc, _ = snapecl.find_owc(g, kw, 5, 5, 1, threshold=t)
            self.assertAlmostEqual(20 * t + 1, owc, delta=self.epsilon)


if __name__ == "__main__":
    unittest.main()
