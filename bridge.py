#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import socket
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 921
DEVICE_ID = "SuperSimGolf AtomS3R V0"

POWER_ANCHORS = (
    (800.0, 110.0),
    (1200.0, 140.0),
    (1600.0, 165.0),
    (1900.0, 180.0),
)

@dataclass
class SwingMetrics:
    peak_gyro_dps: float
    peak_accel_g: float | None = None
    sample_count: int | None = None
    duration_ms: int | None = None

def interpolate(x: float) -> float:
    pts = POWER_ANCHORS
    if x <= pts[0][0]:
        a, b = pts[0], pts[1]
    elif x >= pts[-1][0]:
        a, b = pts[-2], pts[-1]
    else:
        for a, b in zip(pts, pts[1:]):
            if a[0] <= x <= b[0]:
                break
    y = a[1] + (x - a[0]) * (b[1] - a[1]) / (b[0] - a[0])
    return max(60.0, min(195.0, y))

def read_atom_csv(path: Path) -> SwingMetrics:
    rows = []
    with path.open("r", newline="") as f:
        filtered = (line for line in f if not line.lstrip().startswith("#"))
        reader = csv.DictReader(filtered)
        required = {"t_ms", "a_mag", "g_mag"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("Expected AtomS3R columns t_ms, a_mag, g_mag")
        rows.extend(reader)
    if not rows:
        raise ValueError("CSV contains no samples")
    times = [int(float(r["t_ms"])) for r in rows]
    return SwingMetrics(
        peak_gyro_dps=max(float(r["g_mag"]) for r in rows),
        peak_accel_g=max(float(r["a_mag"]) for r in rows),
        sample_count=len(rows),
        duration_ms=max(times) - min(times),
    )

def make_packet(metrics: SwingMetrics, shot_number: int = 1) -> tuple[dict, float]:
    carry = interpolate(metrics.peak_gyro_dps)
    club_speed = max(55.0, min(93.0, 55.0 + (carry - 60.0) * (35.0 / 135.0)))
    ball_speed = club_speed * 1.34
    packet = {
        "DeviceID": DEVICE_ID,
        "Units": "Yards",
        "ShotNumber": shot_number,
        "APIversion": "1",
        "BallData": {
            "Speed": round(ball_speed, 2),
            "SpinAxis": 0.0,
            "TotalSpin": 6000.0,
            "HLA": 0.0,
            "VLA": 18.0,
        },
        "ClubData": {
            "Speed": round(club_speed, 2),
            "AngleOfAttack": 0.0,
            "FaceToTarget": 0.0,
            "Path": 0.0,
        },
        "ShotDataOptions": {
            "ContainsBallData": True,
            "ContainsClubData": True,
            "LaunchMonitorIsReady": True,
            "LaunchMonitorBallDetected": True,
            "IsHeartBeat": False,
        },
    }
    return packet, carry

def send(packet: dict, host: str, port: int, timeout: float = 3.0) -> str:
    payload = json.dumps(packet, separators=(",", ":")).encode("utf-8")
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(payload)
        sock.settimeout(timeout)
        try:
            data = sock.recv(4096)
        except socket.timeout:
            return "(no response before timeout)"
    return data.decode("utf-8", errors="replace") if data else "(connection closed)"

def main() -> int:
    p = argparse.ArgumentParser(description="Turn an AtomS3R swing into a GolfForge test shot.")
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--csv", type=Path)
    source.add_argument("--peak-gyro", type=float)
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--port", default=DEFAULT_PORT, type=int)
    p.add_argument("--shot-number", default=1, type=int)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    try:
        metrics = read_atom_csv(args.csv) if args.csv else SwingMetrics(args.peak_gyro)
        packet, carry = make_packet(metrics, args.shot_number)
        print("Swing metrics:")
        print(json.dumps(metrics.__dict__, indent=2))
        print(f"\nV0 carry target: {carry:.1f} yd")
        print("\nOpen Connect packet:")
        print(json.dumps(packet, indent=2))
        if args.dry_run:
            return 0
        print(f"\nConnecting to GolfForge at {args.host}:{args.port}...")
        print("GolfForge response:", send(packet, args.host, args.port))
        return 0
    except ConnectionRefusedError:
        print("Connection refused. Open GolfForge Practice Range and select GSPro Connect first.", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
