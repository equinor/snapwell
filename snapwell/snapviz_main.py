#  Copyright (C) 2016  Statoil ASA, Norway.
#
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

import sys

import matplotlib as mpl
import matplotlib.pyplot as plt
from snapwell import SnapConfig, WellPath
from snapwell import __version__ as VERSION
from mpl_toolkits.mplot3d import Axes3D


# here begins example output
def printExamples():
    print(
        """
Example minimal Wellpath file well.w:
0.1
DISPOSAL - DRILLED
NORNE-1  462651.97 7325861.57     2451.24
0
462440.00          7325660.00     2490.00
462300.00          7325330.00     2510.00
462160.00          7324930.00     2540.00
Example minimal SnapConfig file norne.sc:
GRID       NORNE_ATW2013.EGRID
RESTART    NORNE_ATW2013.UNRST
INIT       NORNE_ATW2013.INIT
WELLPATH norne-well-B-2H.w            1998
WELLPATH norne-well-1.w               2001
"""
    )


# end of example output


def plotWellbore(x, y, z, label=""):
    mpl.rcParams["legend.fontsize"] = 10
    prefix = label[:9]
    fig = plt.figure(prefix)
    ax = fig.gca(projection="3d")
    ax.plot(x, y, z, label=label)
    ax.legend()


def _verifyInput(args):
    if len(args) < 2:
        print("Usage: snapviz well_1.w  ... well_n.w")
        print("       snapviz conf_1.sc ... conf_n.sc")
        print("       snapviz conf_1.sc ... conf_n.sc well_1.w ... well_m.w")
        print("")
        print(
            "Use    snapviz --example     to see minimal examples for paths and configs"
        )
        print("       snapviz --version     to see current version")
        print("")
        print("Note that a SnapConfig file must have file extension .sc")
        exit(0)


def readConfig(fname):
    """Reads a SnapConfig and returns list of Wellpath file paths"""
    fnames = []
    print("Reading snapconf %s" % fname)
    sc = SnapConfig.parse(fname)
    for wp in sc:
        fnames.append(wp[0])
    return fnames


def parseWellpaths(fnames):
    wps = []
    for fname in fnames:
        print("Reading wellpath %s" % fname)
        try:
            wp = WellPath.parse(fname)
            wps.append(wp)
        except IOError as err:
            print("Warning: Could not parse WellPath file %s: %s" % (fname, err))
    return wps


def parseArguments(args):
    """With args a list of filenames, returns the filenames verbatime, or, if a
    filename has the .sc extension, we read and parse that SnapConfig and
    append all the file paths to its wellpaths.
    """
    fnames = []
    for i in range(1, len(args)):
        fname = args[i]

        if fname[-3:] == ".sc":
            fnames += readConfig(fname)
        else:
            fnames.append(fname)

    return fnames


def main():
    _verifyInput(sys.argv)

    # check if user wants example files
    if sys.argv[1].lower() == "--example":
        printExamples()
        exit(0)
    if sys.argv[1].lower() == "--version":
        print("%s %s" % ("snapviz", VERSION))
        print("%s is part of the %s project." % ("snapviz", "snapwell"))
        exit(0)

    fnames = parseArguments(sys.argv)
    wps = parseWellpaths(fnames)

    for wp in wps:
        x, y, z = [], [], []
        for p in wp.rows():
            x.append(p[0])
            y.append(p[1])
            z.append(-p[2])  # z coordinate

        plotWellbore(x, y, z, wp.wellname())
    plt.show()


if __name__ == "__main__":
    main()
