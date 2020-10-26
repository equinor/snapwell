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
from functools import wraps
from math import inf, isinf, isnan
from os.path import exists


def finiteFloat(elt):
    return not (isinf(elt) or isnan(elt))


def _ignorable_(line):
    line = line.strip()
    if not line or (len(line) >= 2 and line[:2] == "--"):
        return True  # ignorable, yes
    return False


def token(f):
    token = ""
    while _ignorable_(token):
        token = f.readline()
        if not token:
            return None
        token = strip_line(token)
    return token


def strip_line(l):
    """strips string and replace tabs and multiple spaces with single space."""
    l = l.replace("\t", " ")
    while "  " in l:
        l = l.replace("  ", " ")
    return l.strip()


def takes_stream(i, mode):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if len(args) > i and args[i] is not None and isinstance(args[i], str):
                with open(args[i], mode) as f:
                    return func(*args[:i], f, *args[i + 1 :], **kwargs)
            else:
                return func(*args, **kwargs)

        return wrapper

    return decorator


class WellPath:
    """A WellPath is essentially a dictionary of lists containing at the very least,
    x (UTM), y (UTM), z (UTM, TVD), followed by an arbitrary amount of well
    logs (specified in WellPath file), e.g. measured depth, inclination, and
    azimuth.

    (This is essentially a very basic Excel file, with some minimal metadata.)

    Can also contain z-opt, z-diff, permx, swat values etc.

    """

    def __init__(self, version=1.0, welltype="", wellname="", date=None, filename=None):
        self._table = {"x": [], "y": [], "z": []}
        self._version = version
        self.well_type = welltype
        self.well_name = wellname
        self.headers = ["x", "y", "z"]
        self._filename = filename
        self._rkb = (0.0, 0.0, 0.0)
        self._depth_type = None
        self._window_depth = -inf
        self.owc_definition = None
        self.owc_offset = None
        self.date = date
        if filename and filename.endswith(".yaml"):
            logging.warning(
                "WellPath file extension is .yaml.  Potentially a Snapwell config file."
            )

    @property
    def file_name(self):
        return self._filename

    @file_name.setter
    def file_name(self, fname):
        self._filename = fname

    @property
    def rkb(self):
        x, y, z = self._rkb[0], self._rkb[1], self._rkb[2]
        return float(x), float(y), float(z)

    @rkb.setter
    def rkb(self, rkb):
        """Set RKB (x,y,z) to be given triple.  Need a triple of float-able values."""
        if len(rkb) != 3:
            raise IndexError("Need a triple (x,y,z) of floats, not %s" % str(rkb))
        try:
            t = float(rkb[0]), float(rkb[1]), float(rkb[2])
            self._rkb = t
        except ValueError as err:
            raise ValueError(
                "Need x,y,z to be floats, got (%s, %s, %s)"
                % (str(type(rkb[0])), str(type(rkb[1])), str(type(rkb[2])))
            ) from err

    @property
    def depth_type(self):
        return self._depth_type

    @depth_type.setter
    def depth_type(self, depth_type):
        """If None, resets windowdepth to -inf, else must be MD or TVD."""
        if not depth_type:
            self._window_depth = -inf
            self._depth_type = None
        elif depth_type in ["MD", "TVD"]:
            self._depth_type = depth_type
        else:
            raise ValueError(
                'Window depth type must be None, "MD", or "TVD", not %s' % depth_type
            )

    @property
    def window_depth(self):
        return self._window_depth

    @window_depth.setter
    def window_depth(self, depth):
        self._window_depth = float(depth)

    def add_column(self, header, data=None):
        if not data:
            data = []
        if header in self._table:
            raise KeyError("Key %s exists in table." % header)
        lx = len(self)
        ld = len(data)
        if ld != lx:
            raise IndexError(
                "Data needs to be of len(wp)=%d, was given %d entries." % (lx, ld)
            )
        self._table[header] = data
        self.headers.append(header)

    def remove_column(self, header):
        if header in ["x", "y", "z"]:
            raise ValueError(
                "Cannot delete column %s.  A WellPath must contain x, y, and z."
                % str(header)
            )
        if header in self._table:
            del self._table[header]
            hs = [h for h in self.headers if h != header]
            self.headers = hs

    def add_raw_row(self, row):
        """Adds a raw row, where row now is a list following header's order"""
        if len(row) != len(self._table):
            raise IndexError(
                "Cannot insert %s into table of %d columns." % (row, len(self._table))
            )
        idx = 0
        for key in self.headers:
            self._table[key].append(row[idx])
            idx += 1

        if len(self) == 1:
            self._update_rkb()

    def rows(self):
        for i in range(len(self)):
            yield [self._table[c][i] for c in self.headers]

    def _update_rkb(self):
        """Updates the RKB values to the correct ones, that is, rkb=(x, y, z_r) where x
        and y are the x and y values of the first path point and the z_r is
        MD-TVD for the first point.

        In the case where MD or TVD are not finite floats for the first
        point, this function will do nothing and return False.  The function
        returns true if all conditions for value updating is met.

        """
        if len(self) == 0:
            return False
        if "MD" not in self.headers:
            return False
        x, y = self._table["x"][0], self._table["y"][0]
        tvd, md = self._table["z"][0], self._table["MD"][0]
        if finiteFloat(md) and finiteFloat(tvd):
            self.rkb = (x, y, md - tvd)
            return True
        else:
            return False

    def update(self, col, idx, elt):

        """Sets elt in the idx'th position of column col."""
        rs = len(self)
        cs = len(self.headers)
        if not 0 <= idx < rs:
            raise IndexError("row index out of range, 0 <= idx < %d" % rs)

        if isinstance(col, (int)):
            if not 0 <= col < cs:
                raise IndexError("column index out of range, 0 <= col < %d" % cs)
            col = self.headers[col]

        if col not in self.headers:
            raise KeyError("Key %s does not name a column" % str(col))

        self._table[col][idx] = elt

    def __getitem__(self, idx):
        if isinstance(idx, str):
            return self._table[idx]
        return [self._table[key][idx] for key in self.headers]

    def __contains__(self, idx):
        if isinstance(idx, str):
            return idx in self._table
        return all(len(self._table[key]) > idx for key in self.headers)

    def __setitem__(self, idx, elt):
        lx = len(self.headers)
        ld = len(elt)
        for i in range(min(lx, ld)):
            h = self.headers[i]
            self._table[h][idx] = elt[i]
        if idx == 0:
            self._update_rkb()

    def __len__(self):
        """The number of rows, i.e., the number of wellpoints."""
        return len(self._table["x"])

    def __str__(self):
        return self.well_name

    @staticmethod
    @takes_stream(0, "r+")
    def parse(f, date=None):
        """Given a file, parses and returns a WellPath object.
        * easting  (X UTM)
        * northing (Y UTM)
        * tvd mls  (Z UTM, true vertical depth)
        * ...      (specified in format file, see readme)
        """

        fname = getattr(f, "name", "stream")

        version = token(f)
        well_type = token(f)

        # well_name and RKB
        wellconfig = token(f).split()
        well_name = wellconfig[0]
        rkb_x, rkb_y, rkb_z = 0, 0, 0
        try:
            if len(wellconfig) > 1:
                rkb_x = float(wellconfig[1])
            if len(wellconfig) > 2:
                rkb_y = float(wellconfig[2])
            if len(wellconfig) > 3:
                rkb_z = float(wellconfig[3])
        except Exception as err:
            raise ValueError(f"Could not parse RKB values: {err}") from err

        wp = WellPath(
            version=version,
            welltype=well_type,
            wellname=well_name,
            filename=fname,
            date=date,
        )
        wp.rkb = (rkb_x, rkb_y, rkb_z)

        num_columns_line = token(f)
        try:
            num_columns = int(num_columns_line)
        except ValueError as err:
            raise ValueError(
                f"Could not parse WellPath file, no <num_logs> integer, {fname}: {err}"
            ) from err

        for _ in range(num_columns):
            header = token(f).split()[0]  # ignore unit,scale for now
            wp.add_column(header)

        while True:  # loop-and-a-half
            t = token(f)
            if t is None:
                break
            data = [float(e) for e in t.split()]
            wp.add_raw_row(data)
        f.close()

        return wp

    def write_to_stream(self, out, resinsight=False):
        """
        result is the same as WellPath.write, but writes to the
        given stream.
        """
        nl = "\n"

        def fmt(s):
            return "%.2f" % s

        if resinsight:
            out.write(self.well_name)
            out.write(nl)
            for r in self.rows():
                out.write(
                    " ".join(map(fmt, r[:4])) + nl
                )  # ResInsight wants only 'x y tvd md'
        else:
            out.write(self._version)
            out.write(nl)
            out.write(self.well_type)
            out.write(nl)
            out.write(self.well_name)
            out.write(" ")
            out.write(" ".join(map(fmt, self._rkb)))
            out.write(nl)
            out.write(str(len(self.headers) - 3))
            out.write(nl)
            for i in range(3, len(self.headers)):
                out.write(f"{self.headers[i]} 1 lin" + nl)
            for r in self.rows():
                out.write(" ".join(map(fmt, r)) + nl)

    def write(self, fname=None, overwrite=False, resinsight=False):
        """Opens fname and writes this object to file in the typical WellPath format
        (see readme).  If fname exists and overwrite is not explicitly set to
        True, this method will throw.

        The output is version\ntype\nname\n0\ndata where data is len(this)
        many lines of three (space separated) columns with the columns being,
        respectively, x (utm), y (utm) and z (utm), the latter being the new
        depth-optimized output.

        """
        if not fname:
            if not self.file_name:
                raise ValueError(
                    "WellPath.file_name is unspecified and fname not provided.  "
                    "Need at least one."
                )
            fname = "%s.out" % self._filename
        if not overwrite:
            if exists(fname):
                raise IOError(
                    "Filename %s exists, cannot overwrite unless explicitly told to!"
                    % fname
                )

        with open(fname, "w") as fname_out:
            self.write_to_stream(fname_out, resinsight)

        return len(self)
