#!/usr/bin/env python3
"""Convert MEGAlib .tra/.tra.gz hits to a GTM science-like CSV.

The output follows the science pipeline column layout, except that Gain is
removed and ADC is replaced by Energy from the simulation hit.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import math
import random
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Iterator, Optional, TextIO


OUTPUT_COLUMNS = [
    "GTM ID",
    "Day of Year",
    "Hour",
    "Minute",
    "Second",
    "Subsecond",
    "X",
    "Y",
    "Z",
    "Q1",
    "Q2",
    "Q3",
    "Q4",
    "Temperature",
    "CITIROC",
    "Channel",
    "Energy",
    "Relative Time",
]

EARTH_EQUATORIAL_RADIUS_M = 6_378_137.0
ORBIT_ALTITUDE_M = 561_000.0
ORBIT_RADIUS_M = EARTH_EQUATORIAL_RADIUS_M + ORBIT_ALTITUDE_M
ORBIT_RADIUS_JITTER_M = 5_000.0
# Synthetic telemetry settings, not a reconstruction of the actual orbit.
ORBIT_PERIOD_SECONDS = 96.0 * 60.0
ATTITUDE_RATE_DEG_PER_SECOND = 0.1
TEMPERATURE_MIN_C = -25.0
TEMPERATURE_MAX_C = 45.0
TEMPERATURE_PERIOD_SECONDS = 3.0 * 60.0 * 60.0

# Inverse of the provided simplify_label() GTM/CITIROC/channel definition.
# Tuple format: (GTM ID, CITIROC, first hardware channel in the 16-channel block)
SENSOR_TO_READOUT = {
    "M1": (0, 1, 16),
    "M2": (0, 1, 0),
    "M3": (0, 0, 16),
    "M4": (0, 0, 0),
    "S1": (1, 1, 16),
    "S2": (1, 1, 0),
    "S3": (1, 0, 16),
    "S4": (1, 0, 0),
}


@dataclass
class Hit:
    event_id: Optional[int]
    ti: Optional[float]
    x: float
    y: float
    z: float
    energy: float


@dataclass
class ConvertStats:
    read_hits: int = 0
    written_hits: int = 0
    skipped_hits: int = 0
    multi_hit_events: int = 0
    max_hits_per_event: int = 0
    sensor_counts: Counter[str] = None
    skipped_sensor_counts: Counter[str] = None

    def __post_init__(self) -> None:
        if self.sensor_counts is None:
            self.sensor_counts = Counter()
        if self.skipped_sensor_counts is None:
            self.skipped_sensor_counts = Counter()


def open_tra(path: Path) -> TextIO:
    if path.name.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("rt", encoding="utf-8", errors="replace")


def parse_start_time(value: str) -> datetime:
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    raise argparse.ArgumentTypeError(
        "start time must look like 2026-06-28T14:27:05"
    )


def read_tra_start_time(path: Path) -> Optional[datetime]:
    with open_tra(path) as handle:
        for raw in handle:
            parts = raw.split()
            if not parts:
                continue
            if parts[0] == "SE":
                break
            if parts[0] == "Date" and len(parts) >= 3:
                return parse_start_time(f"{parts[1]} {parts[2]}")
    return None


def iter_hits(path: Path) -> Iterator[Hit]:
    event_id: Optional[int] = None
    event_ti: Optional[float] = None
    pending_pe_energy: Optional[float] = None
    pending_me_energy: Optional[float] = None

    with open_tra(path) as handle:
        for raw in handle:
            parts = raw.split()
            if not parts:
                continue

            tag = parts[0]
            if tag == "SE":
                event_id = None
                event_ti = None
                pending_pe_energy = None
                pending_me_energy = None
            elif tag == "ID" and len(parts) >= 2:
                event_id = int(float(parts[1]))
            elif tag == "TI" and len(parts) >= 2:
                event_ti = float(parts[1])
            elif tag == "PE" and len(parts) >= 2:
                pending_pe_energy = float(parts[1])
            elif tag == "PP" and pending_pe_energy is not None and len(parts) >= 4:
                yield Hit(
                    event_id=event_id,
                    ti=event_ti,
                    x=float(parts[1]),
                    y=float(parts[2]),
                    z=float(parts[3]),
                    energy=pending_pe_energy,
                )
                pending_pe_energy = None
            elif tag == "ME" and len(parts) >= 2:
                pending_me_energy = float(parts[1])
            elif tag == "MG" and pending_me_energy is not None and len(parts) >= 4:
                yield Hit(
                    event_id=event_id,
                    ti=event_ti,
                    x=float(parts[1]),
                    y=float(parts[2]),
                    z=float(parts[3]),
                    energy=pending_me_energy,
                )
                pending_me_energy = None
            elif tag == "CH" and len(parts) >= 6:
                yield Hit(
                    event_id=event_id,
                    ti=event_ti,
                    x=float(parts[2]),
                    y=float(parts[3]),
                    z=float(parts[4]),
                    energy=float(parts[5]),
                )


def classify_sensor(x: float, y: float, z: float) -> str:
    """Classify a simulation hit position with the rule provided by GTM."""
    if z < -25:
        if z < -44:
            return "M3"
        if z > -37:
            return "M2"
        if x > 38:
            return "M4"
        return "M1"

    if z < -11:
        return "S3"
    if z > -4:
        return "S2"
    if x > 36:
        return "S1"
    return "S4"


def stable_sensor_channel(x: float, y: float, z: float) -> int:
    """Return a deterministic pseudo-channel in 0..15 from the hit position."""
    pitch = 1.24
    ix = int(abs(round(x / pitch)))
    iy = int(abs(round(y / pitch)))
    iz = int(abs(round(z / pitch)))
    return (ix * 3 + iy * 5 + iz * 7) % 16


def map_sensor_to_readout(hit: Hit) -> tuple[int, int, int, str, int]:
    sensor = classify_sensor(hit.x, hit.y, hit.z)
    gtm_id, citiroc, channel_shift = SENSOR_TO_READOUT[sensor]
    sensor_channel = stable_sensor_channel(hit.x, hit.y, hit.z)
    channel = channel_shift + sensor_channel
    return gtm_id, citiroc, channel, sensor, sensor_channel


def _random_orthonormal_pair(
    rng: random.Random, dimensions: int
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Choose two perpendicular unit vectors for a circular trajectory."""
    basis: list[tuple[float, ...]] = []
    while len(basis) < 2:
        candidate = [rng.gauss(0.0, 1.0) for _ in range(dimensions)]
        if basis:
            projection = sum(a * b for a, b in zip(candidate, basis[0]))
            candidate = [a - projection * b for a, b in zip(candidate, basis[0])]
        norm = math.sqrt(sum(value * value for value in candidate))
        if norm > 1e-12:
            basis.append(tuple(value / norm for value in candidate))
    return basis[0], basis[1]


class DummySpacecraftTimeline:
    """Smooth synthetic telemetry sampled by elapsed seconds, not hit count."""

    def __init__(self, rng: random.Random) -> None:
        self.position_basis = _random_orthonormal_pair(rng, 3)
        self.orbit_radius = ORBIT_RADIUS_M + rng.uniform(
            -ORBIT_RADIUS_JITTER_M, ORBIT_RADIUS_JITTER_M
        )
        self.quaternion_basis = _random_orthonormal_pair(rng, 4)
        self.temperature_phase = rng.uniform(0.0, math.tau)

    def values_at(self, elapsed_seconds: float) -> dict[str, float]:
        orbit_phase = math.tau * elapsed_seconds / ORBIT_PERIOD_SECONDS
        position = [
            self.orbit_radius * (a * math.cos(orbit_phase) + b * math.sin(orbit_phase))
            for a, b in zip(*self.position_basis)
        ]

        # A quaternion advances by half the physical rotation angle. Keep its
        # sign continuous instead of forcing one component to stay positive.
        attitude_phase = math.radians(ATTITUDE_RATE_DEG_PER_SECOND) * elapsed_seconds / 2.0
        quaternion = [
            a * math.cos(attitude_phase) + b * math.sin(attitude_phase)
            for a, b in zip(*self.quaternion_basis)
        ]
        norm = math.sqrt(sum(value * value for value in quaternion))
        q1, q2, q3, q4 = (value / norm for value in quaternion)

        temperature_midpoint = (TEMPERATURE_MIN_C + TEMPERATURE_MAX_C) / 2.0
        temperature_amplitude = (TEMPERATURE_MAX_C - TEMPERATURE_MIN_C) / 2.0
        temperature_phase = (
            self.temperature_phase + math.tau * elapsed_seconds / TEMPERATURE_PERIOD_SECONDS
        )
        return {
            "X": position[0],
            "Y": position[1],
            "Z": position[2],
            "Q1": q1,
            "Q2": q2,
            "Q3": q3,
            "Q4": q4,
            "Temperature": temperature_midpoint + temperature_amplitude * math.sin(temperature_phase),
        }


def format_float(value: float, digits: int = 9) -> str:
    """Round to at most digits decimal places and omit trailing zeros."""
    text = f"{value:.{digits}f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def split_time_columns(start_time: datetime, relative_seconds: float) -> tuple[datetime, float]:
    """Apply relative seconds to start_time and return whole-second time plus subsecond."""
    whole_seconds = math.floor(relative_seconds)
    subsecond = relative_seconds - whole_seconds
    if subsecond >= 1.0:
        whole_seconds += 1
        subsecond = 0.0
    absolute_time = start_time + timedelta(seconds=whole_seconds)
    return absolute_time, subsecond


def default_output_path(input_path: Path) -> Path:
    name = input_path.name
    for suffix in (".tra.gz", ".tra"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    return input_path.with_name(f"{name}_science_pipeline_relative_time.csv")


def convert_file(
    input_path: Path,
    output_path: Path,
    start_time: datetime,
    relative_origin: str,
    seed: int,
    max_rows: Optional[int],
    include_sensor_columns: bool,
) -> ConvertStats:
    columns = list(OUTPUT_COLUMNS)
    if include_sensor_columns:
        columns.extend(["Sensor Name", "Sensor Channel"])

    spacecraft_timeline = DummySpacecraftTimeline(random.Random(seed))
    stats = ConvertStats()
    first_ti: Optional[float] = None
    event_hit_counts: Counter[tuple[Optional[int], float]] = Counter()

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()

        for hit in iter_hits(input_path):
            stats.read_hits += 1
            sensor = classify_sensor(hit.x, hit.y, hit.z)
            stats.sensor_counts[sensor] += 1

            if hit.ti is None:
                stats.skipped_hits += 1
                stats.skipped_sensor_counts["missing_TI"] += 1
                continue

            mapping = map_sensor_to_readout(hit)
            if first_ti is None:
                first_ti = hit.ti
            relative_time = hit.ti - first_ti if relative_origin == "first" else hit.ti
            relative_time_text = format_float(relative_time, 6)
            # Use the exported precision for time columns, including second/day carry.
            absolute_time, subsecond = split_time_columns(start_time, float(relative_time_text))
            event_key = (hit.event_id, hit.ti)
            event_hit_counts[event_key] += 1
            stats.max_hits_per_event = max(
                stats.max_hits_per_event, event_hit_counts[event_key]
            )
            if event_hit_counts[event_key] == 2:
                stats.multi_hit_events += 1
            spacecraft = spacecraft_timeline.values_at(hit.ti - first_ti)
            gtm_id, citiroc, channel, original_sensor, sensor_channel = mapping

            row = {
                "GTM ID": gtm_id,
                "Day of Year": int(absolute_time.strftime("%j")),
                "Hour": absolute_time.hour,
                "Minute": absolute_time.minute,
                "Second": absolute_time.second,
                "Subsecond": format_float(subsecond, 6),
                "X": format_float(spacecraft["X"], 3),
                "Y": format_float(spacecraft["Y"], 3),
                "Z": format_float(spacecraft["Z"], 3),
                "Q1": format_float(spacecraft["Q1"], 6),
                "Q2": format_float(spacecraft["Q2"], 6),
                "Q3": format_float(spacecraft["Q3"], 6),
                "Q4": format_float(spacecraft["Q4"], 6),
                "Temperature": format_float(spacecraft["Temperature"], 5),
                "CITIROC": citiroc,
                "Channel": channel,
                "Energy": format_float(hit.energy, 3),
                "Relative Time": relative_time_text,
            }
            if include_sensor_columns:
                row["Sensor Name"] = original_sensor
                row["Sensor Channel"] = sensor_channel

            writer.writerow(row)
            stats.written_hits += 1
            if max_rows is not None and stats.written_hits >= max_rows:
                break

    return stats


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert a MEGAlib .tra/.tra.gz simulation file to a GTM science-like CSV."
    )
    parser.add_argument("input", type=Path, help="input .tra or .tra.gz file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="output CSV path; defaults to <input>_science_pipeline_relative_time.csv",
    )
    parser.add_argument(
        "--start-time",
        type=parse_start_time,
        help="absolute start time, e.g. 2026-06-28T14:27:05; defaults to the TRA Date header",
    )
    parser.add_argument(
        "--relative-origin",
        choices=("zero", "first"),
        default="zero",
        help="zero uses TI directly; first subtracts the first written hit TI",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="random seed for the smooth dummy spacecraft trajectory and initial attitude",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        help="write only this many converted rows; useful for quick checks",
    )
    parser.add_argument(
        "--include-sensor-columns",
        action="store_true",
        help="append Sensor Name and Sensor Channel columns for validation",
    )
    return parser


def print_stats(stats: ConvertStats, output_path: Path) -> None:
    print(f"Wrote {stats.written_hits} rows to {output_path}")
    print(f"Read {stats.read_hits} hits; skipped {stats.skipped_hits}")
    print(
        f"Multi-hit events written: {stats.multi_hit_events}; "
        f"max hits/event: {stats.max_hits_per_event}"
    )
    if stats.sensor_counts:
        sensor_text = ", ".join(
            f"{sensor}:{count}" for sensor, count in sorted(stats.sensor_counts.items())
        )
        print(f"Sensors read: {sensor_text}")
    if stats.skipped_sensor_counts:
        skipped_text = ", ".join(
            f"{sensor}:{count}"
            for sensor, count in sorted(stats.skipped_sensor_counts.items())
        )
        print(f"Skipped: {skipped_text}")


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    input_path = args.input
    if not input_path.exists():
        parser.error(f"input file does not exist: {input_path}")

    output_path = args.output or default_output_path(input_path)
    start_time = args.start_time or read_tra_start_time(input_path)
    if start_time is None:
        start_time = datetime(2024, 1, 1, 0, 0, 0)

    stats = convert_file(
        input_path=input_path,
        output_path=output_path,
        start_time=start_time,
        relative_origin=args.relative_origin,
        seed=args.seed,
        max_rows=args.max_rows,
        include_sensor_columns=args.include_sensor_columns,
    )
    print_stats(stats, output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
