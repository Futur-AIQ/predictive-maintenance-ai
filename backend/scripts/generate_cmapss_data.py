#!/usr/bin/env python
"""
Generate realistic synthetic NASA CMAPSS FD001-style data.

Produces:
    data/raw/nasa_cmapss/train_FD001.txt   — 20 engines, full run-to-failure
    data/raw/nasa_cmapss/test_FD001.txt    — 20 engines, truncated sequences
    data/raw/nasa_cmapss/RUL_FD001.txt     — true RUL for each test engine
    data/raw/nasa_cmapss/README.txt        — column description

FD001 operating condition: single (sea-level, Mach 0, TRA 100).
Fault mode: HPC (High-Pressure Compressor) degradation.

Usage:
    python scripts/generate_cmapss_data.py
"""

import os
import random
import numpy as np

# Global seed for reproducibility
np.random.seed(42)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "raw", "nasa_cmapss")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
N_ENGINES = 20

# Sensor baseline values (FD001 sea-level, Mach 0, TRA 100)
BASELINES = {
    "s1":  445.00,   # T2        — no degradation
    "s2":  642.40,   # T24       — no degradation
    "s3":  1589.00,  # T30       — INCREASES with HPC degradation
    "s4":  1400.00,  # T50       — INCREASES
    "s5":  14.62,    # P2        — no degradation
    "s6":  21.60,    # P15       — no degradation
    "s7":  553.40,   # P30       — DECREASES
    "s8":  2388.00,  # Nf        — no degradation
    "s9":  9047.00,  # Nc        — no degradation
    "s10": 1.30,     # epr       — no degradation
    "s11": 47.50,    # Ps30      — DECREASES
    "s12": 521.50,   # phi       — INCREASES
    "s13": 2388.00,  # NRf       — no degradation
    "s14": 8138.00,  # NRc       — no degradation
    "s15": 8.45,     # BPR       — DECREASES
    "s16": 0.03,     # farB      — no degradation
    "s17": 393.00,   # htBleed   — DECREASES
    "s18": 2388.00,  # Nf_dmd    — static, no noise
    "s19": 100.00,   # PCNfR_dmd — static, no noise
    "s20": 39.00,    # W31       — DECREASES
    "s21": 23.00,    # W32       — DECREASES
}

# Noise standard deviations (0 = no noise / static)
NOISE_STD = {
    "s1":  1.0,
    "s2":  0.5,
    "s3":  5.0,
    "s4":  8.0,
    "s5":  0.01,
    "s6":  0.1,
    "s7":  1.0,
    "s8":  5.0,
    "s9":  5.0,
    "s10": 0.001,
    "s11": 0.2,
    "s12": 2.0,
    "s13": 5.0,
    "s14": 10.0,
    "s15": 0.05,
    "s16": 0.001,
    "s17": 2.0,
    "s18": 0.0,   # static
    "s19": 0.0,   # static
    "s20": 0.3,
    "s21": 0.2,
}

# Maximum degradation change at failure (signed)
MAX_CHANGE = {
    "s3":  +50.0,   # T30  increases
    "s4":  +80.0,   # T50  increases
    "s7":  -30.0,   # P30  decreases
    "s11": -3.0,    # Ps30 decreases
    "s12": +20.0,   # phi  increases
    "s15": -0.5,    # BPR  decreases
    "s17": -20.0,   # htBleed decreases
    "s20": -3.0,    # W31  decreases
    "s21": -1.5,    # W32  decreases
}

# Sensors with no degradation trend
NO_DEGRADATION = {"s1", "s2", "s5", "s6", "s8", "s9", "s10", "s13", "s14", "s16", "s18", "s19"}

# FD001: single operating condition (sea-level)
SETTING1 = 0.0
SETTING2 = 0.0000
SETTING3 = 100.0

# Special engines
SPECIAL_ENGINES = {
    5:  {"max_cycles": 220, "deg_start_cycle": 50,  "note": "accelerated early degradation (bearing)"},
    15: {"max_cycles": 180, "deg_start_cycle": 30,  "note": "critical bearing failure, fast degradation"},
}


# ---------------------------------------------------------------------------
# Engine generation
# ---------------------------------------------------------------------------

def get_max_cycles(unit_id: int) -> int:
    """Determine max_cycles for a given unit_id (1-based)."""
    if unit_id in SPECIAL_ENGINES:
        return SPECIAL_ENGINES[unit_id]["max_cycles"]
    rng = random.Random(unit_id * 42)
    return rng.randint(150, 350)


def compute_degradation_factor(cycle: int, max_cycles: int, unit_id: int) -> float:
    """
    Compute degradation factor in [0, 1] for a given cycle.

    Special engines degrade faster from an earlier start cycle.
    Standard engines degrade linearly from cycle 1.
    """
    if unit_id in SPECIAL_ENGINES:
        deg_start = SPECIAL_ENGINES[unit_id]["deg_start_cycle"]
        if cycle <= deg_start:
            return 0.0
        effective_cycles = max_cycles - deg_start
        return min(1.0, (cycle - deg_start) / effective_cycles)
    # Standard linear degradation
    return min(1.0, cycle / max_cycles)


def generate_engine_cycles(unit_id: int, max_cycles: int) -> list:
    """
    Generate all cycle rows for one engine as a list of lists.

    Each row: [unit_id, cycle, setting1, setting2, setting3, s1..s21]
    """
    rows = []
    rng = np.random.default_rng(seed=unit_id * 1000)  # per-engine RNG for reproducibility

    for cycle in range(1, max_cycles + 1):
        deg = compute_degradation_factor(cycle, max_cycles, unit_id)

        row = [unit_id, cycle, SETTING1, SETTING2, SETTING3]

        for sensor in [f"s{i}" for i in range(1, 22)]:
            baseline = BASELINES[sensor]
            noise_std = NOISE_STD[sensor]

            if sensor in NO_DEGRADATION:
                noise = rng.normal(0, noise_std) if noise_std > 0 else 0.0
                value = baseline + noise
            else:
                trend = deg * MAX_CHANGE[sensor]
                noise = rng.normal(0, noise_std) if noise_std > 0 else 0.0
                value = baseline + trend + noise

            row.append(value)

        rows.append(row)

    return rows


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_row(row: list) -> str:
    """
    Format a data row into the CMAPSS space-delimited string.

    Columns:
        0  : unit_id  — integer
        1  : cycle    — integer
        2  : setting1 — %.1f
        3  : setting2 — %.4f
        4  : setting3 — %.1f
        5+  : sensors — %.2f  (s18/s19 are integer-like but printed %.2f)
    """
    parts = []
    parts.append(str(int(row[0])))          # unit_id
    parts.append(str(int(row[1])))          # cycle
    parts.append(f"{row[2]:.1f}")           # setting1
    parts.append(f"{row[3]:.4f}")           # setting2
    parts.append(f"{row[4]:.1f}")           # setting3
    for val in row[5:]:
        parts.append(f"{val:.2f}")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# README content
# ---------------------------------------------------------------------------

README_CONTENT = """NASA CMAPSS FD001 — Synthetic Dataset (generated)
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
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Generating synthetic CMAPSS FD001 data in: {OUTPUT_DIR}")

    train_rows_all = []
    test_rows_all = []
    rul_values = []

    for unit_id in range(1, N_ENGINES + 1):
        max_cycles = get_max_cycles(unit_id)
        all_rows = generate_engine_cycles(unit_id, max_cycles)

        # Training: full run-to-failure
        train_rows_all.extend(all_rows)

        # Test: truncate to represent engines at various lifecycle stages
        rng_trunc = random.Random(unit_id * 99 + 7)
        if unit_id in SPECIAL_ENGINES:
            # Special bearing-fault engines: force near end-of-life (CRITICAL)
            truncation_point = max(max_cycles - 20, max_cycles // 2)
        else:
            # Spread truncation across full lifecycle (12% - 92%) for health variety
            trunc_min = max(1, max_cycles // 8)
            trunc_max = max(trunc_min + 5, max_cycles - int(max_cycles * 0.08))
            truncation_point = rng_trunc.randint(trunc_min, trunc_max)

        test_rows = all_rows[:truncation_point]
        test_rows_all.extend(test_rows)

        true_rul = max_cycles - truncation_point
        rul_values.append(true_rul)

        print(
            f"  Engine-{unit_id:02d}: max_cycles={max_cycles:3d}, "
            f"test_truncated_at={truncation_point:3d}, RUL={true_rul:3d}"
        )

    # Write train_FD001.txt
    train_path = os.path.join(OUTPUT_DIR, "train_FD001.txt")
    with open(train_path, "w") as f:
        for row in train_rows_all:
            f.write(format_row(row) + "\n")
    print(f"\nWrote {len(train_rows_all):,} rows -> {train_path}")

    # Write test_FD001.txt
    test_path = os.path.join(OUTPUT_DIR, "test_FD001.txt")
    with open(test_path, "w") as f:
        for row in test_rows_all:
            f.write(format_row(row) + "\n")
    print(f"Wrote {len(test_rows_all):,} rows -> {test_path}")

    # Write RUL_FD001.txt
    rul_path = os.path.join(OUTPUT_DIR, "RUL_FD001.txt")
    with open(rul_path, "w") as f:
        for rul in rul_values:
            f.write(f"{rul}\n")
    print(f"Wrote {len(rul_values)} RUL values -> {rul_path}")

    # Write README
    readme_path = os.path.join(OUTPUT_DIR, "README.txt")
    with open(readme_path, "w") as f:
        f.write(README_CONTENT)
    print(f"Wrote README -> {readme_path}")

    print("\nDone. Summary:")
    print(f"  Train rows : {len(train_rows_all):,}")
    print(f"  Test rows  : {len(test_rows_all):,}")
    print(f"  Engines    : {N_ENGINES}")


if __name__ == "__main__":
    main()
