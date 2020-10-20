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


import argparse
import logging
import sys
import warnings
from os import makedirs, path
from time import time

from snapwell import __version__ as VERSION
from snapwell import snap, tryFloat
from snapwell.snapconfig import SnapConfig


class DuplicateFilter(logging.Filter):
    def filter(self, record):
        # add other fields if you need more granular comparison, depends on your app
        current_log = (record.module, record.levelno, record.msg)
        log_count = getattr(self, "log_count", 0)
        if current_log != getattr(self, "last_log", None):
            if log_count > 1:
                print(f"Suppressed {self.log_count} similar messages")
            self.last_log = current_log
            self.log_count = 1
            return True
        else:
            log_count = getattr(self, "log_count", 0)
            self.log_count = log_count + 1

        return False

    def reset_count(self):
        self.last_log = None
        log_count = getattr(self, "log_count", 0)
        if log_count > 1:
            print(f"Suppressed {self.log_count} similar messages")
        self.log_count = 0


def warn_without_traceback(message, category, filename, lineno, file=None, line=None):

    log = file if hasattr(file, "write") else sys.stderr
    log.write(f"Warning: {message}\n")


class ParserPrintHelp(argparse.ArgumentParser):
    def error(self, message, exit_code=2):
        sys.stderr.write("error: %s\n" % message)
        self.print_help()
        sys.exit(exit_code)


class SnapwellRunner:
    def __init__(self, config, grid, restart, init, wellpaths, resinsight):
        self.config = config
        self.grid = grid
        self.restart = restart
        self.init = init
        self.wellpaths = wellpaths
        self.resinsight = resinsight

    def run_and_write(self, wp, wp_date):
        try:
            # call to main algorithm
            snap(
                wp,
                self.grid,
                self.restart,
                self.init,
                wp_date,
                owc_offset=self.config.owcOffset(),
                keywords=self.config.logKeywords(),
                delta=self.config.deltaZ(),
                owc_definition=self.config.owcDefinition(),
            )
            # write wellpath to file
            rows = wp.write(
                overwrite=self.config.overwrite(), resinsight=self.resinsight
            )
            logging.info("Wrote %d rows to %s.out", rows, wp.filename())
            # done with this wellpath

        except ValueError as err:
            logging.error("in well/grid/restart values: %s", err)
            return False
        except IOError as err:
            logging.error("while writing file: %s", err)
            return False
        return True

    def main_loop(self):
        num_snaps = len(self.wellpaths)
        logging.info("delta_z    = %.3f", self.config.deltaZ())
        logging.info("owc_offset = %.3f", self.config.owcOffset())
        owc_def = self.config.owcDefinition()
        logging.info("owc_defini = %.3f (%s)", owc_def[1], owc_def[0])
        logging.info("output     = %s", self.config.output())
        success = True
        for i, wp in enumerate(self.wellpaths):
            wp_date = self.config.date(i)
            sep = "=" * 79
            logging.info("\n\n%s", sep)
            logging.info("%d/%d \t Snapping %s", i + 1, num_snaps, wp.wellname())
            start = time()
            success = success and self.run_and_write(wp, wp_date)
            stop = time()
            sec = round(stop - start, 2)
            logging.info("Operation took %s seconds", str(sec))
        return success


class SnapwellApp:
    def __init__(self, argv):
        self.parser = self.make_parser(argv[0])
        self.argv = argv[1:]

    def parse_args(self):
        return self.parser.parse_args(self.argv)

    def load_config(self, args):
        snap_conf = args.config

        if args.owc_offset:
            snap_conf.setOwcOffset(args.owc_offset)
        if args.output:
            outpath = path.abspath(args.output)
            if path.isfile(outpath):
                self.exit_with_usage(
                    "Output path is an existing file. Delete it or choose a different output path."
                )
            if not path.exists(outpath):
                makedirs(outpath)
            snap_conf.setOutput(outpath)
        if args.overwrite:
            snap_conf.setOverwrite(args.overwrite)
        if args.owc_definition:
            snap_conf.setOwcDefinition(args.owc_definition)
        if args.owc_offset:
            snap_conf.setOwcOffset(args.owc_offset)
        if args.delta:
            snap_conf.setDeltaZ(args.delta)
        return snap_conf

    def load_wellpaths(self, config):
        logging.info("Loading %d wells", len(config))

        wellpaths = []
        for i in range(len(config)):
            fname = config.filename(i)
            logging.info(fname, end=" ... ")
            wp = config.getWellpath(i)
            logging.info("(%d points, %d logs)", len(wp), len(wp.headers()))
            wellpaths.append(wp)
            logging.info("done")
        return wellpaths

    def load_restart_file(self, config):
        logging.info("Loading restart %s", config.restartFile())
        restart = None
        restartFile = config.restartFile()
        try:
            restart = config.getRestart()
        except Exception as err:
            logging.warning("supplied RESTART file not loaded: %s", err)

        if not restart:
            if not path.isfile(restartFile):
                self.exit_with_usage("Missing restart: No such file %s." % restartFile)
            else:
                self.exit_with_usage(
                    "Missing restart: Failed to read restart file %s." % restartFile
                )
        return restart

    def load_grid_file(self, config):
        logging.info("Loading grid %s", config.gridFile())
        grid = None
        gridFile = config.gridFile()
        try:
            grid = config.getGrid()
        except Exception as err:
            logging.warning("supplied GRID file not loaded: %s", err)
        if not grid:
            if not path.isfile(gridFile):
                self.exit_with_usage("Missing grid: No such file %s." % gridFile)
            else:
                self.exit_with_usage(
                    "Missing grid: Failed to read grid file %s." % gridFile
                )
        return grid

    def load_init_file(self, config):
        init = None
        if config.initFile():
            logging.info("Loading INIT %s", config.initFile())
            try:
                init = config.getInit()
            except Exception as err:
                logging.warning("supplied INIT file not loaded: %s", err)

        if not init:
            logging.info("No INIT file, will not output PERM values")
        return init

    def exit_with_usage(self, msg=None, exit_code=0):
        self.parser.error(message=msg, exit_code=exit_code)

    @staticmethod
    def make_parser(prog):
        def snapwell_config_file(conf_file):
            if not path.exists(conf_file):
                raise argparse.ArgumentTypeError(
                    f"No such file or directory: {conf_file}"
                )

            if not path.isfile(conf_file):
                raise argparse.ArgumentTypeError(
                    "A Snapwell config file is needed.  Provide full path to config file."
                )

            if not conf_file[-3:] == ".sc":
                logging.warning(
                    "It is highly recommended that a Snapwell config file has file extension .sc"
                )
            logging.info("Parsing config file %s", conf_file)
            try:
                return SnapConfig.parse(conf_file)
            except ValueError as err:
                raise argparse.ArgumentTypeError(
                    f"Error while parsing snapwell config file: {err}"
                ) from err

        def owc_definition(od):
            od = od.strip()
            if ":" not in od:
                raise argparse.ArgumentTypeError(
                    "owc definition is malformed: missing ':'"
                )
            t = od.split(":")
            if len(t) != 2:
                raise argparse.ArgumentTypeError(
                    "owc definition is malformed: more than one ':'"
                )
            odkw, odval = t[0], t[1]
            odval = tryFloat(odval, ret=None)
            if odval is None:
                raise argparse.ArgumentTypeError(
                    f"owc definition is malformed: could not parse value {odval}"
                )
            if not odkw.isalpha():
                raise argparse.ArgumentTypeError(
                    f"owc definition is malform: could not parse key word {odkw}"
                )
            return odkw.upper(), odval

        parser = ParserPrintHelp(
            prog=prog, description="Snapwell --- a wellpath optimization program."
        )
        parser.add_argument(
            "-o",
            "--output",
            type=str,
            help="Output folder. In this folder, all the new wellpath files are written.",
        )
        parser.add_argument(
            "-z", "--owc_offset", type=float, help="OWC offset in meters, e.g. 0.5"
        )
        parser.add_argument(
            "-f",
            "--owc_definition",
            type=owc_definition,
            help="OWC definition, e.g. SWAT:0.7",
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
            "--version",
            action="version",
            version="%(prog)s {version}".format(version=VERSION),
        )

        parser.add_argument(
            "config",
            type=snapwell_config_file,
            help="The Snapwell configuration file, e.g. snap.sc",
        )
        return parser

    def runner(self):
        args = self.parse_args()
        config = self.load_config(args)
        return SnapwellRunner(
            config,
            self.load_grid_file(config),
            self.load_restart_file(config),
            self.load_init_file(config),
            self.load_wellpaths(config),
            args.resinsight,
        )


def run(app):
    fullstart = time()

    runner = app.runner()

    confstop = time()
    conftime = round(confstop - fullstart, 2)
    logging.info("\n\nConfiguration completed in %s sec.\n", str(conftime))

    success = runner.main_loop()

    fullstop = time()
    fullsec = round(fullstop - fullstart, 2)
    logging.info("snapwell completed in %s seconds", str(fullsec))

    if not success:
        logging.error("Snapwell completed, but errors occurred")
        return -1
    return 0


def main():
    logging.basicConfig(format="%(levelname)s: %(message)s")
    f = DuplicateFilter()
    logging.getLogger().addFilter(f)
    logging.info("Snapwell launched")
    warnings.showwarning = warn_without_traceback
    exit_val = run(SnapwellApp(sys.argv))
    f.reset_count()
    sys.exit(exit_val)


if __name__ == "__main__":
    main()
