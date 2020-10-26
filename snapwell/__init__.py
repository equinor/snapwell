#  This file is part of Snapwell.
#
#  Snapwell is free software: you can redistribute it and/or modify it under the
#  terms of the GNU General Public License as published by the Free Software
#  Foundation, either version 3 of the License, or (at your option) any later
#  version.
#
#  Snapwell is distributed in the hope that it will be useful, but WITHOUT ANY
#  WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
#  A PARTICULAR PURPOSE.
#
#  See the GNU General Public License at <http://www.gnu.org/licenses/gpl.html>
#  for more details.

"""The Snapwell module, a wellpath optimization module.

   This module provides functionality for reading and writing wellpaths in the
   RMS format, as well as optimizing the vertical position of these wellpaths
   provided an Eclipse restart file (UNRST) and a grid file ((E)GRID).

   If one wants to use the snapping feature, a snapconfig file is needed.  This
   file specifies the location of a GRID file, a RESTART file, optionally an
   INIT file, if the PERMX keyword is wanted.  Then follows the wellpath files
   and the date (in the UNRST) wanted.

   See README.md for more information and usage information.

   There is a binary in /project/res/bin/snapwell for reading the config file
   and applying the snapping algorithm.

   This module exposes the WellPath class, the SnapConfig class as well as the
   snap algorithm (in snapecl).


"""
from pkg_resources import DistributionNotFound, get_distribution

__author__ = "PG Drange, K Flikka, and KW Kongsvik"
__email__ = "pgdr@statoil.com"
__copyright__ = "Copyright 2016, Statoil ASA"
__license__ = "GNU General Public License version 3"
__maintainer__ = "GBS IT SI SIB"
__status__ = "Prototype"
__credits__ = ["PG Drange", "K Flikka", "KW Kongsvik"]

from .snapconfig import SnapConfig
from .snapecl import findKeyword, findRestartStep, in_snap_mode, roundAwayFromEven, snap
from .wellpath import WellPath, finiteFloat

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    __version__ = "0.0.0"
