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

from ecl.eclfile import EclFile
from ecl.grid import EclGrid

from .snap_utils import Inf, Nan, roundAwayFromEven, findKeyword, enterSnapMode
from .snap_utils import close, dist


# The next ten lines are used for improved logging (skipping repeated lines)
_snap_prevmsg = ""
_snap_prevmsgcnt = 0


def doprint(msg):
    """Prints msg unless it's a repetition from the previous time this function was
    called, and if so, we output a repetition count and reset the counter.

    """

    global _snap_prevmsg, _snap_prevmsgcnt
    if msg == _snap_prevmsg:
        _snap_prevmsgcnt += 1
    else:
        if _snap_prevmsgcnt > 0:
            print("         %d similar messages skipped\n" % _snap_prevmsgcnt)
        _snap_prevmsgcnt = 0
        _snap_prevmsg = msg
        print(msg)


def _activeIdx(grid, i, j, k):
    """Get the active index corresponding to grid coordinate i, j, k.  Or -1."""
    if min(i, j, k) < 0:
        return -1
    return grid.get_active_index(ijk=(i, j, k))


_snap_prev_ijk = None


def _ijk(grid, x, y, z):
    """Get i,j,k for x,y,z in grid"""
    global _snap_prev_ijk

    ijk = grid.find_cell(x, y, z, start_ijk=_snap_prev_ijk)
    if not ijk:
        k = 0
        i, j = grid.findCellXY(x, y, 0)
        ijk = (i, j, k)

    _snap_prev_ijk = ijk
    return ijk


def activeCellColumn(grid, owc_kw, x, y, z):
    """Let i,j,k be the cell containing x,y,z.  This function returns a pair,
    (col,idx), where the first element, col, is a list of the active cells in
    the (i,j)-column

        [(i,j,n_z,an_z,sn_z), (i,j,n_z-1,an_z-1,sn_z-1), ..., (i,j,0,a0,s0)],

    where n_z is the height of the grid, at is the active index of the t'th
    cell in the list and st its s owc_kw.

    The second element of the output, idx, is the index of the cell
    containing x,y,z.  We filter away inactive cells.

    In the case where there is no cell found containing xyz, this function
    will return ([], -1).

    """
    col = []
    ret_idx = -1

    ijk = _ijk(grid, x, y, z)
    i, j, k = ijk
    nz = grid.getNZ()
    num_cells = 0
    for k_idx in range(nz - 1, -1, -1):  # backwards from nz-1 to 0
        a = _activeIdx(grid, i, j, k_idx)
        s = Nan
        if k_idx == k:
            ret_idx = num_cells
        if a >= 0:
            s = owc_kw[a]
            col.append((i, j, k_idx, a, s))
            num_cells += 1
    return (col, ret_idx)


def interpolate(grid, k_above, col, thresh):
    """Interpolates.  Takes grid, a index, the activeCellColumn and a threshold.

    Returns owc given that k_above is index of first cell whose center is
    above owc.

    """
    # we have crossed (OWC) the thresh border (from below)
    # this means inv_k is above OWC, whereas inv_k-1 is below
    k_below = k_above - 1
    if k_below < 0:
        raise IndexError("Cannot interpolate down from bottom cell.")
    a_idx_below = col[k_below][3]
    a_idx_above = col[k_above][3]  # recall col contains cell from bottom and up

    swat_below = col[k_below][4]  # the SWAT/SGAS/etc in cell above and below OWC
    swat_above = col[k_above][4]

    norm_swat_above = swat_below - swat_above
    norm_swat_thresh = swat_below - thresh
    norm_swat_ratio = 1 - (norm_swat_thresh / norm_swat_above)

    z_above = grid.get_xyz(active_index=a_idx_above)[
        2
    ]  # z coordinate of cell gives height
    z_below = grid.get_xyz(active_index=a_idx_below)[2]
    z_diff = abs(z_above - z_below)  # distance between cell centers

    owc = z_above + z_diff * norm_swat_ratio

    return owc


def findOwc(grid, owc_kw, x, y, z, thresh=0.7, owc_offset=0.5):
    """Given a grid, owc_kw, x, y, z, find the OWC Z s.t. owc_kw(x,y,Z)=thresh.

    This function returns a pair (owc, tvd) where owc is the approximate
    (linear interpolated) OWC for (x,y) and tvd is the lowest cell center
    above owc_exact - owc_offset.

    """

    col, idx = activeCellColumn(grid, owc_kw, x, y, z)
    if not col:
        raise ValueError(
            "Could not find cell column for (%.2f, %.2f, %.2f) in grid." % (x, y, z)
        )

    current_swat = -1
    # Called inv_k because it is inv_k = nz - k
    for inv_k in range(0, len(col)):
        if col[inv_k][3] >= 0:  #           x,y,z,a,s
            current_swat = col[inv_k][4]  #       ^ ^
            break
    # inv_k is first active index from below.
    if current_swat < 0:
        raise ValueError("No active cell in column for (%.2f,%.2f,%.2f)" % (x, y, z))

    while current_swat >= (thresh + 0.0001):
        inv_k += 1
        if inv_k >= len(col):
            raise ValueError("No OWC in column for (%.2f,%.2f,%.2f)" % (x, y, z))
        current_swat = col[inv_k][4]

    a_idx = col[inv_k][3]  # col[idx] contains x,y,z,a,s
    cell_center = grid.get_xyz(active_index=a_idx)[2]  # the z value of cell center

    if inv_k > 0:
        owc_exact = interpolate(grid, inv_k, col, thresh)
    else:
        owc_exact = grid.get_xyz(active_index=a_idx)[2]

    # snap to first cell center above 'owc_exact - owc_offset'
    while (owc_exact - owc_offset) < cell_center:
        inv_k += 1
        if inv_k >= len(col):
            break
        a_idx = col[inv_k][3]  # col[idx] contains x,y,z,a,s
        cell_center = grid.get_xyz(active_index=a_idx)[2]

    return (owc_exact, cell_center)


def snap(
    wp,
    grid,
    rest,
    init,
    date,
    owc_offset=0.5,
    keywords=None,
    delta=Inf,
    owc_definition=("SWAT", 0.7),
):
    """Given a WellPath wp, an EclGrid grid, an EclFile (restart file) rest, and a
    datetime date, we snap the WellPath wp to fit OWC - offset, where OWC is
    defined as min z st. SWAT(z)<=0.7.

    Keywords is a collection of columns we want to add to wp.  Possible
    keywords include 'LENGTH', 'TVD_DIFF', 'OLD_TVD', 'OWC', 'PERMX', 'SWAT',
    'SGAS', and 'SOIL'.  Functionality must be added to add more keywords.

    The delta property is to set the max inclination.  Setting delta=0.03
    makes wellpath not ascend or descend more than 3 meters per 100 meters.
    This is referred to as dogleg inclination.

    The owc_definition property is normally ('SWAT', 0.7), but can be things
    like ('SGAS', 0.1) and similar.  The first value should be a restart
    keyword and the second a valid number in the range of that keyword.

    The date we use is the last restart step before the given date.

    """

    permx_kw = None
    if init:
        permx_kw = init.iget_named_kw("PERMX", 0)  # step 0 -- INIT has only 1 step
    else:
        if "PERMX" in keywords:
            doprint("WARNING: PERMX requested, but no INIT.  Ignoring keyword PERMX")
            keywords = [kw for kw in keywords if kw != "PERMX"]

    c_owc_offset = wp.owcOffset()
    if c_owc_offset is None:
        c_owc_offset = owc_offset
    else:
        print("     \t Overriding global OWC_OFFSET.  Using value %.2f" % c_owc_offset)

    c_owc_definition = wp.owcDefinition()
    if c_owc_definition is None:
        c_owc_definition = owc_definition[1]
    else:
        print(
            "     \t Overriding global OWC_DEFINITION.  Using value %.2f"
            % c_owc_definition
        )

    # pick out swat/sgas/etc info for given step
    owc_kw = findKeyword(owc_definition[0], rest, date)

    logs = {
        "TVD_DIFF": [],  # TVD_DIFF
        "OLD_TVD": [],  # OLD_TVD
        "PERMX": [],  # PERMX --- if INIT file is specified
        "OWC": [],  # OWC --- Approximate OWC for given (x,y)
        "LENGTH": [],  # XY-length from previous wellpoint (2D)
        "SWAT": [],  # SWAT of result
        "SGAS": [],  # SGAS of result
        "SOIL": [],
    }  # 1 - (SGAS+SWAT)

    snap_mode = False  # set to true below when we start optimizing more
    #                   specifically, set to true when three points in the input
    #                   has had the same z-value in the input data.  This should
    #                   kindof imply that we are in a well-completion stage

    swat = None
    sgas = None
    if "SWAT" in keywords or "SOIL" in keywords:
        swat = findKeyword("SWAT", rest, date)
    if "SGAS" in keywords or "SOIL" in keywords:
        sgas = findKeyword("SGAS", rest, date)

    snapped_idx = 0
    for idx in range(len(wp)):
        point = wp[idx]
        x = point[0]
        y = point[1]
        z = point[2]
        logs["OLD_TVD"].append(z)
        new_tvd = z
        owc_exact = Nan
        z_range = (-Inf, Inf)

        # Ready to enter snap mode?
        new_mode = enterSnapMode(snap_mode, wp, idx)
        if new_mode and not snap_mode:
            print("Enabling snap mode at point %d (depth %.2f)" % (idx, wp[idx][2]))
            print(
                "                      %s %f" % (str(wp.depthType()), wp.windowDepth())
            )
            snap_mode = new_mode

        #
        # Step 1.  If snap mode, find owc_exact (interpolated) and let
        #          new_tvd=owc_exact-owc_offset.  This is the point at which we
        #          potentially want to put the well (eg 0.5m above owc_exact).
        #
        if snap_mode:
            snapped_idx += 1
            try:
                # findOwc returns owc, cell_column and index (in col) of cell
                owc_exact, new_tvd = findOwc(
                    grid,
                    owc_kw,
                    x,
                    y,
                    z,
                    thresh=c_owc_definition,
                    owc_offset=c_owc_offset,
                )
            except ValueError as err:
                doprint("Warning: %s" % err)

        #
        # Step 2.  If this is not the first point of the well, and we are
        #          adjusting the wellpoint, we must take care to respect delta,
        #          i.e., the increase/decrease in height (owc) cannot be higher
        #          than the (x,y) distances times delta.
        #
        if snap_mode and idx > 1:  # caring about delta at this point
            prev_wp = wp[idx - 1]
            x2, y2 = prev_wp[0], prev_wp[1]
            d = dist(
                (x, y), (x2, y2)
            )  # the projected distance between prev point and this
            prev_z = prev_wp[2]
            if snapped_idx > 1:
                zp = prev_z + d * delta  # previous z plus  max elevation
                zm = prev_z - d * delta  # previous z minus max elevation
                z_range = (min(zp, zm), max(zp, zm))
            new_tvd = roundAwayFromEven(min(max(new_tvd, z_range[0]), z_range[1]))

        diff = abs(z - new_tvd)
        if diff > 100:
            doprint(
                "Warning: Observed a vertical adjustment of %d m.  Ignoring."
                % int(diff)
            )
            new_tvd = z
            diff = 0

        ### END OF WELLPOINT ITERATIONS ###

        # Now we add this row's values on to the columns: perm, owc, length, old_tvd, diff etc.
        logs["TVD_DIFF"].append(new_tvd - z)
        wp[idx] = (x, y, new_tvd)
        i, j, k = _ijk(grid, x, y, new_tvd)
        new_cell = _activeIdx(grid, i, j, k)  # Active index of (i,j,k), or -1

        if new_cell < 0 and snap_mode:
            doprint(
                "Warning:  Suggested wellpoint inactive.  (%d,%d,%d)\t->\t(%.1f, %.1f, %.1f)"
                % (i, j, k, x, y, new_tvd)
            )
        permx = Nan
        if permx_kw and new_cell >= 0:
            permx = permx_kw[new_cell]
        logs["PERMX"].append(permx)

        # SWAT, SGAS, SOIL
        swat_val, sgas_val, soil_val = Nan, Nan, Nan
        if "SWAT" in keywords and new_cell >= 0:
            swat_val = swat[new_cell]
        logs["SWAT"].append(swat_val)

        if "SGAS" in keywords and new_cell >= 0:
            sgas_val = sgas[new_cell]
        logs["SGAS"].append(sgas_val)

        if "SOIL" in keywords and new_cell >= 0:
            soil_val = swat[new_cell] + sgas[new_cell]
        logs["SOIL"].append(1 - soil_val)

        logs["OWC"].append(owc_exact)
        if idx > 0:
            prev_wp = wp[idx - 1]
            x2, y2, z2 = prev_wp[0], prev_wp[1], prev_wp[2]
            length = dist((x, y), (x2, y2))
            logs["LENGTH"].append(length)
            if "MD" in wp.headers() and snap_mode:
                true_length = dist((x, y, new_tvd), (x2, y2, z2))
                prev_md = wp["MD"][idx - 1]
                new_md = prev_md + true_length
                wp["MD"][idx] = new_md
        else:
            logs["LENGTH"].append(0)

    recognized_kw = (
        "LENGTH",
        "TVD_DIFF",
        "OLD_TVD",
        "OWC",
        "PERMX",
        "SWAT",
        "SGAS",
        "SOIL",
    )
    for kw in keywords:
        if kw in recognized_kw:
            wp.addColumn(kw, logs[kw])
        else:
            doprint('Warning: Unrecognized keyword "%s".  Ignoring' % kw)
    doprint("")

    return wp
