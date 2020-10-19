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

from datetime import datetime
from math import isinf, isnan, sqrt

Nan = float("nan")  # Not-a-number capitalized like None, True, False
Inf = float("inf")  # infinite value capitalized ...


def _ignorable_(line):
    line = line.strip()
    if not line or (len(line) >= 2 and line[:2] == "--"):
        return True  # ignorable, yes
    return False


def read_next_tokenline(f):
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


def parse_date(s):
    """Returns a datetime string if input is either YYYY, YYYY-MM or YYYY-MM-DD."""
    d = None
    try:
        d = datetime.strptime(s, "%Y-%m-%d")
    except Exception:
        pass
    try:
        d = datetime.strptime(s, "%Y-%m")
    except Exception:
        pass
    try:
        d = datetime.strptime(s, "%Y")
    except Exception:
        pass

    if d is None:
        raise ValueError(
            "Provide a datetime string on the form YYYY-MM-DD, YYYY-MM, or YYYY, not %s"
            % str(s)
        )
    return d


def roundAwayFromEven(val):
    """Eclipse cannot deal with values close to even integers.  We
    (in)sanitize the value so that it always will be at least 0.1m away
    from an even integer.

    This function only makes sense should you assume cell floors are at even
    integers.
    """
    epsilon = 0.1
    r = val % 2.0
    if r < epsilon:
        return round(val) + epsilon
    if r > (2.0 - epsilon):
        return round(val) - epsilon
    return val


def findRestartStep(restart, date):
    """Finds the last restart step in the given restart file before the given date."""
    # start at 1, since we return step - 1
    for step in range(1, restart.num_report_steps()):
        new_date = restart.iget_restart_sim_time(step)  # step date
        if new_date > date:
            return step - 1

    # did not find it, return len - 1
    return step


def findKeyword(kw, restart, date, step=None):
    """Find and return kw (EclKW) from restart file at the last step before given
    date.
    """
    if not step:
        step = findRestartStep(restart, date)
    if not (0 <= step < restart.num_report_steps()):
        raise ValueError("restart step out of range 0 <= %d < steps" % step)
    return restart.iget_named_kw(kw, step)


def enterSnapMode(mode, wp, idx):
    """Checks if we are in snap mode.  This happens if we are already snapping, or
    if we have reached a prescribed window depth.
    """
    if mode or not wp.depthType():
        return True
    t = wp.depthType()

    return wp[t][idx] > wp.windowDepth()


def finiteFloat(elt):
    return not (isinf(elt) or isnan(elt))


def close(f1, f2, epsilon=0.0001):
    """Checks if f1~f2 with epsilon accuracy."""
    return abs(f1 - f2) <= epsilon


def tryFloat(val, ret=0):
    try:
        return float(val)
    except ValueError:
        return ret


def dist(p1, p2):
    """Returns Euclidean distance between p1 and p2, i.e. Pythagoras.

    Works on coordinates of any dimension.  If p1 and p2 have different
    dimensionality, we pick the min(len(p1), len(p2)) first points of each
    coordinate.

    """
    return sqrt(sum([(e[0] - e[1]) ** 2 for e in zip(p1, p2)]))
