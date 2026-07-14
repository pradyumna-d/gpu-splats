from __future__ import annotations

import json
import shutil
import struct
from datetime import UTC, datetime
from pathlib import Path

from app.utils.config import Settings, settings
from app.utils.logging import JobLogger
from app.utils.process import ProcessRunner, split_command


class SplatExporter:
    def __init__(self, logger: JobLogger, config: Settings = settings) -> None:
        self.logger = logger
        self.settings = config
        self.runner = ProcessRunner(logger)

    async def export(self, config_path: Path, export_dir: Path, output_dir: Path, progress) -> Path:
        export_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        command_template = self.settings.splat_export_command or (
            "ns-export gaussian-splat --load-config {config_path} --output-dir {export_dir}"
        )
        command = split_command(command_template, config_path=config_path, export_dir=export_dir)
        await self.runner.run(
            command,
            progress=progress,
            progress_start=95,
            progress_end=98,
            estimated_seconds=120,
            env={"TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD": "1"},
        )

        splat_candidates = (
            sorted(export_dir.rglob("*.splat"))
            + sorted(export_dir.rglob("*.ksplat"))
            + sorted(export_dir.rglob("*.ply"))
        )
        if not splat_candidates:
            raise RuntimeError("Export completed without producing a splat, ksplat, or ply file.")

        selected_export = splat_candidates[0]
        scene_path = output_dir / f"scene{selected_export.suffix}"
        shutil.copy2(splat_candidates[0], scene_path)

        thumbnail_path = output_dir / "thumbnail.jpg"
        if not thumbnail_path.exists():
            thumbnail_path.write_bytes(_minimal_jpeg())

        metadata = {
            "created_at": datetime.now(UTC).isoformat(),
            "source_export": str(selected_export),
            "scene": str(scene_path),
            "scene_file": scene_path.name,
            "thumbnail": str(thumbnail_path),
        }
        bounds = _ply_bounds(selected_export)
        if bounds:
            metadata["bounds"] = bounds
        (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        await progress(100)
        return scene_path


def _minimal_jpeg() -> bytes:
    # 1x1 white JPEG fallback. Real thumbnails can be generated later from viewer screenshots.
    return bytes.fromhex(
        "ffd8ffe000104a46494600010101006000600000ffdb00430003020203020203030303040303"
        "040504040405060a07060606060d090a080a0f0d100f0e0d0e0e10121714101116110e0e14"
        "1b14161718191a1910ffdb00430103040405040509050509140d0b0d1414141414141414"
        "141414141414141414141414141414141414141414141414141414141414141414141414"
        "14141414141414ffc00011080001000103012200021101031101ffc4001400010000000000"
        "00000000000000000000000008ffc4001410010000000000000000000000000000000000"
        "0000ffda000c03010002110311003f00b2c001ffd9"
    )


def _ply_bounds(path: Path) -> dict[str, list[float]] | None:
    if path.suffix.lower() != ".ply":
        return None

    data = path.read_bytes()
    header_end = data.find(b"end_header\n")
    header_length = len(b"end_header\n")
    if header_end == -1:
        header_end = data.find(b"end_header\r\n")
        header_length = len(b"end_header\r\n")
    if header_end == -1:
        return None

    header = data[:header_end].decode("ascii", errors="ignore").splitlines()
    if "format binary_little_endian" not in "\n".join(header):
        return None

    type_formats = {
        "char": "b",
        "uchar": "B",
        "int8": "b",
        "uint8": "B",
        "short": "h",
        "ushort": "H",
        "int16": "h",
        "uint16": "H",
        "int": "i",
        "uint": "I",
        "int32": "i",
        "uint32": "I",
        "float": "f",
        "float32": "f",
        "double": "d",
        "float64": "d",
    }

    vertex_count = 0
    vertex_props: list[tuple[str, str]] = []
    in_vertex = False
    for line in header:
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "element":
            in_vertex = parts[1] == "vertex"
            if in_vertex:
                vertex_count = int(parts[2])
            continue
        if in_vertex and len(parts) == 3 and parts[0] == "property":
            vertex_props.append((parts[2], parts[1]))

    if not vertex_count or not vertex_props:
        return None

    try:
        row = struct.Struct("<" + "".join(type_formats[prop_type] for _, prop_type in vertex_props))
    except KeyError:
        return None

    prop_offsets: dict[str, int] = {}
    offset = 0
    for name, prop_type in vertex_props:
        prop_offsets[name] = offset
        offset += struct.calcsize("<" + type_formats[prop_type])

    if not {"x", "y", "z"}.issubset(prop_offsets):
        return None

    payload_start = header_end + header_length
    mins = [float("inf"), float("inf"), float("inf")]
    maxs = [float("-inf"), float("-inf"), float("-inf")]
    for index in range(vertex_count):
        base = payload_start + index * row.size
        if base + row.size > len(data):
            return None
        values = [
            struct.unpack_from("<f", data, base + prop_offsets["x"])[0],
            struct.unpack_from("<f", data, base + prop_offsets["y"])[0],
            struct.unpack_from("<f", data, base + prop_offsets["z"])[0],
        ]
        for axis, value in enumerate(values):
            mins[axis] = min(mins[axis], value)
            maxs[axis] = max(maxs[axis], value)

    center = [(mins[axis] + maxs[axis]) / 2 for axis in range(3)]
    size = [maxs[axis] - mins[axis] for axis in range(3)]
    return {"min": mins, "max": maxs, "center": center, "size": size}
