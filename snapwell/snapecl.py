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
from math import inf, nan, sqrt

from .snapconfig import OwcDefinition


def dist(p1, p2):
    """Returns Euclidean distance between p1 and p2, i.e. Pythagoras.
    Works on coordinates of any dimension.  If p1 and p2 have different
    dimensionality, we pick the min(len(p1), len(p2)) first points of each
    coordinate.
    """
    return sqrt(sum([(e[0] - e[1]) ** 2 for e in zip(p1, p2)]))


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
    """
    Finds the last restart step in the given restart file before the given date
    """
    # start at 1, since we return step - 1
    for step in range(1, restart.num_report_steps()):
        new_date = restart.iget_restart_sim_time(step).date()  # step date
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


def in_snap_mode(already_in_snap_mode, well_path, idx):
    """
    Checks whether snap mode is enabled for the well path at row with index idx.
    In snap mode means well path should be snapped to owc at that index.

    :returns: True if at the well path row at idx we are in snap mode.
    :param already_in_snap_mode: True if we are already in snap mode at row idx-1.
    :param well_path: The well path with rows.
    :param idx: The index of the row.

    Raises Value Error if the well path depth type is not set correctly.
    """
    if already_in_snap_mode or not well_path.depth_type:
        return True
    if well_path.depth_type not in well_path:
        raise ValueError(
            f"Well path {well_path} does not contain given depth type: {well_path.depth_type}"
        )

    return well_path[well_path.depth_type][idx] > well_path.window_depth


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


def active_cell_column(grid, owc_kw, x, y, z):
    """Let i,j,k be the cell containing x,y,z.  This function returns a list of
    the active cells in the (i,j)-column

        [(i,j,n_z,an_z,sn_z), (i,j,n_z-1,an_z-1,sn_z-1), ..., (i,j,0,a0,s0)],

    where n_z is the height of the grid, at is the active index of the t'th
    cell in the list and st its s owc_kw.

    In the case where there is no cell found containing xyz, this function
    will return [].

    """
    col = []

    i, j, _ = _ijk(grid, x, y, z)
    nz = grid.getNZ()
    for k_idx in range(nz - 1, -1, -1):  # backwards from nz-1 to 0
        a = _activeIdx(grid, i, j, k_idx)
        if a >= 0:
            s = owc_kw[a]
            col.append((i, j, k_idx, a, s))
    return col


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
    active_idx_below = col[k_below][3]
    active_idx_above = col[k_above][3]  # col contains cell from bottom and up

    swat_below = col[k_below][4]  # the SWAT/SGAS/etc in cell above and below OWC
    swat_above = col[k_above][4]

    norm_swat_above = swat_below - swat_above
    norm_swat_thresh = swat_below - thresh
    norm_swat_ratio = 1 - (norm_swat_thresh / norm_swat_above)

    # z coordinate of cell gives height
    z_above = grid.get_xyz(active_index=active_idx_above)[2]
    z_below = grid.get_xyz(active_index=active_idx_below)[2]
    z_diff = abs(z_above - z_below)  # distance between cell centers

    owc = z_above + z_diff * norm_swat_ratio

    return owc


def first_swat_below_treshold(column, threshold=0.7):
    """
    finds the first (i,j,k,a,swat) tuple with swat less than treshold.
    If there is no such tuple, returns None.
    :param column: List of (x,y,z,a,swat) tuples.
    """
    for idx, (_, _, _, _, swat) in enumerate(column):
        if swat < (threshold + 0.0001):
            return idx
    return None


def interpolate_owc(grid, col, k_above_owc, threshold=0.7):
    """
    This function returns  the approximate
    (linear interpolated) OWC for (x,y).

    :param col: List of (i,j,k,a,s) tuples to interpolate over.
    :param grid: The grid the column belongs to.
    :param k_above_owc:index of first cell whose center is above owc.
    """

    active_idx = col[k_above_owc][3]  # col[idx] contains x,y,z,a,s

    if k_above_owc > 0:
        return interpolate(grid, k_above_owc, col, threshold)

    return grid.get_xyz(active_index=active_idx)[2]


def find_center_z(grid, column, height):
    """
    Given list of (i,j,k,a,swat) tuples giving indecies of active cells in
    the grid. Returns the center point z value of a cell in the grid above the
    given height.  Returns None if cell center above the last column center
    """
    for (_, _, _, active_idx, _) in column:
        cell_center_height = grid.get_xyz(active_index=active_idx)[2]
        if height >= cell_center_height:
            return cell_center_height
    return None


def find_owc(grid, owc_kw, x, y, z, threshold=0.7, owc_offset=0.5):
    """Given a grid, owc_kw, x, y, z, find the OWC Z s.t. owc_kw(x,y,Z)=thresh."""
    col = active_cell_column(grid, owc_kw, x, y, z)
    if not col:
        logging.warning(
            "No active cell for %s at (%f, %f, %f), owc is nan", owc_kw, x, y, z
        )
        return nan, z
    threshold_idx = first_swat_below_treshold(col, threshold=threshold)
    if threshold_idx is None:
        logging.warning(
            "No active cell has swat below treshold for %s at (%f, %f, %f), owc is nan",
            owc_kw,
            x,
            y,
            z,
        )
        return nan, z
    # snap to first cell center above 'owc_exact - owc_offset'
    owc_exact = interpolate_owc(grid, col, threshold_idx, threshold=threshold)
    cell_center = find_center_z(grid, col, owc_exact - owc_offset)
    if cell_center is None:
        logging.warning(
            "Depth is above active cells for %s at (%f, %f, %f), using depth from last active cell",
            owc_kw,
            x,
            y,
            z,
        )
        return owc_exact, grid.get_xyz(active_index=col[-1][3])[2]

    return owc_exact, cell_center


def snap(
    well_path,
    grid,
    rest,
    date,
    owc_offset=0.5,
    permx_kw=None,
    keywords=None,
    delta=inf,
    owc_definition=None,
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
    if keywords is None:
        keywords = []
    c_owc_offset = well_path.owc_offset

    if owc_definition is None:
        owc_definition = OwcDefinition("SWAT", 0.7)

    if c_owc_offset is None:
        c_owc_offset = owc_offset
    else:
        logging.info("Overriding global OWC_OFFSET. Using value %.2f", c_owc_offset)

    if well_path.owc_definition is not None:
        c_owc_definition = well_path.owc_definition[1]
    else:
        c_owc_definition = owc_definition.value
        logging.info(
            "Overriding global OWC_DEFINITION. Using value %.2f",
            c_owc_definition,
        )

    # pick out swat/sgas/etc info for given step
    owc_kw = findKeyword(owc_definition.keyword, rest, date)

    logs = {
        "TVD_DIFF": [],  # TVD_DIFF
        "OLD_TVD": [],  # OLD_TVD
        "PERMX": [],  # PERMX --- if INIT file is specified
        "OWC": [],  # OWC --- Approximate OWC for given (x,y)
        "LENGTH": [],  # XY-length from previous wellpoint (2D)
        "SWAT": [],  # SWAT of result
        "SGAS": [],  # SGAS of result
        "SOIL": [],  # 1 - (SGAS+SWAT)
    }

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
    for idx, (x, y, z, *_) in enumerate(well_path):
        logs["OLD_TVD"].append(z)
        new_tvd = z
        owc_exact = nan
        z_range = (-inf, inf)

        # Ready to enter snap mode?
        new_mode = in_snap_mode(snap_mode, well_path, idx)
        if new_mode and not snap_mode:
            logging.info(
                f"Enabling snap mode at point {idx} (depth {z}), "
                f"depth type: {well_path.depth_type} window path: {well_path.window_depth}"
            )
            snap_mode = new_mode

        #
        # Step 1.  If snap mode, find owc_exact (interpolated) and let
        #          new_tvd=owc_exact-owc_offset.  This is the point at which we
        #          potentially want to put the well (eg 0.5m above owc_exact).
        #
        if snap_mode:
            snapped_idx += 1
            owc_exact, new_tvd = find_owc(
                grid,
                owc_kw,
                x,
                y,
                z,
                threshold=c_owc_definition,
                owc_offset=c_owc_offset,
            )

        #
        # Step 2.  If this is not the first point of the well, and we are
        #          adjusting the wellpoint, we must take care to respect delta,
        #          i.e., the increase/decrease in height (owc) cannot be higher
        #          than the (x,y) distances times delta.
        #
        if snap_mode and idx > 1:  # caring about delta at this point
            prev_wp = well_path[idx - 1]
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

        if abs(z - new_tvd) > 100:
            logging.warning(
                "Observed a vertical adjustment of %d m. Ignoring.", z - new_tvd
            )
            new_tvd = z

        # END OF WELLPOINT ITERATIONS

        # Now we add this row's values on to the columns: perm, owc, length, old_tvd, diff etc.
        logs["TVD_DIFF"].append(new_tvd - z)
        well_path[idx] = (x, y, new_tvd)
        i, j, k = _ijk(grid, x, y, new_tvd)
        new_cell = _activeIdx(grid, i, j, k)  # Active index of (i,j,k), or -1

        if new_cell < 0 and snap_mode:
            logging.warning(
                "Suggested wellpoint inactive.  (%d,%d,%d)\t->\t(%.1f, %.1f, %.1f)",
                i,
                j,
                k,
                x,
                y,
                new_tvd,
            )
        permx = nan
        if permx_kw and new_cell >= 0:
            permx = permx_kw[new_cell]
        logs["PERMX"].append(permx)

        # SWAT, SGAS, SOIL
        swat_val, sgas_val, soil_val = nan, nan, nan
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
            prev_wp = well_path[idx - 1]
            x2, y2, z2 = prev_wp[0], prev_wp[1], prev_wp[2]
            length = dist((x, y), (x2, y2))
            logs["LENGTH"].append(length)
            if "MD" in well_path.headers and snap_mode:
                true_length = dist((x, y, new_tvd), (x2, y2, z2))
                prev_md = well_path["MD"][idx - 1]
                new_md = prev_md + true_length
                well_path["MD"][idx] = new_md
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
            well_path.add_column(kw, logs[kw])
        else:
            logging.warning('Unrecognized keyword "%s".  Ignoring', kw)

    return well_path
