from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog
import json


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from muronto_app.markpoints_xml_metadata_auditor import (
    parse_markpoints_xml_bytes,
)


def pick_xml_file() -> Path:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    file_path = filedialog.askopenfilename(
        title="Select PrairieView MarkPoints XML file",
        filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
    )

    if not file_path:
        raise SystemExit("No XML file selected.")

    return Path(file_path)


def export_outputs(xml_path: Path, result: dict) -> Path:
    output_dir = xml_path.parent / f"{xml_path.stem}_metadata_audit"
    output_dir.mkdir(parents=True, exist_ok=True)

    table_names = (
        "metadata_summary",
        "series",
        "markpoints",
        "galvo_elements",
        "points",
        "raw_elements",
    )

    for name in table_names:
        df = result.get(name)
        if df is None:
            continue

        out_path = output_dir / f"{name}.csv"
        df.to_csv(out_path, index=False)
        print(f"Saved: {out_path}")

    return output_dir


def collect_warnings(result: dict) -> list[str]:
    metadata = result.get("metadata", {})
    warnings = []

    num_points = metadata.get("markpoints_num_points", "")
    num_custom = metadata.get("markpoints_num_custom_laser_percent_values", "")
    num_indices = metadata.get("markpoints_num_indices_declared", "")

    if str(num_points) in ("", "0", "0.0"):
        warnings.append("No MarkPoints targets detected.")

    if (
        str(num_points) not in ("", "0", "0.0")
        and str(num_custom) not in ("", str(num_points))
    ):
        warnings.append(
            "Number of CustomLaserPercent values does not match number of points."
        )

    if (
        str(num_points) not in ("", "0", "0.0")
        and str(num_indices) not in ("", str(num_points))
    ):
        warnings.append(
            "Declared MarkPoints indices do not match number of Point elements."
        )

    if str(metadata.get("markpoints_all_points_at_once", "")).lower() == "true":
        warnings.append(
            "AllPointsAtOnce is True; InterPointDelay may not reflect sequential point timing."
        )

    if str(metadata.get("markpoints_any_points_have_z", "")).lower() != "true":
        warnings.append(
            "Use3D may be true, but no point-specific Z values were detected."
        )

    inferred_power = str(metadata.get("markpoints_inferred_point_power_by_point", ""))
    if inferred_power:
        warnings.append(
            "Inferred point powers were calculated as UncagingLaserPower × CustomLaserPercent; verify this interpretation before treating as calibrated power."
        )

    return warnings


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
        "markpoints_xml_filename": metadata.get(
            "markpoints_xml_filename",
            xml_path.name,
        ),
        "markpoints_source_tseries": metadata.get(
            "markpoints_source_tseries",
            "",
        ),
        "markpoints_cycle": metadata.get("markpoints_cycle", ""),
        "markpoints_group_name": metadata.get("markpoints_group_name", ""),
        "markpoints_category": metadata.get("markpoints_category", ""),
        "markpoints_num_points": metadata.get("markpoints_num_points", ""),
        "markpoints_uncaging_laser": metadata.get(
            "markpoints_uncaging_laser",
            "",
        ),
        "markpoints_uncaging_laser_power": metadata.get(
            "markpoints_uncaging_laser_power",
            "",
        ),
        "markpoints_repetitions": metadata.get("markpoints_repetitions", ""),
        "markpoints_duration_ms": metadata.get("markpoints_duration_ms", ""),
        "warnings": warnings,
        "outputs": [
            "metadata_summary.csv",
            "series.csv",
            "markpoints.csv",
            "galvo_elements.csv",
            "points.csv",
            "raw_elements.csv",
            "audit_manifest.json",
        ],
    }

    out_path = output_dir / "audit_manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Saved: {out_path}")


def print_report(result: dict) -> None:
    metadata = result.get("metadata", {})

    print("\n========================================")
    print("PrairieView MarkPoints Metadata Auditor")
    print("========================================")
    print(f"File: {metadata.get('markpoints_xml_filename', '')}")
    print(f"Source TSeries: {metadata.get('markpoints_source_tseries', '')}")
    print(f"Cycle: {metadata.get('markpoints_cycle', '')}")
    print(f"Group name: {metadata.get('markpoints_group_name', '')}")
    print(f"Category: {metadata.get('markpoints_category', '')}")
    print(f"Points: {metadata.get('markpoints_num_points', '')}")
    print(f"Uncaging laser: {metadata.get('markpoints_uncaging_laser', '')}")
    print(
        "Uncaging laser power: "
        f"{metadata.get('markpoints_uncaging_laser_power', '')}"
    )
    print(f"Repetitions: {metadata.get('markpoints_repetitions', '')}")
    print(f"Duration: {metadata.get('markpoints_duration_ms', '')} ms")
    print(
        "Custom laser percent: "
        f"{metadata.get('markpoints_custom_laser_percent', '')}"
    )
    print(
        "Spiral size: "
        f"{metadata.get('markpoints_spiral_size_um_values', '')} um"
    )
    print("========================================\n")


def print_key_metadata_table(result: dict) -> None:
    metadata = result.get("metadata", {})

    variables = [
        "markpoints_xml_filename",
        "markpoints_source_tseries",
        "markpoints_cycle",
        "markpoints_root_tag",
        "markpoints_group_name",
        "markpoints_category",
        "markpoints_iterations",
        "markpoints_iteration_delay_ms",
        "markpoints_calc_funct_map",
        "markpoints_num_markpoint_elements",
        "markpoints_num_galvo_elements",
        "markpoints_num_points",
        "markpoints_repetitions",
        "markpoints_initial_delay_ms",
        "markpoints_inter_point_delay_ms",
        "markpoints_duration_ms",
        "markpoints_trigger_frequency",
        "markpoints_trigger_selection",
        "markpoints_trigger_count",
        "markpoints_async_sync_frequency",
        "markpoints_uncaging_laser",
        "markpoints_uncaging_laser_power",
        "markpoints_custom_laser_percent",
        "markpoints_num_custom_laser_percent_values",
        "markpoints_custom_laser_percent_by_point",
        "markpoints_custom_laser_percent_min",
        "markpoints_custom_laser_percent_max",
        "markpoints_inferred_point_power_by_point",
        "markpoints_inferred_point_power_min",
        "markpoints_inferred_point_power_max",
        "markpoints_all_points_at_once",
        "markpoints_use_3d",
        "markpoints_points_label",
        "markpoints_indices_raw",
        "markpoints_indices_expanded",
        "markpoints_num_indices_declared",
        "markpoints_point_indices",
        "markpoints_all_points_spiral",
        "markpoints_spiral_revolutions",
        "markpoints_spiral_size_um_values",
        "markpoints_spiral_size_um_min",
        "markpoints_spiral_size_um_max",
        "markpoints_x_normalized_values",
        "markpoints_y_normalized_values",
        "markpoints_x_normalized_min",
        "markpoints_x_normalized_max",
        "markpoints_y_normalized_min",
        "markpoints_y_normalized_max",
        "markpoints_any_points_have_z",
        "markpoints_voltage_output_category_name",
        "markpoints_voltage_rec_category_name",
        "markpoints_parameter_set",
    ]

    print("\n===================== Key Metadata =====================")

    for variable in variables:
        print(f"{variable:<50} {metadata.get(variable, '')}")

    print("=" * 60)


def check_key_metadata_schema(result: dict) -> None:
    metadata = result.get("metadata", {})

    expected_variables = [
        "markpoints_xml_filename",
        "markpoints_group_name",
        "markpoints_category",
        "markpoints_num_points",
        "markpoints_uncaging_laser",
        "markpoints_uncaging_laser_power",
        "markpoints_repetitions",
        "markpoints_duration_ms",
        "markpoints_custom_laser_percent",
        "markpoints_point_indices",
        "markpoints_x_normalized_values",
        "markpoints_y_normalized_values",
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
    result = parse_markpoints_xml_bytes(
        xml_bytes,
        filename=xml_path.name,
    )

    output_dir = export_outputs(xml_path, result)
    warnings = collect_warnings(result)
    export_manifest(xml_path, output_dir, result, warnings)

    print_report(result)
    print_key_metadata_table(result)
    check_key_metadata_schema(result)
    print_warnings(warnings)


if __name__ == "__main__":
    main()