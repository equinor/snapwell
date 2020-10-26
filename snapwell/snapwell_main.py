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

import yaml

from snapwell import __version__ as VERSION
from snapwell import snap
from snapwell.snapconfig import OwcDefinition, SnapConfig


def percentage(value):
    try:
        value = float(value)
    except (ValueError, TypeError):
        raise argparse.ArgumentTypeError(f"Value must be float {value}")
    if 0.0 <= value <= 100.0:
        return value
    raise argparse.ArgumentTypeError(f"Value must be in range [0, 100] {value}")


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
    def __init__(self, config, grid, restart, permx, wellpaths, resinsight):
        self.config = config
        self.grid = grid
        self.restart = restart
        self.permx = permx
        self.wellpaths = wellpaths
        self.resinsight = resinsight
        self.errors = []

    def run_and_write(self, wp):
        if not self.config.output_dir.exists():
            makedirs(str(self.config.output_dir))
        try:
            # call to main algorithm
            snap(
                wp,
                self.grid,
                self.restart,
                wp.date,
                permx_kw=self.permx,
                owc_offset=self.config.owc_offset,
                keywords=self.config.log_keywords,
                delta=self.config.delta_z,
                owc_definition=self.config.owc_definition,
            )
            # write wellpath to file
            rows = wp.write(overwrite=self.config.overwrite, resinsight=self.resinsight)
            logging.info("Wrote %d rows to %s.out", rows, wp.file_name)
            # done with this wellpath

        except ValueError as err:
            logging.error("in well/grid/restart values: %s", err)
            self.errors.append("Snap failed for well path: {}".format(wp.file_name))
        except IOError as err:
            logging.error("while writing file: %s", err)
            self.errors.append("Failed to write well path: {}".format(wp.file_name))

    def main_loop(self):
        num_snaps = len(self.wellpaths)
        logging.info("delta_z    = %.3f", self.config.delta_z)
        logging.info("owc_offset = %.3f", self.config.owc_offset)
        owc_def = self.config.owc_definition
        logging.info("owc_defini = %.3f (%s)", owc_def.value, owc_def.keyword)
        logging.info("output     = %s", self.config.output_dir)
        for i, wp in enumerate(self.wellpaths):
            sep = "=" * 79
            logging.info("\n\n%s", sep)
            logging.info("%d/%d \t Snapping %s", i + 1, num_snaps, wp.well_name)
            start = time()
            self.run_and_write(wp)
            stop = time()
            sec = round(stop - start, 2)
            logging.info("Operation took %s seconds", str(sec))


class SnapwellApp:
    def __init__(self, argv):
        self.parser = self.make_parser(argv[0])
        self.args = self.parser.parse_args(argv[1:])

    def load_config(self):
        args = self.args
        snap_conf = args.config

        if args.owc_offset:
            snap_conf.owc_offset = args.owc_offset
        if args.output:
            outpath = path.abspath(args.output)
            if path.isfile(outpath):
                self.exit_with_usage(
                    "Output path is an existing file. Delete it or choose a different output path."
                )
            snap_conf.output_dir = outpath
        if args.overwrite:
            snap_conf.overwrite = args.overwrite
        if args.owc_definition:
            snap_conf.owc_definition = args.owc_definition
        if args.owc_offset:
            snap_conf.owc_offset = args.owc_offset
        if args.delta:
            snap_conf.delta_z = args.delta
        return snap_conf

    def load_restart_file(self, config):
        logging.info("Loading restart %s", config.restart_file)
        try:
            return config.restart
        except Exception as err:
            logging.error("supplied RESTART file not loaded: %s", err)

    def load_grid_file(self, config):
        logging.info("Loading grid %s", config.grid_file)
        try:
            return config.grid
        except IOError as err:
            logging.error("supplied GRID file not loaded: %s", err)

    def load_permx(self, config):
        init = None
        if "PERMX" in config.log_keywords:
            if config.init_file:
                logging.info("Loading INIT %s", config.init_file)
                try:
                    init = config.init
                except Exception as err:
                    self.exit_with_usage(f"could not load supplied INIT file: {err}")

            if not init:
                self.exit_with_usage("PERMX requested, but no INIT file given.")
            try:
                return init.iget_named_kw("PERMX", 0)
            except Exception as err:
                self.exit_with_usage(
                    f"Could not get permx keyword from init file: {err}"
                )
        if config.init_file:
            logging.warning("Init file set, but PERMX keyword not requested, ignoring.")
        return None

    def exit_with_usage(self, msg=None, exit_code=2):
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

            logging.info("Parsing config file %s", conf_file)
            try:
                with open(conf_file) as config_stream:
                    config_dict = yaml.safe_load(config_stream)
                    if not isinstance(config_dict, dict):
                        raise ValueError(
                            f"Wrong format in config file, expected root dictionary, but got {type(config_dict)}"
                        )
                    conf = SnapConfig(**config_dict)
                    conf.set_base_path(path.dirname(conf_file))
                    return conf
            except Exception as err:
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
            try:
                odval = float(odval)
            except Exception as err:
                raise argparse.ArgumentTypeError(
                    f"owc definition is malformed: could not parse value {odval}"
                ) from err
            if not odkw.isalpha():
                raise argparse.ArgumentTypeError(
                    f"owc definition is malform: could not parse key word {odkw}"
                )
            return OwcDefinition(odkw.upper(), odval)

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
        parser.add_argument(
            "-a",
            "--allow-fail",
            type=percentage,
            default=0.0,
            help="Allow a percentage of snaps to fail without application failing",
        )
        return parser

    def runner(self):
        config = self.load_config()
        return SnapwellRunner(
            config,
            self.load_grid_file(config),
            self.load_restart_file(config),
            self.load_permx(config),
            config.wellpaths,
            self.args.resinsight,
        )


def run(app):
    fullstart = time()

    runner = app.runner()

    confstop = time()
    conftime = round(confstop - fullstart, 2)
    logging.info("\n\nConfiguration completed in %s sec.\n", str(conftime))

    runner.main_loop()

    fullstop = time()
    fullsec = round(fullstop - fullstart, 2)
    logging.info("snapwell completed in %s seconds", str(fullsec))

    if runner.errors:
        error_msg = "Snapwell completed, but errors occurred: \n" + "\n".join(
            runner.errors
        )
        logging.error(error_msg)

    if len(runner.errors) / len(runner.wellpaths) * 100.0 > app.args.allow_fail:
        # The users sometimes want the program to pass even though it failed at
        # snapping all wells
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
