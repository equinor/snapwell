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

from __future__ import print_function  # so we can write print(..,end='')

import argparse
import sys
from os import makedirs, path
from time import time

from snapwell.snapconfig import SnapConfig
from snapwell import __version__ as VERSION, snap, tryFloat


def exit_with_usage(msg=None, exit_status=0):
    if msg:
        print(msg)
    print("usage:          snapwell conf.sc")
    print("                snapwell -h")
    print("                snapwell --help")
    print("                snapwell --version")
    print("")
    print("Visualization:")
    print("                snapviz conf.sc")
    exit(exit_status)


def get_conf_file(conf_file):
    if not path.exists(conf_file):
        exit_with_usage("No such file or directory: %s" % conf_file, 1)

    if not path.isfile(conf_file):
        exit_with_usage(
            "A Snapwell config file is needed.  Provide full path to config file."
        )

    if not conf_file[-3:] == ".sc":
        print(
            "Warning: It is highly recommended that a Snapwell config file has file extension .sc"
        )
    return conf_file


def get_snap_conf(conf_file):
    print("Parsing config file %s" % conf_file)
    try:
        return SnapConfig.parse(conf_file)
    except Exception as err:
        exit_with_usage(str(err), 1)


def load_grid_file(snap_conf):
    print("Loading grid %s" % snap_conf.gridFile())
    grid = None
    gridFile = snap_conf.gridFile()
    try:
        grid = snap_conf.getGrid()
    except Exception as err:
        print("Warning, supplied GRID file not loaded: %s" % err)
    if not grid:
        if not path.isfile(gridFile):
            exit_with_usage("Missing grid: No such file %s." % gridFile)
        else:
            exit_with_usage("Missing grid: Failed to read grid file %s." % gridFile)
    return grid


def load_restart_file(snap_conf):
    print("Loading restart %s" % snap_conf.restartFile())
    restart = None
    restartFile = snap_conf.restartFile()
    try:
        restart = snap_conf.getRestart()
    except Exception as err:
        print("Warning, supplied RESTART file not loaded: %s" % err)

    if not restart:
        if not path.isfile(restartFile):
            exit_with_usage("Missing restart: No such file %s." % restartFile)
        else:
            exit_with_usage(
                "Missing restart: Failed to read restart file %s." % restartFile
            )
    return restart


def load_init_file(snap_conf):
    init = None
    if snap_conf.initFile():
        print("Loading INIT %s" % snap_conf.initFile())
        try:
            init = snap_conf.getInit()
        except Exception as err:
            print("Warning, supplied INIT file not loaded: %s" % err)

    if not init:
        print("No INIT file, will not output PERM values")
    return init


def load_wellpaths(snap_conf):
    print("Loading %d wells" % (len(snap_conf)))

    wellpaths = []
    for i in range(len(snap_conf)):
        fname = snap_conf.filename(i)
        print(fname, end=" ... ")
        wp = snap_conf.getWellpath(i)
        print("(%d points, %d logs)" % (len(wp), len(wp.headers())), end=" ")
        wellpaths.append(wp)
        print("done")
    return wellpaths


def run_and_write(grid, restart, init, snap_conf, wp, wp_date, resinsight=False):
    try:
        # call to main algorithm
        snap(
            wp,
            grid,
            restart,
            init,
            wp_date,
            owc_offset=snap_conf.owcOffset(),
            keywords=snap_conf.logKeywords(),
            delta=snap_conf.deltaZ(),
            owc_definition=snap_conf.owcDefinition(),
        )
        # write wellpath to file
        rows = wp.write(overwrite=snap_conf.overwrite(), resinsight=resinsight)
        print("Wrote %d rows to %s.out" % (rows, wp.filename()))
        # done with this wellpath
    except ValueError as err:
        print("Error in well/grid/restart values: %s" % err)
    except IOError as err:
        print("Error while writing file: %s" % err)


def _parseOwcDefinition(od):
    od = od.strip()
    if not ":" in od:
        return None
    t = od.split(":")
    if len(t) != 2:
        return None
    odkw, odval = t[0], t[1]
    odval = tryFloat(odval, ret=None)
    if odval is None:
        return None
    if not odkw.isalpha():
        return None
    return odkw.upper(), odval


def main_loop(grid, restart, init, snap_conf, wellpaths, resinsight=False):
    num_snaps = len(wellpaths)
    print("delta_z    = %.3f" % snap_conf.deltaZ())
    print("owc_offset = %.3f" % snap_conf.owcOffset())
    owc_def = snap_conf.owcDefinition()
    print("owc_defini = %.3f (%s)" % (owc_def[1], owc_def[0]))
    print("output     = %s" % snap_conf.output())
    for i in range(len(wellpaths)):
        wp = wellpaths[i]
        wp_date = snap_conf.date(i)
        sep = "=" * 79
        print("\n\n%s" % sep)
        print("%d/%d \t Snapping %s" % (i + 1, num_snaps, wp.wellname()))
        start = time()
        run_and_write(
            grid, restart, init, snap_conf, wp, wp_date, resinsight=resinsight
        )
        stop = time()
        sec = round(stop - start, 2)
        print("Operation took %s seconds" % str(sec))


def main():
    try:
        from web_log import LogAsync

        LogAsync("snapwell", "launch")
    except:
        pass
    if len(sys.argv) == 1:
        exit_with_usage()
    elif len(sys.argv) == 2:
        if sys.argv[1] == "-v" or sys.argv[1] == "--version":
            print("%s %s" % ("snapwell", VERSION))
            exit(0)

    parser = argparse.ArgumentParser(
        description="Snapwell --- a wellpath optimization program."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output folder.  In this folder, all the new wellpath files are written on the specified format.",
    )
    parser.add_argument(
        "-z", "--owc_offset", type=float, help="OWC offset in meters, e.g. 0.5"
    )
    parser.add_argument(
        "-f", "--owc_definition", type=str, help="OWC definition, e.g. SWAT:0.7"
    )
    parser.add_argument(
        "-d", "--delta", type=float, help="Delta Z dogleg restriction, e.g. 0.0165"
    )
    parser.add_argument(
        "-w",
        "--overwrite",
        action="store_true",
        help="Overwrite output files will overwrite existing files",
    )
    parser.add_argument(
        "-r",
        "--resinsight",
        action="store_true",
        help="ResInsight compatible output format instead of RMS",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="show snapwell version (%s) and exit" % VERSION,
    )

    parser.add_argument("config", help="The Snapwell configuration file, e.g. snap.sc")

    args = parser.parse_args()

    fullstart = time()

    conf_file = get_conf_file(args.config)
    snap_conf = get_snap_conf(conf_file)

    if args.owc_offset:
        snap_conf.setOwcOffset(args.owc_offset)
    if args.output:
        outpath = path.abspath(args.output)
        if path.isfile(outpath):
            exit_with_usage(
                "Output path is an existing file.  Delete file, or choose a different output path."
            )
        if not path.exists(outpath):
            makedirs(outpath)
        snap_conf.setOutput(outpath)
    if args.overwrite:
        snap_conf.setOverwrite(args.overwrite)
    if args.owc_definition:
        d = _parseOwcDefinition(args.owc_definition)
        if d:
            snap_conf.setOwcDefinition(d)
        else:
            exit_with_usage("Incorrect usage.  Use as --owc_definition SWAT:0.07")
    if args.owc_offset:
        snap_conf.setOwcOffset(args.owc_offset)
    if args.delta:
        snap_conf.setDeltaZ(args.delta)

    grid = load_grid_file(snap_conf)
    restart = load_restart_file(snap_conf)
    init = load_init_file(snap_conf)
    wellpaths = load_wellpaths(snap_conf)
    confstop = time()
    conftime = round(confstop - fullstart, 2)
    print("\n\nConfiguration completed in %s sec.\n" % str(conftime))

    # This function loops through all wellpaths wp in wellpaths
    main_loop(grid, restart, init, snap_conf, wellpaths, resinsight=args.resinsight)

    fullstop = time()
    fullsec = round(fullstop - fullstart, 2)
    print("snapwell completed in %s seconds" % str(fullsec))


if __name__ == "__main__":
    main()
