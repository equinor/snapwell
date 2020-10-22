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

import logging
from dataclasses import field
from datetime import date
from math import inf
from os import path
from pathlib import Path
from typing import List, Optional

from ecl.eclfile import EclFile
from ecl.grid import EclGrid
from pydantic.dataclasses import dataclass
from typing_extensions import Literal

from .wellpath import WellPath


class SnapWellConfig:
    validate_all = True
    validate_assignment = True
    extra = "forbid"
    arbitrary_types_allowed = True


@dataclass(config=SnapWellConfig)
class OwcDefinition:
    keyword: str = "SWAT"
    value: float = 0.7


@dataclass(config=SnapWellConfig)
class WellPathFile:
    well_file: Path
    date: date
    owc_definition: Optional[float] = None
    owc_offset: Optional[float] = None
    depth_type: Optional[Literal["TVD", "MD"]] = None
    window_depth: float = -inf


@dataclass(config=SnapWellConfig)
class SnapConfig:
    grid_file: Path
    restart_file: Path
    wellpath_files: List[WellPathFile]
    init_file: Optional[Path] = None
    overwrite: bool = False
    output_dir: Path = "."
    owc_offset: float = 0.5
    owc_definition: OwcDefinition = OwcDefinition()
    log_keywords: List[str] = field(default_factory=list)
    delta_z: float = inf

    def set_base_path(self, new_base):
        """
        sets the base path for relative paths in the config.
        """
        if not self.grid_file.is_absolute():
            self.grid_file = Path(new_base).joinpath(self.grid_file)
        if not self.restart_file.is_absolute():
            self.restart_file = Path(new_base).joinpath(self.restart_file)
        if not self.output_dir.is_absolute():
            self.output_dir = Path(new_base).joinpath(self.output_dir)
        if self.init_file is not None and not self.init_file.is_absolute():
            self.init_file = Path(new_base).joinpath(self.init_file)

        for wpf in self.wellpath_files:
            if not wpf.well_file.is_absolute():
                wpf.well_file = Path(new_base).joinpath(wpf.well_file)

    @property
    def wellpaths(self):
        logging.info("Loading %d wells", len(self.wellpath_files))

        def read_wellpath_file(wpf):
            wp = WellPath.parse(str(wpf.well_file), date=wpf.date)
            if (
                wp.well_name
                and len(wp.well_name) > 1
                and len(wp.well_name.split()) == 1
            ):
                wp.file_name = path.abspath(path.join(self.output_dir, wp.well_name))
            wp.depth_type = wpf.depth_type
            wp.window_depth = wpf.window_depth
            logging.info(
                "Configuring depth: %s [%s]", str(wp.window_depth), str(wp.depth_type)
            )

            wp.owc_definition = wpf.owc_definition
            wp.owc_offset = wpf.owc_offset
            logging.info("(%d points, %d logs)", len(wp), len(wp.headers))
            logging.info("done")
            return wp

        return [read_wellpath_file(wpf) for wpf in self.wellpath_files]

    @property
    def grid(self):
        return EclGrid(str(self.grid_file))

    @property
    def restart(self):
        return EclFile(str(self.restart_file))

    @property
    def init(self):
        return EclFile(str(self.init_file))
