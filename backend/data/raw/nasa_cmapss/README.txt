NASA CMAPSS FD001 — Synthetic Dataset (generated)
====================================================

This dataset mimics the NASA CMAPSS Turbofan Engine Degradation Simulation
dataset (FD001 subset).  It was generated programmatically for development
and testing purposes.

For the real dataset visit:
    https://www.kaggle.com/datasets/behrad3d/nasa-cmaps

------------------------------------------------------------------------
File descriptions
------------------------------------------------------------------------
train_FD001.txt  : Training set. Run-to-failure sequences for 20 engines.
test_FD001.txt   : Test set. Truncated sequences (engines not yet failed).
RUL_FD001.txt    : True Remaining Useful Life at the last test observation.

------------------------------------------------------------------------
Column layout (space-delimited, no header, 26 columns)
------------------------------------------------------------------------
Col  Name         Description
---  -----------  -------------------------------------------------------
  0  unit_id      Engine unit number (1-20)
  1  cycle        Operational cycle (starts at 1)
  2  setting1     Altitude (FD001: always 0.0)
  3  setting2     Mach number (FD001: always 0.0000)
  4  setting3     TRA (FD001: always 100.0)
  5  T2           Total temperature at fan inlet (degR)           — stable
  6  T24          Total temperature at LPC outlet (degR)          — stable
  7  T30          Total temperature at HPC outlet (degR)          — INCREASES
  8  T50          Total temperature at LPT outlet (degR)          — INCREASES
  9  P2           Pressure at fan inlet (psia)                    — stable
 10  P15          Total pressure in bypass-duct (psia)            — stable
 11  P30          Total pressure at HPC outlet (psia)             — DECREASES
 12  Nf           Physical fan speed (rpm)                        — stable
 13  Nc           Physical core speed (rpm)                       — stable
 14  epr          Engine pressure ratio (P50/P2)                  — stable
 15  Ps30         Static pressure at HPC outlet (psia)            — DECREASES
 16  phi          Ratio of fuel flow to Ps30 (pps/psi)            — INCREASES
 17  NRf          Corrected fan speed (rpm)                       — stable
 18  NRc          Corrected core speed (rpm)                      — stable
 19  BPR          Bypass ratio                                    — DECREASES
 20  farB         Burner fuel-air ratio                           — stable
 21  htBleed      Bleed enthalpy (BTU/s)                          — DECREASES
 22  Nf_dmd       Demanded fan speed (rpm)                        — static
 23  PCNfR_dmd    Demanded corrected fan speed (%)                — static
 24  W31          HPT coolant bleed flow (lbm/s)                  — DECREASES
 25  W32          LPT coolant bleed flow (lbm/s)                  — DECREASES

------------------------------------------------------------------------
Fault mode: HPC degradation (single fault, FD001)
------------------------------------------------------------------------
Sensors showing clear degradation trend:
  T30  (+50 over lifetime)    T50  (+80)
  P30  (-30)                  Ps30 (-3)
  phi  (+20)                  BPR  (-0.5)
  htBleed (-20)               W31  (-3)    W32 (-1.5)

Special engines:
  Engine-05 : max 220 cycles, accelerated degradation from cycle 50 (bearing)
  Engine-15 : max 180 cycles, critical bearing failure, fast from cycle 30
