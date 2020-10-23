import datetime
from unittest.mock import MagicMock, create_autospec
from itertools import product

import pytest

from snapwell.snapecl import snap
from snapwell.wellpath import WellPath
import snapwell

from ecl import EclTypeEnum
from ecl.eclfile import Ecl3DKW, EclKW
from ecl.grid import EclGridGenerator


@pytest.fixture()
def homogeneous_grid(ni=3, nj=3, nk=3, x=1.0, y=1.0, z=1.0):
    """Generate an ni*nj*nk grid where each cell has size x,y,z.  Return grid."""
    grid = EclGridGenerator.createRectangular((ni, nj, nk), (x, y, z))
    keyword = EclKW("SWAT", grid.getNumActive(), EclTypeEnum.ECL_FLOAT_TYPE)
    kw3 = Ecl3DKW.castFromKW(keyword, grid)
    for i, j, k in product(
        range(grid.getNX()), range(grid.getNY()), range(grid.getNZ())
    ):
        kw3[i, j, k] = k / float(nk)
    yield grid, keyword, kw3


@pytest.fixture()
def well_path_mock():
    def side_effect(idx):
        return [(1.0, 1.0, 1.0), (2.0, 2.0, 2.0)][idx]

    well_path = create_autospec(WellPath)
    well_path.owc_offset = 0.5
    well_path.owc_definition = ("SWAT", 0.7)
    well_path.window_depth = 1
    well_path.headers = []
    well_path.depth_type = None
    well_path.__getitem__.side_effect = side_effect
    yield well_path


def test_snap_inside_grid(monkeypatch, well_path_mock, homogeneous_grid):
    grid, _, _ = homogeneous_grid
    eclkw_mock = MagicMock()
    eclkw_mock.__getitem__.return_value = 0.0
    monkeypatch.setattr(
        snapwell.snapecl, "findKeyword", MagicMock(return_value=eclkw_mock)
    )
    random_date = datetime.datetime(1998, 1, 1, 0, 0)
    snap(well_path_mock, grid, "EclFile", random_date, 0.5, keywords=["SWAT"])

    well_path_mock.add_column.assert_called_once_with("SWAT", [0.0, 0.0])


def test_snap_outside_grid(monkeypatch, well_path_mock, homogeneous_grid):
    grid, _, _ = homogeneous_grid
    eclkw_mock = MagicMock()
    eclkw_mock.__getitem__.return_value = 0.0
    monkeypatch.setattr(
        snapwell.snapecl, "findKeyword", MagicMock(return_value=eclkw_mock)
    )
    random_date = datetime.datetime(1998, 1, 1, 0, 0)

    def side_effect(idx):
        return [(4.0, 4.0, 4.0), (4.0, 4.0, 5.0)][idx]

    well_path_mock.__getitem__.side_effect = side_effect
    with pytest.raises(ValueError, match="Could not find the point"):
        snap(well_path_mock, grid, "EclFile", random_date, 0.5, keywords=["SWAT"])
