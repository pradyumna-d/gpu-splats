#!/usr/bin/env python3
from __future__ import annotations

import json
import struct
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> str:
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return completed.stdout + completed.stderr


def model_stats(model_dir: Path) -> dict[str, int | float | str]:
    output = run(["colmap", "model_analyzer", "--path", str(model_dir)])
    stats: dict[str, int | float | str] = {"model": str(model_dir)}
    for line in output.splitlines():
        if "Registered images:" in line:
            stats["registered_images"] = int(line.rsplit(":", 1)[1].strip())
        elif "Points:" in line:
            stats["points"] = int(line.rsplit(":", 1)[1].strip())
        elif "Mean reprojection error:" in line:
            stats["mean_reprojection_error_px"] = float(line.rsplit(":", 1)[1].strip().removesuffix("px"))
    return stats


def ply_bounds(path: Path) -> dict[str, list[float]] | None:
    if not path.exists() or path.suffix.lower() != ".ply":
        return None
    data = path.read_bytes()
    header_end = data.find(b"end_header\n")
    header_len = len(b"end_header\n")
    if header_end == -1:
        return None
    header = data[:header_end].decode("ascii", errors="ignore").splitlines()
    if "format binary_little_endian" not in "\n".join(header):
        return None

    formats = {"float": "f", "float32": "f", "double": "d", "uchar": "B", "char": "b", "int": "i", "uint": "I"}
    count = 0
    props: list[tuple[str, str]] = []
    in_vertex = False
    for line in header:
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "element":
            in_vertex = parts[1] == "vertex"
            if in_vertex:
                count = int(parts[2])
        elif in_vertex and len(parts) == 3 and parts[0] == "property":
            props.append((parts[2], parts[1]))
    row = struct.Struct("<" + "".join(formats[prop_type] for _, prop_type in props))
    offsets: dict[str, int] = {}
    offset = 0
    for name, prop_type in props:
        offsets[name] = offset
        offset += struct.calcsize("<" + formats[prop_type])
    if not {"x", "y", "z"}.issubset(offsets):
        return None

    mins = [float("inf"), float("inf"), float("inf")]
    maxs = [float("-inf"), float("-inf"), float("-inf")]
    payload_start = header_end + header_len
    for index in range(count):
        base = payload_start + index * row.size
        xyz = [struct.unpack_from("<f", data, base + offsets[axis])[0] for axis in ("x", "y", "z")]
        for axis, value in enumerate(xyz):
            mins[axis] = min(mins[axis], value)
            maxs[axis] = max(maxs[axis], value)
    return {
        "min": mins,
        "max": maxs,
        "center": [(mins[axis] + maxs[axis]) / 2 for axis in range(3)],
        "size": [maxs[axis] - mins[axis] for axis in range(3)],
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: scripts/diagnose_job.py <job_id>", file=sys.stderr)
        return 2

    job_id = sys.argv[1]
    job_dir = ROOT / "data" / "jobs" / job_id
    output_dir = ROOT / "data" / "outputs" / job_id
    metadata_path = job_dir / "metadata.json"
    if not metadata_path.exists():
        print(f"Job not found: {job_id}", file=sys.stderr)
        return 1

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    frame_count = len(list((job_dir / "frames").glob("*.jpg")))
    sparse_dir = job_dir / "colmap" / "sparse"
    models = [model_stats(path) for path in sorted(sparse_dir.iterdir()) if path.is_dir()] if sparse_dir.exists() else []
    best = max(models, key=lambda item: (int(item.get("registered_images", 0)), int(item.get("points", 0))), default=None)

    transforms_path = job_dir / "dataset" / "transforms.json"
    dataset_frames = None
    if transforms_path.exists():
        dataset_frames = len(json.loads(transforms_path.read_text(encoding="utf-8")).get("frames", []))

    output_metadata_path = output_dir / "metadata.json"
    output_metadata = json.loads(output_metadata_path.read_text(encoding="utf-8")) if output_metadata_path.exists() else {}
    scene_file = output_metadata.get("scene_file")
    scene_path = output_dir / scene_file if scene_file else None

    report = {
        "job": {
            "job_id": job_id,
            "status": metadata.get("status"),
            "progress": metadata.get("progress"),
            "input_filename": metadata.get("input_filename"),
        },
        "frames_extracted": frame_count,
        "colmap_models": models,
        "best_model": best,
        "best_registered_ratio": (best.get("registered_images", 0) / frame_count if best and frame_count else None),
        "dataset_frames": dataset_frames,
        "scene_file": scene_file,
        "scene_bounds": ply_bounds(scene_path) if scene_path else None,
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
