from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog
import json
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from muronto_app.tseries_xml_metadata_auditor import (
    parse_tseries_xml_bytes,
)


def pick_xml_file() -> Path:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    file_path = filedialog.askopenfilename(
        title="Select PrairieView XML file",
        filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
    )

    if not file_path:
        raise SystemExit("No XML file selected.")

    return Path(file_path)


def add_selected_filename_metadata(xml_path: Path, result: dict) -> None:
    metadata = result.setdefault("metadata", {})
    metadata["tseries_xml_filename"] = xml_path.name

    metadata_summary = result.get("metadata_summary")
    if metadata_summary is None:
        return

    filename_row = {
        "category": "file_identity",
        "variable": "tseries_xml_filename",
        "value": xml_path.name,
        "unit": "",
        "source_scope": "file",
        "xml_source": "selected file path",
        "extraction_method": "file name from selected XML path",
        "confidence": "high",
        "notes": "",
    }

    result["metadata_summary"] = pd.concat(
        [
            pd.DataFrame([filename_row]),
            metadata_summary,
        ],
        ignore_index=True,
    )


def export_outputs(xml_path: Path, result: dict) -> Path:
    output_dir = xml_path.parent / f"{xml_path.stem}_metadata_audit"
    output_dir.mkdir(exist_ok=True)

    for name in (
        "metadata_summary",
        "frames",
        "files",
        "z_audit",
        "planes",
        "sequences",
        "global_state",
    ):
        df = result.get(name)
        if df is None:
            continue

        out_path = output_dir / f"{xml_path.stem}_{name}.csv"
        df.to_csv(out_path, index=False)
        print(f"Saved: {out_path}")

    return output_dir


def export_manifest(
    xml_path: Path,
    output_dir: Path,
    result: dict,
    warnings: list[str],
) -> None:
    metadata = result.get("metadata", {})

    manifest = {
        "source_xml": str(xml_path),
        "output_dir": str(output_dir),
        "tseries_xml_filename": metadata.get(
            "tseries_xml_filename",
            xml_path.name,
        ),
        "pv_version": metadata.get("pv_version", ""),
        "sequence_types": metadata.get("sequence_types", ""),
        "frame_count_total": metadata.get("frame_count_total", ""),
        "frame_rate_actual_hz": metadata.get("frame_rate_actual_hz", ""),
        "num_planes_inferred": metadata.get("num_planes_inferred", ""),
        "plane_depths": metadata.get("plane_depths", ""),
        "plane_relative_depths": metadata.get("plane_relative_depths", ""),
        "laser_power_at_plane_depths": metadata.get(
            "laser_power_at_plane_depths",
            "",
        ),
        "volume_rate_hz": metadata.get("volume_rate_hz", ""),
        "warnings": warnings,
        "outputs": [
            f"{xml_path.stem}_metadata_summary.csv",
            f"{xml_path.stem}_frames.csv",
            f"{xml_path.stem}_files.csv",
            f"{xml_path.stem}_z_audit.csv",
            f"{xml_path.stem}_planes.csv",
            f"{xml_path.stem}_sequences.csv",
            f"{xml_path.stem}_global_state.csv",
        ],
    }

    out_path = output_dir / f"{xml_path.stem}_audit_manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Saved: {out_path}")


def print_report(result: dict) -> None:
    metadata = result.get("metadata", {})

    print("\n========================================")
    print("PrairieView Metadata Auditor")
    print(f"File: {metadata.get('tseries_xml_filename', '')}")
    print("========================================")
    print(f"PV version: {metadata.get('pv_version', '')}")
    print(f"Sequence type: {metadata.get('sequence_types', '')}")
    print(f"Frames: {metadata.get('frame_count_total', '')}")
    print(f"Frame rate: {metadata.get('frame_rate_actual_hz', '')} Hz")
    print(f"Planes: {metadata.get('num_planes_inferred', '')}")
    print(f"Plane depths: {metadata.get('plane_depths', '')}")
    print(
        "Plane relative depths: "
        f"{metadata.get('plane_relative_depths', '')}"
    )
    print(
        "Laser power at plane depths: "
        f"{metadata.get('laser_power_at_plane_depths', '')}"
    )
    print(f"Volume rate: {metadata.get('volume_rate_hz', '')} Hz")
    print("========================================\n")


def print_key_metadata_table(result: dict) -> None:
    metadata = result.get("metadata", {})

    variables = [
        "tseries_xml_filename",
        "pv_version",
        "xml_date_time",
        "sequence_types",
        "num_sequences_or_cycles",
        "frame_count_total",
        "first_frame_relative_time_s",
        "last_frame_relative_time_s",
        "duration_s",
        "frame_period_actual_s",
        "frame_rate_actual_hz",
        "frame_period_global_s",
        "frame_rate_global_hz",
        "frame_period_global_matches_actual",
        "files_per_frame",
        "num_channels_recorded",
        "channel_numbers_recorded",
        "channel_names_recorded",
        "objective_name",
        "objective_magnification",
        "objective_na",
        "optical_zoom",
        "laser_wavelength_nm",
        "pixels_per_line",
        "lines_per_frame",
        "resolution_pix",
        "microns_per_pixel_x",
        "microns_per_pixel_y",
        "fov_size_x_um",
        "fov_size_y_um",
        "fov_size_um",
        "stage_x",
        "stage_y",
        "z_focus",
        "etl_position_global",
        "piezo_position_global",
        "laser_power_0",
        "laser_power_1",
        "laser_power_2",
        "twophoton_laser_power_0",
        "pmt_gain_0",
        "pmt_gain_1",
        "num_planes_inferred",
        "plane_depths",
        "plane_relative_depths",
        "laser_power_at_plane_depths",
        "plane_depth_source",
        "num_volumes_complete",
        "leftover_frames_after_complete_volumes",
        "volume_rate_hz",
    ]

    print("\n===================== Key Metadata =====================")

    for variable in variables:
        print(f"{variable:<40} {metadata.get(variable, '')}")

    print("=" * 60)


def check_key_metadata_schema(result: dict) -> None:
    metadata = result.get("metadata", {})

    expected_variables = [
        "tseries_xml_filename",
        "pv_version",
        "xml_date_time",
        "sequence_types",
        "frame_count_total",
        "frame_rate_actual_hz",
        "resolution_pix",
        "fov_size_um",
        "num_planes_inferred",
        "plane_depths",
        "plane_relative_depths",
        "laser_power_at_plane_depths",
    ]

    missing = [
        variable
        for variable in expected_variables
        if variable not in metadata
    ]

    if not missing:
        print("\nSchema check: passed")
        return

    print("\nSchema check: missing expected variables")
    for variable in missing:
        print(f"- {variable}")


def collect_warnings(result: dict) -> list[str]:
    metadata = result.get("metadata", {})
    warnings = []

    if str(metadata.get("frame_period_global_matches_actual", "")).lower() == "false":
        warnings.append(
            "Global framePeriod does not match frame timestamps. Use actual frame rate."
        )

    leftover = metadata.get("leftover_frames_after_complete_volumes", "")
    if str(leftover) not in ("", "0", "0.0"):
        warnings.append(
            f"Recording has {leftover} leftover frame(s) after complete volumes."
        )

    num_planes = str(metadata.get("num_planes_inferred", ""))
    plane_depths = str(metadata.get("plane_depths", ""))
    laser_powers = str(metadata.get("laser_power_at_plane_depths", ""))

    if num_planes not in ("", "1") and not laser_powers:
        warnings.append(
            "Multiple planes were detected, but laser_power_at_plane_depths is blank."
        )

    if plane_depths and laser_powers:
        plane_depth_count = len(
            [value for value in plane_depths.split(", ") if value]
        )
        laser_power_count = len(
            [value for value in laser_powers.split(", ") if value]
        )
        if plane_depth_count != laser_power_count:
            warnings.append(
                "plane_depths and laser_power_at_plane_depths have different "
                f"numbers of values ({plane_depth_count} vs {laser_power_count})."
            )

    return warnings


def print_warnings(warnings: list[str]) -> None:
    if not warnings:
        print("\nWarnings: none")
        return

    print("\nWarnings:")
    for warning in warnings:
        print(f"- {warning}")


def main() -> None:
    xml_path = pick_xml_file()
    print(f"Selected XML: {xml_path}")

    xml_bytes = xml_path.read_bytes()
    result = parse_tseries_xml_bytes(xml_bytes)

    add_selected_filename_metadata(xml_path, result)

    output_dir = export_outputs(xml_path, result)
    warnings = collect_warnings(result)
    export_manifest(xml_path, output_dir, result, warnings)
    print_report(result)
    print_key_metadata_table(result)
    check_key_metadata_schema(result)
    print_warnings(warnings)


if __name__ == "__main__":
    main()