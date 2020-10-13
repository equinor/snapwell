GRID           NORNE_ATW2013.EGRID
RESTART        NORNE_ATW2013.UNRST
INIT           NORNE_ATW2013.INIT

OUTPUT         norne-mid
OVERWRITE      False
DELTA_Z        0.003
LOG            PERMX
LOG            OWC
LOG            TVD_DIFF

--WELLPATH     FILE_NAME          STARTUP_DATE
WELLPATH       norne-test-1-mid.w 1997-05
WELLPATH       norne-test-2-mid.w 1998-01
