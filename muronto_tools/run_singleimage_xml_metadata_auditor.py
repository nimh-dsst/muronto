from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog
import json
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from muronto_app.singleimage_xml_metadata_auditor import (
    parse_singleimage_xml_bytes,
)


def pick_xml_file() -> Path:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    file_path = filedialog.askopenfilename(
        title="Select PrairieView SingleImage XML file",
        filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
    )

    if not file_path:
        raise SystemExit("No XML file selected.")

    return Path(file_path)


def add_selected_filename_metadata(xml_path: Path, result: dict) -> None:
    metadata = result.setdefault("metadata", {})
    metadata["singleimage_xml_filename"] = xml_path.name

    metadata_summary = result.get("metadata_summary")
    if metadata_summary is None:
        return

    filename_row = {
        "category": "file_identity",
        "variable": "singleimage_xml_filename",
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
    output_dir.mkdir(parents=True, exist_ok=True)

    for name in (
        "metadata_summary",
        "frames",
        "files",
        "extra_parameters",
        "sequences",
        "global_state",
        "raw_elements",
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
        "singleimage_xml_filename": metadata.get(
            "singleimage_xml_filename",
            xml_path.name,
        ),
        "singleimage_pv_version": metadata.get("singleimage_pv_version", ""),
        "singleimage_sequence_types": metadata.get(
            "singleimage_sequence_types",
            "",
        ),
        "singleimage_image_filename": metadata.get(
            "singleimage_image_filename",
            "",
        ),
        "singleimage_frame_count_total": metadata.get(
            "singleimage_frame_count_total",
            "",
        ),
        "singleimage_channel_numbers_recorded": metadata.get(
            "singleimage_channel_numbers_recorded",
            "",
        ),
        "singleimage_channel_names_recorded": metadata.get(
            "singleimage_channel_names_recorded",
            "",
        ),
        "singleimage_resolution_pix": metadata.get(
            "singleimage_resolution_pix",
            "",
        ),
        "singleimage_fov_size_um": metadata.get(
            "singleimage_fov_size_um",
            "",
        ),
        "singleimage_z_focus": metadata.get("singleimage_z_focus", ""),
        "warnings": warnings,
        "outputs": [
            f"{xml_path.stem}_metadata_summary.csv",
            f"{xml_path.stem}_frames.csv",
            f"{xml_path.stem}_files.csv",
            f"{xml_path.stem}_extra_parameters.csv",
            f"{xml_path.stem}_sequences.csv",
            f"{xml_path.stem}_global_state.csv",
            f"{xml_path.stem}_raw_elements.csv",
            f"{xml_path.stem}_audit_manifest.json",
        ],
    }

    out_path = output_dir / f"{xml_path.stem}_audit_manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Saved: {out_path}")


def print_report(result: dict) -> None:
    metadata = result.get("metadata", {})

    print("\n========================================")
    print("PrairieView SingleImage Metadata Auditor")
    print(f"File: {metadata.get('singleimage_xml_filename', '')}")
    print("========================================")
    print(f"PV version: {metadata.get('singleimage_pv_version', '')}")
    print(f"Sequence type: {metadata.get('singleimage_sequence_types', '')}")
    print(f"Image file: {metadata.get('singleimage_image_filename', '')}")
    print(f"Frames: {metadata.get('singleimage_frame_count_total', '')}")
    print(
        "Channels: "
        f"{metadata.get('singleimage_channel_numbers_recorded', '')} "
        f"({metadata.get('singleimage_channel_names_recorded', '')})"
    )
    print(f"Resolution: {metadata.get('singleimage_resolution_pix', '')}")
    print(f"FOV size: {metadata.get('singleimage_fov_size_um', '')} um")
    print(f"Z focus: {metadata.get('singleimage_z_focus', '')} um")
    print("========================================\n")


def print_key_metadata_table(result: dict) -> None:
    metadata = result.get("metadata", {})

    variables = [
        "singleimage_xml_filename",
        "singleimage_pv_version",
        "singleimage_xml_date_time",
        "singleimage_sequence_types",
        "singleimage_num_sequences",
        "singleimage_sequence_cycle",
        "singleimage_sequence_time",
        "singleimage_image_filename",
        "singleimage_frame_count_total",
        "singleimage_first_frame_relative_time_s",
        "singleimage_last_frame_relative_time_s",
        "singleimage_duration_s",
        "singleimage_frame_period_global_s",
        "singleimage_frame_rate_global_hz",
        "singleimage_files_per_frame",
        "singleimage_num_channels_recorded",
        "singleimage_channel_numbers_recorded",
        "singleimage_channel_names_recorded",
        "singleimage_objective_name",
        "singleimage_objective_magnification",
        "singleimage_objective_na",
        "singleimage_optical_zoom",
        "singleimage_laser_wavelength_nm",
        "singleimage_pixels_per_line",
        "singleimage_lines_per_frame",
        "singleimage_resolution_pix",
        "singleimage_microns_per_pixel_x",
        "singleimage_microns_per_pixel_y",
        "singleimage_fov_size_x_um",
        "singleimage_fov_size_y_um",
        "singleimage_fov_size_um",
        "singleimage_stage_x",
        "singleimage_stage_y",
        "singleimage_z_focus",
        "singleimage_etl_position_global",
        "singleimage_piezo_position_global",
        "singleimage_laser_power_0",
        "singleimage_laser_power_1",
        "singleimage_laser_power_2",
        "singleimage_twophoton_laser_power_0",
        "singleimage_pmt_gain_0",
        "singleimage_pmt_gain_1",
    ]

    print("\n===================== Key Metadata =====================")

    for variable in variables:
        print(f"{variable:<50} {metadata.get(variable, '')}")

    print("=" * 60)


def check_key_metadata_schema(result: dict) -> None:
    metadata = result.get("metadata", {})

    expected_variables = [
        "singleimage_xml_filename",
        "singleimage_pv_version",
        "singleimage_xml_date_time",
        "singleimage_sequence_types",
        "singleimage_image_filename",
        "singleimage_frame_count_total",
        "singleimage_resolution_pix",
        "singleimage_fov_size_um",
        "singleimage_z_focus",
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

    sequence_type = str(metadata.get("singleimage_sequence_types", ""))
    if sequence_type and "Single" not in sequence_type:
        warnings.append(
            f"Expected Single sequence type, but found: {sequence_type}"
        )

    frame_count = str(metadata.get("singleimage_frame_count_total", ""))
    if frame_count not in ("", "1", "1.0"):
        warnings.append(
            f"Expected one frame for SingleImage, but found {frame_count}."
        )

    channels = str(metadata.get("singleimage_num_channels_recorded", ""))
    if channels in ("", "0", "0.0"):
        warnings.append("No image channel file detected.")

    image_filename = str(metadata.get("singleimage_image_filename", ""))
    if not image_filename:
        warnings.append("No SingleImage image filename detected.")

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
    result = parse_singleimage_xml_bytes(
        xml_bytes,
        filename=xml_path.name,
    )

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