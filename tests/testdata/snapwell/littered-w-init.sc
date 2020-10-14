-- tst
 --- lol
  --- aha
-- jaja

-- the old

--  this is the old GRID FILE:  bbl.grid

GRID grid.EGRID

-- here is the restart file:

RESTART a_restart_file.UNRST

 -- we have init in this file
 INIT ../eclipse/SPE3CASE1.INIT
-- here comes the wellpath files specificications

  --- the format is:

--FILENAME       DATETIME
WELLPATH well.w        2022
--WELLPATH well1.w     2016-05
WELLPATH well1.w       2019-05
-- WELLPATH well2.w       2015
-- WELLPATH well3.w       2015
-- WELLPATH well4-xxx.w   2015-04-30
