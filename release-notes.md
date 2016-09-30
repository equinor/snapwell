# Version 1.0.0 (2016-09-16)

PO confirms snapwell is stable enough to be called 1.0.

This is version 0.9.1 with a new name.

# Version 0.9.1 (2016-09-12)

Output the correct MD value.

General code cleanup.

Updated documentation and this file.

MR: !382 !383

JIRA:RES-23, JIRA:RES-25

# Version 0.9 (2016-09-09)

This release should be considered as an alpha version of 1.0.  Once we get a
green light from PO, we will bump the version to snapwell 1.0, and call it
stable.

Improved command line usage with argparse.  Can now use

    snapwell --owc_definition SWAT:0.65 --owc_offset 0.15 --delta 0.0167 --output ~/myfolder ~/statoil/myconf.sc

where
 * `--owc_definition` (or `-f`) set to `SWAT:0.65` means that the definition of
   OWC is the lowest point where the SWAT value goes from _above_ 0.65 to
   _below_ 0.65.
 * `--owc_offset` (or `-z`) is the vertical offset (in meters) _above_ OWC we
   want to put the wellpoint.  Set to 0.15 means that we aim the wellpoint
   towards the first cell center above OWC - offset. (Minus means up.)
* `--delta` (or `-d`) means the dogleg restrictions (in m/m).  Set to 0.0167, it
  means we can differ in TVD 0.5 meters per 30 meters in length difference (see
  `LOG LENGTH`)

Adding `-w` means we overwrite existing files if necessary.  The flag `-r` means
output ResInsight compatible files.  In this case, we ignore all `LOG` keywords
provided and output only `WELLNAME` and then `X`, `Y`, `TVD`, and `MD` for each
wellpoint.

With that feature, one can run parallell instance with one config file, e.g.

    snapwell -z 0.0 -o ~/snap0 myconf.sc
    snapwell -z 0.2 -o ~/snap2 myconf.sc
    snapwell -z 0.5 -o ~/snap5 myconf.sc

which would run Snapwell with `owc_owffset=0.0, 0.2, 0.5`, respectively, and
output the files to different folders, `~/snap0`, `~/snap2`, and `~/snap5`,
respectively.

MR: !373 !380

JIRA:RES-18


# Version 0.8.3

Some bug fixes and improvements.

Update RKB values to be x,y,md-tvd for the first row (see issue #7)

Can now output columns SWAT, SGAS, SOIL (with LOG keyword).

MR: !375.

JIRA:RES-20, JIRA:RES-21


# Version 0.8.2

Wellpath aims towards first cell center above OWC+OWC_OFFSET, where OWC is
defined in config file (default SWAT 0.7).

If a user wants to have the first (lowest) "oil cell", one should use
OWC_OFFSET=0 in the config file.

JIRA:RES-16--RES-17


# Version 0.8.1

Bug fix for nan-values.

ert/ert-statoil:#6 https://git.statoil.no/ert/ert-statoil/issues/6


# Version 0.8.0 (2016-08-30)

Use LOG keywords to optionally add colums to output.
Supported keywords are:

    LOG LENGTH
    LOG TVD_DIFF
    LOG OLD_TVD
    LOG OWC
    LOG PERMX

JIRA:RES-11



# Version 0.7.4

Start searching for OWC at bottom.  Fixed interpolation algorithm.

JIRA:RES-14

# Version 0.7.3

Fixed bugs in snap algorithm, use 2D distance (not 3D) for calculating length.

# Version 0.7.2

Added WINDOW_DEPTH to config.  See readme for usage.

JIRA:RES-12

# Version 0.7.1

Removed cell center logic (viz meeting 2016-08-25 with Mathias)

Wells snap to thresh-owc_offset (owc=0.7 - 0.5m by default), unless we are close
to an even integer, in which case, we round about 0.1m away.

JIRA:RES-13.


# Version 0.7 (2016-08-23)
First trial version.  This version is a minimal working snapwell application.

Parsing wellpaths and config file.
* Understands x,y,z, can add arbitrary columns to wellpaths
* Parsing of wellpaths, dates
* Parsing of output config as well as overwrite flag
* Parsing of OWC, OWC_OFFSET, DELTA_Z keywords

Visualizing wellpaths (reads config files as well)

Contains snapping feature and a first attempt on delta limits.

Contains a preliminary WINDOW_DEPTH keyword parsing.

JIRA:RES-1--RES-8.
