GRID                  /d/proj/bg/enkf/ErtTestData/ECLIPSE/Norne/reservoir_models/Norne_ATW2013/NORNE_ATW2013.EGRID
RESTART               /d/proj/bg/enkf/ErtTestData/ECLIPSE/Norne/reservoir_models/Norne_ATW2013/NORNE_ATW2013.UNRST
INIT                  /d/proj/bg/enkf/ErtTestData/ECLIPSE/Norne/reservoir_models/Norne_ATW2013/NORNE_ATW2013.INIT

OUTPUT                ../norne-prod-out
OVERWRITE             True
DELTA_Z               0.0167
LOG                   TVD_DIFF
LOG                   OWC

LOG SWAT
LOG SGAS
LOG SOIL

OWC_OFFSET            0.0
OWC_DEFINITION        SWAT    0.7


-- WELL  FILE         NAME STARTUP DATE
WELLPATH norne-prod.w 2001-09-01
