from os.path import join, abspath
import unittest
from datetime import datetime

from .testcase import TestCase
from snapwell import WellPath, snapecl, Inf

from ecl.eclfile import EclKW, Ecl3DKW
from ecl import EclTypeEnum
from ecl.grid import EclGridGenerator


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
            owc, tvd = snapecl.findOwc(g, kw, 5, 5, 1, thresh=t)
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
            owc, tvd = snapecl.findOwc(g, kw, 5, 5, 1, thresh=t)
            self.assertAlmostEqual(20 * t + 1, owc, delta=self.epsilon)


if __name__ == "__main__":
    unittest.main()
