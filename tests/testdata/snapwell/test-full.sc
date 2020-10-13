GRID        ../eclipse/SPE3CASE1.EGRID
RESTART     ../eclipse/SPE3CASE1.UNRST
INIT        ../eclipse/SPE3CASE1.INIT

-- Writes the new wellpath to
OUTPUT      ../eclipse
OVERWRITE   True

OWC_OFFSET       0.88
DELTA_Z          0.55
OWC_DEFINITION SGAS 0.31415

LOG LENGTH
LOG TVD_DIFF
LOG OLD_TVD
LOG OWC
LOG PERMX


-- WELL     FILE NAME                 STARTUP DATE
WELLPATH    well.w                    2025-03-31
WELLPATH    well1.w                   2022-12-03      TVD 2000.00
WELLPATH    well2.w                   2025-03-31      MD   158.20
WELLPATH    well3.w                   2022-12-03      MD  1680
WELLPATH    well4.w                   2023-12-03      MD  1680           OWC_DEFINITION 0.71828
WELLPATH    well5.w                   2024-12-03      OWC_OFFSET 0.5115  OWC_DEFINITION 0.1828
WELLPATH    well6.w                   2025-12-03      OWC_OFFSET 0.115   OWC_DEFINITION 0.828 MD 1884
WELLPATH    well7.w                   2022            MD 4000 OWC_DEFINITION 0.0
