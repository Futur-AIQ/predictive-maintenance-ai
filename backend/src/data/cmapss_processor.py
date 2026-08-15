import os
import sys
import numpy as np
import pandas as pd
from typing import Dict, Optional
from dataclasses import dataclass
from loguru import logger


SENSOR_COLS = [
    "T2", "T24", "T30", "T50", "P2", "P15", "P30",
    "Nf", "Nc", "epr", "Ps30", "phi", "NRf", "NRc",
    "BPR", "farB", "htBleed", "Nf_dmd", "PCNfR_dmd",
    "W31", "W32"
]

ALL_COLS = ["unit_id", "cycle", "setting1", "setting2", "setting3"] + SENSOR_COLS


@dataclass
class EngineSnapshot:
    unit_id: int
    equipment_id: str           # "Engine-01" etc.
    current_cycle: int
    max_cycle: int
    rul: int                    # true RUL from RUL_FD001.txt
    health_score: float         # 0-100
    status: str                 # OK / WARNING / CRITICAL
    sensor_readings: dict       # dict of sensor_name -> last_value


class CMAPSSProcessor:
    """
    Loads and processes NASA CMAPSS FD001 data.

    Uses the TEST set (truncated sequences representing engines still running)
    with ground-truth RUL from RUL_FD001.txt, giving realistic mid-lifecycle
    snapshots rather than end-of-life failure points.

    health_score = 100 * (rul / max_cycle), clamped to [0, 100].
    Status thresholds: CRITICAL < 30, WARNING < 60, OK >= 60.
    """

    def __init__(self, data_dir: str = "./data/raw/nasa_cmapss"):
        self.data_dir = data_dir
        self._snapshots: Dict[int, EngineSnapshot] = {}
        self._loaded = False

    def load(self) -> None:
        """Load and process the FD001 data. Idempotent."""
        if self._loaded:
            return

        train_path = os.path.join(self.data_dir, "train_FD001.txt")

        if not os.path.exists(train_path):
            logger.warning(
                f"CMAPSS data not found at {train_path}. Generating synthetic data..."
            )
            self._generate_synthetic()

        test_path = os.path.join(self.data_dir, "test_FD001.txt")
        rul_path = os.path.join(self.data_dir, "RUL_FD001.txt")

        if os.path.exists(test_path) and os.path.exists(rul_path):
            self._load_test_data(train_path, test_path, rul_path)
        else:
            # Fallback: use training data end-of-life snapshots
            self._load_train_data(train_path)

    def _generate_synthetic(self) -> None:
        """Generate synthetic CMAPSS data if real data is unavailable."""
        os.makedirs(self.data_dir, exist_ok=True)
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "scripts", "generate_cmapss_data.py"
        )
        if os.path.exists(script_path):
            import subprocess
            subprocess.run([sys.executable, script_path], check=True)
        else:
            logger.error("Cannot generate synthetic CMAPSS data: script not found")

    def _parse_file(self, path: str) -> pd.DataFrame:
        """Parse a space-delimited CMAPSS file into a DataFrame."""
        df = pd.read_csv(path, sep=" ", header=None, names=ALL_COLS)
        # Drop any trailing NaN columns (CMAPSS files sometimes have trailing spaces)
        df = df.dropna(axis=1, how="all")
        df.columns = ALL_COLS[: len(df.columns)]
        return df

    def _load_test_data(
        self, train_path: str, test_path: str, rul_path: str
    ) -> None:
        """
        Load engine snapshots from the TEST set for realistic mid-lifecycle state.

        - max_cycle per engine comes from training data (full run-to-failure).
        - current sensor readings come from the last row of each test sequence.
        - true RUL comes from RUL_FD001.txt.
        """
        # 1. Training data → max cycle per engine
        train_df = self._parse_file(train_path)
        max_cycles_by_unit: Dict[int, int] = (
            train_df.groupby("unit_id")["cycle"].max().astype(int).to_dict()
        )

        # 2. Test data → last observed row per engine
        test_df = self._parse_file(test_path)

        # 3. True RUL per engine (one value per line)
        with open(rul_path) as f:
            rul_values = [int(line.strip()) for line in f if line.strip()]

        loaded = 0
        for idx, (unit_id, group) in enumerate(test_df.groupby("unit_id")):
            unit_id = int(unit_id)
            group = group.sort_values("cycle")
            last_row = group.iloc[-1]
            current_cycle = int(last_row["cycle"])

            max_cycle = max_cycles_by_unit.get(unit_id, current_cycle)
            rul = rul_values[idx] if idx < len(rul_values) else 0

            health_score = (
                round(100.0 * rul / max_cycle, 1) if max_cycle > 0 else 0.0
            )
            health_score = max(0.0, min(100.0, health_score))

            if health_score < 30:
                status = "CRITICAL"
            elif health_score < 60:
                status = "WARNING"
            else:
                status = "OK"

            sensor_readings = {}
            for col in SENSOR_COLS:
                if col in last_row.index:
                    sensor_readings[col] = round(float(last_row[col]), 4)

            equipment_id = f"Engine-{unit_id:02d}"
            self._snapshots[unit_id] = EngineSnapshot(
                unit_id=unit_id,
                equipment_id=equipment_id,
                current_cycle=current_cycle,
                max_cycle=max_cycle,
                rul=rul,
                health_score=health_score,
                status=status,
                sensor_readings=sensor_readings,
            )
            loaded += 1

        self._loaded = True
        logger.info(
            f"CMAPSS data loaded: {loaded} engines from test set ({test_path})"
        )

    def _load_train_data(self, train_path: str) -> None:
        """
        Fallback: load end-of-life snapshots from training data.
        Uses second-to-last cycle as current state.
        """
        train_df = self._parse_file(train_path)

        for unit_id, group in train_df.groupby("unit_id"):
            unit_id = int(unit_id)
            group = group.sort_values("cycle")
            max_cycle = int(group["cycle"].max())
            current_cycle = max_cycle
            rul = 0

            if len(group) > 1:
                second_to_last = group.iloc[-2]
                current_cycle = int(second_to_last["cycle"])
                rul = max_cycle - current_cycle

            health_score = (
                round(100.0 * rul / max_cycle, 1) if max_cycle > 0 else 0.0
            )
            health_score = max(0.0, min(100.0, health_score))

            if health_score < 30:
                status = "CRITICAL"
            elif health_score < 60:
                status = "WARNING"
            else:
                status = "OK"

            last_row = group.iloc[-1]
            sensor_readings = {}
            for col in SENSOR_COLS:
                if col in last_row.index:
                    sensor_readings[col] = round(float(last_row[col]), 4)

            equipment_id = f"Engine-{unit_id:02d}"
            self._snapshots[unit_id] = EngineSnapshot(
                unit_id=unit_id,
                equipment_id=equipment_id,
                current_cycle=current_cycle,
                max_cycle=max_cycle,
                rul=rul,
                health_score=health_score,
                status=status,
                sensor_readings=sensor_readings,
            )

        self._loaded = True
        logger.info(
            f"CMAPSS data loaded (train fallback): {len(self._snapshots)} engines"
        )

    def get_snapshot(self, equipment_id: str) -> Optional[EngineSnapshot]:
        """Return snapshot for 'Engine-XX'. Returns None if not a turbofan."""
        if not equipment_id.startswith("Engine-"):
            return None
        try:
            unit_id = int(equipment_id.split("-")[1])
        except (IndexError, ValueError):
            return None
        return self._snapshots.get(unit_id)

    def get_all_snapshots(self) -> Dict[str, EngineSnapshot]:
        """Return all engine snapshots keyed by equipment_id."""
        return {s.equipment_id: s for s in self._snapshots.values()}


# Module-level singleton
cmapss = CMAPSSProcessor()
