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

import datetime
from os import path, makedirs
import logging
from math import isnan

from ecl.eclfile import EclFile
from ecl.grid import EclGrid
from res.config import ContentTypeEnum, ConfigParser

from .snap_utils import Inf, parse_date
from .wellpath import WellPath


class SnapConfig:
    """A class for representing a Snapwell config object.  It contains
    the filename (path) for grid, for restart file, and a list of
    (welldata file, date)-pairs.
    """

    def __init__(self, grid, restart, init=None):
        self._grid = None
        self._restart = None
        self._init = None
        self._gridFile = grid
        self._restartFile = restart
        self._initFile = init
        self._wellpath_config = []
        self._output = "."  # Output path
        self._overwrite = False  # Are we allowed to overwrite files?
        self._delta = Inf  # max ascend/descend rate for wellpaths
        self._owc_offset = 0.5  # default OWC Z offset
        self._owc_definition = ("SWAT", 0.7)  # definition of OWC
        self._logKeywords = []

    def __len__(self):
        return len(self._wellpath_config)

    def __getitem__(self, index):
        return self._wellpath_config[index]

    def __str__(self):
        m = {}
        m["grid"] = self._gridFile
        m["restart"] = self._restartFile
        m["init"] = self._initFile
        m["wellpath"] = self._wellpath_config
        return "snap: " + str(m)

    def _append(self, elt):
        """Append an elt=(fname, date) pair to wellpath.  In this setting, elt[0] should
        be a string that is a filepath to a wellpath and elt[1] should be
        datetime, corresponding to the restart time of this wellpath.

        """
        if type(elt[1]) is not type(datetime.datetime(2000, 1, 1)):
            raise TypeError("Need datetime object, not " + str(elt[1]))
        self._wellpath_config.append(elt)

    def setOwcOffset(self, owc):
        """This is the OWC Z offset value used.  That is, if OWC in the GRID is found to
        be at 1761.3, and owc=0.5 (the usual value), then we are interested
        in placing the wellpoint at 1761.3-0.5=1760.8.

        """
        self._owc_offset = float(owc)

    def owcOffset(self):
        return self._owc_offset

    def addLogKeyword(self, log):
        """Add log keywords items"""
        self._logKeywords.append(log)

    def logKeywords(self):
        return self._logKeywords

    def owcDefinition(self):
        """The definition of OWC might be owcDefinition=('SWAT', 0.7).  This
        means that OWC is the first z-point from the bottom that has cell
        property SWAT=0.7 (interpolated).  Can also be SGAS=0.1 ..."""
        return self._owc_definition

    def setOwcDefinition(self, owc_definition):
        if len(owc_definition) != 2:
            raise ValueError(
                "OWC Definition must be a (str, float)-pair, not %s"
                % str(owc_definition)
            )
        self._owc_definition = tuple(owc_definition)

    def setDeltaZ(self, delta):
        """This delta is the max inclination of a wellpath, i.e., we cannot have h_diff
        (horizontal difference) between two wellpoints h_diff/z_diff > delta.
        """
        self._delta = float(delta)

    def deltaZ(self):
        return self._delta

    def setOutput(self, path):
        """The output folder to which we write the new wellpaths."""
        self._output = path

    def output(self):
        return self._output

    def setOverwrite(self, overwrite):
        """If this is set to True, we will overwrite the wellpath files.

        This should not be set to true unless you know what you are doing,
        hence the rigidity in "if overwrite is True".
        """
        self._overwrite = False
        if overwrite is True:
            self._overwrite = True

    def overwrite(self):
        return self._overwrite is True

    def getWellpath(self, idx):
        fname = self.filename(idx)
        wp = WellPath.parse(fname)
        if wp.wellname() and len(wp.wellname()) > 1 and len(wp.wellname().split()) == 1:
            wp.setFilename(path.abspath(path.join(self._output, wp.wellname())))
        if self.depthType(idx):
            wp.setDepthType(self.depthType(idx))
            wp.setWindowDepth(self.windowDepth(idx))
            print(
                "Configuring depth: %s [%s]"
                % (str(wp.windowDepth()), str(wp.depthType()))
            )

        wp.setOwcDefinition(self.igetOwcDefinition(idx))
        wp.setOwcOffset(self.igetOwcOffset(idx))

        return wp

    def filename(self, idx):
        """Return filename of idx'th wellpath."""
        return self._wellpath_config[idx][0]

    def date(self, idx):
        """Return date of idx'th wellpath."""
        return self._wellpath_config[idx][1]

    def igetOwcDefinition(self, idx):
        """Returns the OWC_DEFINITION for wp idx if set, or None"""
        key = "OWC_DEFINITION"
        if key in self._wellpath_config[idx][2]:
            return self._wellpath_config[idx][2][key]
        return None

    def igetOwcOffset(self, idx):
        """Returns the OWC_OFFSET for wp idx if set, or None"""
        key = "OWC_OFFSET"
        if key in self._wellpath_config[idx][2]:
            return self._wellpath_config[idx][2][key]
        return None

    def depthType(self, idx):
        """Return depth type (MD/TVD) of idx'th wellpath or None if not set."""
        if "MD" in self._wellpath_config[idx][2]:
            return "MD"
        if "TVD" in self._wellpath_config[idx][2]:
            return "TVD"
        return None

    def windowDepth(self, idx):
        """Return depth of idx'th wellpath or -inf if not set."""
        dt = self.depthType(idx)
        if dt:
            return self._wellpath_config[idx][2][dt]
        return -Inf

    def gridFile(self):
        return self._gridFile

    def restartFile(self):
        return self._restartFile

    def initFile(self):
        return self._initFile

    def getGrid(self):
        if self._grid is None:
            self._grid = EclGrid(self.gridFile())
        return self._grid

    def getRestart(self):
        if self._restart is None:
            self._restart = EclFile(self.restartFile())
        return self._restart

    def getInit(self):
        if self._init is None and self._initFile:
            self._init = EclFile(self.initFile())
        return self._init

    @staticmethod
    def tryset(setter, value, content):
        if not value in content:
            return False
        try:
            val = content[value][0][0]
            setter(val)
            return True
        except Exception as err:
            logging.warning("Ill specified %s.  Ignoring. %s" % (value, err))

    @staticmethod
    def addConfigItemFloat(parser, value, repeated=False):
        item = parser.add(value, repeated)
        item.iset_type(0, ContentTypeEnum.CONFIG_FLOAT)

    @staticmethod
    def addConfigItemPath(parser, value, repeated=False):
        item = parser.add(value, repeated)
        item.iset_type(0, ContentTypeEnum.CONFIG_PATH)

    @staticmethod
    def parse(fname):
        """Takes a configuration object containing grid file path, restart file
        path and a list of wellpath-files and their restart dates.  Returns a
        SnapWell object, containing this info.

        """

        conf = ConfigParser()

        SnapConfig.addConfigItemPath(conf, "GRID")
        SnapConfig.addConfigItemPath(conf, "RESTART")
        SnapConfig.addConfigItemPath(conf, "INIT")
        SnapConfig.addConfigItemPath(conf, "OUTPUT")

        overwrite_item = conf.add(
            "OVERWRITE", False
        )  # the last OVERWRITE specified counts
        overwrite_item.iset_type(0, ContentTypeEnum.CONFIG_STRING)

        SnapConfig.addConfigItemFloat(conf, "OWC_OFFSET")
        SnapConfig.addConfigItemFloat(conf, "DELTA_Z")

        owc_def_item = conf.add("OWC_DEFINITION")  # e.g. OWC_DEFINITION SWAT 0.7
        owc_def_item.iset_type(0, ContentTypeEnum.CONFIG_STRING)
        owc_def_item.iset_type(1, ContentTypeEnum.CONFIG_FLOAT)

        log_item = conf.add("LOG")
        log_item.iset_type(0, ContentTypeEnum.CONFIG_STRING)

        wellpath_item = conf.add("WELLPATH", True)  # a series of WELLPATH/DATE pairs
        wellpath_item.iset_type(0, ContentTypeEnum.CONFIG_PATH)
        wellpath_item.iset_type(1, ContentTypeEnum.CONFIG_STRING)

        content = conf.parse(fname)

        # Grid
        gridFile = tryGetPath(content, "GRID", 0, 0)
        if not gridFile:
            logging.info("No GRID file specified?")
            raise ValueError("Could not load GRID file from Snapwell config file.")

        # Restart
        restartFile = tryGetPath(content, "RESTART", 0, 0)
        if not restartFile:
            logging.info("No RESTART file specified?")
            raise ValueError("Could not load RESTART file from Snapwell config file.")

        # init
        initFile = None
        if "INIT" in content:
            initFile = tryGetPath(content, "INIT", 0, 0)
        s = SnapConfig(gridFile, restartFile, initFile)

        # output
        outputPath = None
        if "OUTPUT" in content:
            outputPath = tryGetPath(content, "OUTPUT", 0, 0)
            if path.exists(outputPath):
                if path.isfile(outputPath):
                    raise ValueError(
                        "Provided output folder is a file.  Either delete file, or set a different output folder: %s"
                        % outputPath
                    )
                else:
                    s.setOutput(outputPath)
            else:
                makedirs(outputPath)
                s.setOutput(outputPath)

        # overwrite
        overwrite = False
        if "OVERWRITE" in content:
            overwrite = tryGet(content, "OVERWRITE", 0, 0)
            try:
                if overwrite.strip().lower() == "true":
                    overwrite = True
            except Exception as err:
                logging.warning('Ill specified overwrite flag: "%s".' % err)
        s.setOverwrite(overwrite)

        SnapConfig.tryset(s.setDeltaZ, "DELTA_Z", content)
        SnapConfig.tryset(s.setOwcOffset, "OWC_OFFSET", content)

        # Loading OWC_DEFINITION
        if "OWC_DEFINITION" in content:
            try:
                if len(content["OWC_DEFINITION"][0]) != 2:
                    logging.warning(
                        "Wrong number of arguments in OWC_DEFINITION.  Needs to be e.g. SWAT 0.7, got %s"
                        % str(content["OWC_DEFINITION"][0])
                    )
                else:
                    owc_kw = tryGet(content, "OWC_DEFINITION", 0, 0)
                    owc_val = tryGetFloat(content, "OWC_DEFINITION", 0, 1)
                    s.setOwcDefinition((owc_kw, owc_val))
            except Exception as err:
                logging.warning('Ill specified OWC_DEFINITION keyword: "%s".' % err)
        else:
            logging.info("Using OWC definition %s" % str(s.owcDefinition()))

        if "LOG" in content:
            for i in range(len(content["LOG"])):
                line = content["LOG"][i]
                num_tokens = len(line)
                if num_tokens < 1:
                    raise ValueError(
                        'Missing data in LOG %d: "%s".' % (i + 1, str(line))
                    )
                s.addLogKeyword(tryGet(content, "LOG", i, 0))

        # Loading the wellpath file names
        if "WELLPATH" not in content:
            logging.warning("No wellpaths provided in Snapwell config file.")
            return s

        for i in range(len(content["WELLPATH"])):
            wp_line = content["WELLPATH"][i]
            num_tokens = len(wp_line)
            if num_tokens < 2:
                raise ValueError(
                    'Missing data in WELLPATH %d: "%s".' % (i + 1, str(wp_line))
                )

            fname = tryGetPath(content, "WELLPATH", i, 0)

            date_str = tryGet(content, "WELLPATH", i, 1)
            date = None
            try:
                date = parse_date(date_str)
            except ValueError as err:
                logging.info(str(err))
            if date is None:
                raise ValueError(
                    'Could not read date from wellpath %d.  Got date string "%s".'
                    % (i + 1, str(date_str))
                )

            if num_tokens % 2 != 0:
                raise ValueError(
                    "WELLPATH format error.  Need an even number of tokens, got %d tokens: %s"
                    % (num_tokens, str(wp_line))
                )
            settings = {}
            # WELLPATH /path/to/file.w 1996-01-01 MD 134 OWC_DEFINITION 0.3 OWC_OFFSET 0.1
            for idx in range(2, len(wp_line), 2):
                settings_key = tryGet(content, "WELLPATH", i, idx)
                settings_val = tryGetFloat(content, "WELLPATH", i, idx + 1)
                if settings_key not in settings and settings_val is not None:
                    settings[settings_key] = settings_val
                else:
                    logging.warning(
                        "Failed to retrieve key/value from wellpath %d: %s %s"
                        % (
                            i + 1,
                            content["WELLPATH"][i][idx],
                            content["WELLPATH"][i][idx + 1],
                        )
                    )

            s._append((fname, date, settings))
        return s


def tryGetPath(cnt, key, idx1, idx2):
    try:
        return path.expanduser(cnt[key][idx1].getPath(idx2))
    except Exception as e:
        logging.warning("Failed to load path key %s from Snapwell config file." % key)
    return None


def tryGet(cnt, key, idx1, idx2):
    try:
        return cnt[key][idx1][idx2]
    except Exception as e:
        logging.warning("Failed to load key %s from Snapwell config file." % key)
    return None


def tryGetFloat(cnt, key, idx1, idx2):
    try:
        return float(cnt[key][idx1][idx2])
    except Exception as e:
        logging.warning("Failed to load key %s from Snapwell config file." % key)
    return None
