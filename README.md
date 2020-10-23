    Snapwell is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free
    Software Foundation, either version 3 of the License, or (at your option)
    any later version.

    Snapwell is distributed in the hope that it will be useful, but WITHOUT ANY
    WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE.

    See the GNU General Public License at <http://www.gnu.org/licenses/gpl.html>
    for more details.

# Installation and usage

Snappwell is available on [pypi](https://pypi.org/project/snapwell/) and can be
installed using `pip install snapwell`


# On snapwell

Snapwell is a project for depth optimizing wellpaths by changing the TVD
according to OWC.  What exactly defines OWC at a given (x,y)-coordinate can be
specified as number r between 0 and 1, and OWC is then the lowest point with
SWAT=r.  Future implementations might also take the permeability into account.

Changes in TVD are typically done by using a max increase of 0.5 m/30m to avoid
making vertical segments.

Should avoid putting the majority of the well path in cells with non producible
permeability.


# Fileformat
## snapwell input file
The filepath is relative to the config file, not the current working directory.

The config file is a yaml-file having the following format:

```yaml
grid_file: "NORNE_ATW2013.EGRID"
restart_file: "NORNE_ATW2013.UNRST"
init_file: "NORNE_ATW2013.INIT"

output_dir: "norne-mid"
overwrite: False
delta_z: 0.003
log_keywords: ["PERMX", "OWC", "TVD_DIFF"]

wellpath_files:
  - {well_file: "norne-test-1-mid.w", date: "1997-05-1"}
  - {well_file: "norne-test-2-mid.w", date: "1998-01-1"}

```

* Two keywords are mandatory, `grid_file` and `restart_file`, and should be followed by a
  path to the grid (GRID/EGRID) and restart files (UNRST), respectively (see
  example below).
* The `init_file` is required for permeability output, and should be
  a path to an init file.
* The following additional keywords are supported:
    * `output` --- the output directory (path), is set to cwd by default
    * `overwrite` --- a boolean (True/False) specifying whether the program is
      allowed to overwrite already existing files.  Defaulted to False; use with
      care.
    * `delta_z` --- the maximum elevation per 100 meters, given as a float.
      0.0167 is 0.5m/30m.
    * `owc_definition` --- The keyword used for saturation and threshold value used to determine owc

```yaml
owc_definition:
  keyword: "SWAT"
  value: 0.7
```

* `owc_offset` --- a number (eg. 0.5).  Will place the wellpoint 0.5m above OWC
* `log_keywords` --- list of values written to the well file:
   * `OWC` --- actual OWC for given date and (x,y) coordinate
   * `OLD_TVD` --- the old TVD specified in the input Wellpath
   * `DIFF` --- The difference between `OLD_TVD` and new `TVD`
   * `SWAT`, `SOIL`, `SGAS`, `PERMX` --- value in wellpoint cell for keyword
   * `LENGTH` --- the distance between this (x,y) coordinate and the previous
* `wellpath_files` --- list of files in the wellpath format
   * `well_file` --- path to the wellpath file
   * `date` --- `YYYY-MM-DD` The date to look up values for in the restart file.
   * `window_depth` --- The depth to start optimizing the well for.
   * `depth_type` --- Type of depth in the well file, either "MD" or "TVD".



## WellPath format (RMS well format)

The wellpath format is given as follows: (blank lines and lines starting with -- ignored)

    <version>
    <well type>
    <well name> <x> <y> <rkb>
    <number of well logs>
    <log name 1> <unit> <scale>
    ...
    <log name n> <unit> <scale>
    <x> <y> <z> <p1> ... <pn>
    ...
    <x> <y> <z> <p1> ... <pn>

An example is the following:

    1.0
    PRODUCTION
    TEST_WELL 1068.000 0.000 0.0000
    3
    MD 1 lin
    Incl 1 lin
    Az 1 lin
    1068.0    0.0    38.0    38.0    109.0    359.0
    1069.0    5.0    39.0    50.0    109.0    359.0

Here, the X, Y, and Z numbers are UTM* easting, UTM northing, UTM TVD (true
vertical depth), and then follow the three log parameters defined, MD, INC and
AZ, being measured_depth, inclination and azimuth.

We safely ignore all but the three first numbers in each row (actually, only x
and y are really interesting).

* UTM is Universal Transverse Mercator coordinate system

## Run tests
[tox](https://tox.readthedocs.io/en/latest/) is used as the test facilitator,
to run the full test suite:

```sh
# Test
pip install tox
tox
```

or to run it for a particular Python version (in this case Python 3.7):

```sh
# Test
pip install tox
tox -e py37
```

or to run it for a the current Python version on PATH:

```sh
# Test
pip install tox
tox -e py
```

[pytest](https://docs.pytest.org/en/latest/) is used as the test runner, so for quicker
iteration it is possible to run:

```sh
# Test
pytest
```

this requires that the `pytest` is installed.

```sh
# Install pytest
pip install pytest
```

[pre-commit](https://pre-commit.com/) is used to comply with the formatting standards.
The complete formatting tests can be run with:

```sh
pip install tox
tox -e style
```

See `.pre-commit-config.yaml` for the complete steps.

[pre-commit](https://pre-commit.com/) can also provide git hooks to run on every commit
to avoid commiting with formatting errors. This will only run on the diff so is quite fast.
To configure this, run:

```sh
pip install pre-commit
pre-commit install
```

After this the hook will run on every commit.

If you would like to remove the hooks, run:

```sh
pre-commit uninstall
```
