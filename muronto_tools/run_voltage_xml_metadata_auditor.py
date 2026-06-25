from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog
import json


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from muronto_app.voltage_xml_metadata_auditor import (
    parse_voltage_xml_bytes,
)


def pick_xml_file() -> Path:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    file_path = filedialog.askopenfilename(
        title="Select Voltage Recording XML file",
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
        "session",
        "experiment",
        "signals",
        "enabled_signals",
        "plot_configs",
        "visible_signals",
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

    duration_matches = str(
        metadata.get("voltage_duration_matches_configured", "")
    ).lower()

    if duration_matches == "false":
        warnings.append(
            "Actual voltage duration does not match configured acquisition time."
        )

    lost_data = str(metadata.get("voltage_lost_data", "")).lower()
    if lost_data == "true":
        warnings.append("Voltage XML reports lost data.")

    enabled_channels = metadata.get("voltage_num_channels_enabled", "")
    if str(enabled_channels) in ("", "0", "0.0"):
        warnings.append("No enabled voltage channels detected.")

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
        "voltage_xml_datetime": metadata.get("voltage_xml_datetime", ""),
        "voltage_data_file": metadata.get("voltage_data_file", ""),
        "voltage_experiment_name": metadata.get("voltage_experiment_name", ""),
        "voltage_sampling_rate_hz": metadata.get("voltage_sampling_rate_hz", ""),
        "voltage_samples_acquired": metadata.get("voltage_samples_acquired", ""),
        "voltage_duration_s": metadata.get("voltage_duration_s", ""),
        "voltage_num_channels_enabled": metadata.get(
            "voltage_num_channels_enabled", ""
        ),
        "voltage_enabled_channel_names": metadata.get(
            "voltage_enabled_channel_names", ""
        ),
        "warnings": warnings,
        "outputs": [
            "metadata_summary.csv",
            "session.csv",
            "experiment.csv",
            "signals.csv",
            "enabled_signals.csv",
            "plot_configs.csv",
            "visible_signals.csv",
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
    print("Voltage XML Metadata Auditor")
    print("========================================")
    print(f"XML datetime: {metadata.get('voltage_xml_datetime', '')}")
    print(f"Data file: {metadata.get('voltage_data_file', '')}")
    print(f"Experiment name: {metadata.get('voltage_experiment_name', '')}")
    print(f"Sampling rate: {metadata.get('voltage_sampling_rate_hz', '')} Hz")
    print(f"Samples acquired: {metadata.get('voltage_samples_acquired', '')}")
    print(f"Duration: {metadata.get('voltage_duration_s', '')} s")
    print(f"Enabled channels: {metadata.get('voltage_num_channels_enabled', '')}")
    print(f"Channel names: {metadata.get('voltage_enabled_channel_names', '')}")
    print("========================================\n")


def print_key_metadata_table(result: dict) -> None:
    metadata = result.get("metadata", {})

    variables = [
        "voltage_xml_datetime",
        "voltage_data_file",
        "voltage_experiment_name",
        "voltage_sampling_rate_hz",
        "voltage_samples_acquired",
        "voltage_duration_s",
        "voltage_acquisition_time_configured_ms",
        "voltage_acquisition_time_configured_s",
        "voltage_duration_matches_configured",
        "voltage_trigger",
        "voltage_trigger_count",
        "voltage_lost_data",
        "voltage_lost_data_beyond",
        "voltage_is_csv",
        "voltage_associated_linescan_profile_file",
        "voltage_num_channels_available",
        "voltage_num_channels_enabled",
        "voltage_channel_names_all",
        "voltage_channel_numbers_all",
        "voltage_enabled_channel_names",
        "voltage_enabled_channel_numbers",
        "voltage_enabled_channel_units",
        "voltage_enabled_channel_gains",
        "voltage_enabled_signal_ids_inferred",
        "voltage_num_plot_configs",
        "voltage_visible_signal_ids",
    ]

    print("\n===================== Key Metadata =====================")

    for variable in variables:
        print(f"{variable:<50} {metadata.get(variable, '')}")

    print("=" * 60)


def check_key_metadata_schema(result: dict) -> None:
    metadata = result.get("metadata", {})

    expected_variables = [
        "voltage_xml_datetime",
        "voltage_data_file",
        "voltage_experiment_name",
        "voltage_sampling_rate_hz",
        "voltage_samples_acquired",
        "voltage_duration_s",
        "voltage_num_channels_enabled",
        "voltage_enabled_channel_names",
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
    result = parse_voltage_xml_bytes(xml_bytes)

    output_dir = export_outputs(xml_path, result)
    warnings = collect_warnings(result)
    export_manifest(xml_path, output_dir, result, warnings)

    print_report(result)
    print_key_metadata_table(result)
    check_key_metadata_schema(result)
    print_warnings(warnings)


if __name__ == "__main__":
    main()