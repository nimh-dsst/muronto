# voltage_xml_metadata_auditor.py

from __future__ import annotations

import io
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pandas as pd


# ---------------------------------------------------------------------
# Basic cleaning helpers
# ---------------------------------------------------------------------


def clean_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def clean_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def clean_bool(value: Any) -> bool | None:
    text = clean_string(value).lower()
    if text == "true":
        return True
    if text == "false":
        return False
    return None


def clean_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def compact_unique(values: list[Any]) -> str:
    cleaned: list[str] = []
    for value in values:
        text = clean_string(value)
        if text and text not in cleaned:
            cleaned.append(text)
    return ", ".join(cleaned)


def child_text(parent: ET.Element | None, tag: str) -> str:
    """Safely read direct child text from an XML element."""
    if parent is None:
        return ""
    child = parent.find(tag)
    if child is None or child.text is None:
        return ""
    return clean_string(child.text)


def element_to_flat_rows(
    elem: ET.Element,
    *,
    path: str = "",
    rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Flatten an XML tree into simple audit rows.

    This is intended as a raw XML inspection table, not as the primary
    metadata output. It is helpful when a future voltage XML contains fields
    that are not yet represented in the main parser.
    """
    if rows is None:
        rows = []

    current_path = f"{path}/{elem.tag}" if path else elem.tag

    text = clean_string(elem.text)
    if text:
        rows.append(
            {
                "xml_path": current_path,
                "tag": elem.tag,
                "attribute": "",
                "value": text,
            }
        )

    for attr_name, attr_value in elem.attrib.items():
        rows.append(
            {
                "xml_path": current_path,
                "tag": elem.tag,
                "attribute": attr_name,
                "value": attr_value,
            }
        )

    for child in list(elem):
        element_to_flat_rows(child, path=current_path, rows=rows)

    return rows


# ---------------------------------------------------------------------
# Low-level XML parsers
# ---------------------------------------------------------------------


def parse_session(root: ET.Element) -> dict[str, Any]:
    """Parse root-level Voltage Recording session fields."""
    return {
        "root_tag": root.tag,
        "samples_acquired": clean_int(child_text(root, "SamplesAcquired")),
        "data_file": child_text(root, "DataFile"),
        "xml_date_time": child_text(root, "DateTime"),
        "is_csv": clean_bool(child_text(root, "IsCSV")),
        "associated_linescan_profile_file": child_text(
            root, "AssociatedLinescanProfileFile"
        ),
        "lost_data": clean_bool(child_text(root, "LostData")),
        "lost_data_beyond": clean_int(child_text(root, "LostDataBeyond")),
    }


def parse_experiment(root: ET.Element) -> dict[str, Any]:
    """Parse Experiment-level Voltage Recording acquisition fields."""
    exp = root.find("Experiment")

    if exp is None:
        return {}

    return {
        "experiment_name": child_text(exp, "Name"),
        "color_integer": clean_int(child_text(exp, "ColorInteger")),
        "rate_hz": clean_float(child_text(exp, "Rate")),
        "divider": clean_float(child_text(exp, "Divider")),
        "acquisition_time_ms": clean_float(child_text(exp, "AcquisitionTime")),
        "trigger": child_text(exp, "Trigger"),
        "trigger_count": clean_int(child_text(exp, "TriggerCount")),
        "x_axis_fit": clean_bool(child_text(exp, "XAxisFit")),
        "x_axis_period_s": clean_float(child_text(exp, "XAxisPeriod")),
        "automatically_adjust_time_when_synchronized": clean_bool(
            child_text(exp, "AutomaticallyAdjustTimeWhenSynchronized")
        ),
    }


def parse_signals(root: ET.Element) -> pd.DataFrame:
    """Parse Experiment/SignalList/VRecSignal elements into one row per signal."""
    rows: list[dict[str, Any]] = []
    exp = root.find("Experiment")

    if exp is None:
        return pd.DataFrame(rows)

    for signal_i, signal in enumerate(exp.findall("SignalList/VRecSignal"), start=1):
        unit = signal.find("Unit")
        card = clean_int(child_text(signal, "Card"))
        channel = clean_int(child_text(signal, "Channel"))

        rows.append(
            {
                "signal_index": signal_i,
                "type": child_text(signal, "Type"),
                "name": child_text(signal, "Name"),
                "color_as_argb": clean_int(child_text(signal, "ColorAsARGB")),
                "gain": clean_float(child_text(signal, "Gain")),
                "unit_name": child_text(unit, "UnitName"),
                "unit_multiplier": clean_float(child_text(unit, "Multiplier")),
                "unit_divisor": clean_float(child_text(unit, "Divisor")),
                "patchclamp_device": child_text(unit, "PatchclampDevice"),
                "patchclamp_channel": clean_int(child_text(unit, "PatchclampChannel")),
                "card": card,
                "channel": channel,
                "enabled": clean_bool(child_text(signal, "Enabled")),
                "signal_id_inferred": (
                    f"AI({card},{channel})"
                    if card is not None and channel is not None
                    else ""
                ),
            }
        )

    return pd.DataFrame(rows)


def parse_plot_configs(root: ET.Element) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parse plot/display configuration and visible signal IDs."""
    plot_rows: list[dict[str, Any]] = []
    visible_rows: list[dict[str, Any]] = []

    exp = root.find("Experiment")
    if exp is None:
        return pd.DataFrame(plot_rows), pd.DataFrame(visible_rows)

    for plot_i, plot in enumerate(exp.findall("PlotConfigList/VRPlotConfig"), start=1):
        axis0 = plot.find("Axis0")
        axis1 = plot.find("Axis1")

        plot_rows.append(
            {
                "plot_index": plot_i,
                "average": clean_int(child_text(plot, "Average")),
                "previous": clean_int(child_text(plot, "Previous")),
                "history": clean_int(child_text(plot, "History")),
                "shown_axis": clean_int(child_text(plot, "ShownAxis")),
                "axis0_autoscale_y": clean_bool(child_text(axis0, "AutoscaleY")),
                "axis0_ymin": clean_float(child_text(axis0, "YMin")),
                "axis0_ymax": clean_float(child_text(axis0, "YMax")),
                "axis1_autoscale_y": clean_bool(child_text(axis1, "AutoscaleY")),
                "axis1_ymin": clean_float(child_text(axis1, "YMin")),
                "axis1_ymax": clean_float(child_text(axis1, "YMax")),
            }
        )

        for visible_i, visible in enumerate(
            plot.findall("VisibleSignals/VRecSignalPerPlotProperties"),
            start=1,
        ):
            signal_id_elem = visible.find("SignalId")
            visible_rows.append(
                {
                    "plot_index": plot_i,
                    "visible_signal_index": visible_i,
                    "signal_id": child_text(signal_id_elem, "Value"),
                }
            )

    return pd.DataFrame(plot_rows), pd.DataFrame(visible_rows)


def parse_raw_elements(root: ET.Element) -> pd.DataFrame:
    """Return a raw flattened XML table for inspection/debugging."""
    return pd.DataFrame(element_to_flat_rows(root))


# ---------------------------------------------------------------------
# Summary / inference helpers
# ---------------------------------------------------------------------


def compute_voltage_timing(
    session: dict[str, Any],
    experiment: dict[str, Any],
) -> dict[str, Any]:
    """Compute timing metadata from sample count and sampling rate."""
    samples = session.get("samples_acquired")
    rate_hz = experiment.get("rate_hz")
    acquisition_time_ms = experiment.get("acquisition_time_ms")

    duration_s = None
    if samples is not None and rate_hz not in (None, 0):
        duration_s = samples / rate_hz

    acquisition_time_configured_s = None
    if acquisition_time_ms is not None:
        acquisition_time_configured_s = acquisition_time_ms / 1000

    duration_matches_configured = None
    duration_difference_s = None
    if duration_s is not None and acquisition_time_configured_s is not None:
        duration_difference_s = duration_s - acquisition_time_configured_s
        duration_matches_configured = abs(duration_difference_s) < 0.01

    sample_period_s = None
    if rate_hz not in (None, 0):
        sample_period_s = 1.0 / rate_hz

    return {
        "voltage_samples_acquired": samples,
        "voltage_sampling_rate_hz": rate_hz,
        "voltage_sample_period_s": sample_period_s,
        "voltage_duration_s": duration_s,
        "voltage_acquisition_time_configured_ms": acquisition_time_ms,
        "voltage_acquisition_time_configured_s": acquisition_time_configured_s,
        "voltage_duration_difference_s": duration_difference_s,
        "voltage_duration_matches_configured": duration_matches_configured,
    }


def summarize_signals(signal_df: pd.DataFrame) -> dict[str, Any]:
    """Summarize available and enabled voltage signals/channels."""
    if signal_df.empty:
        return {
            "voltage_num_channels_available": 0,
            "voltage_num_channels_enabled": 0,
            "voltage_channel_names_all": "",
            "voltage_channel_numbers_all": "",
            "voltage_channel_cards_all": "",
            "voltage_enabled_channel_names": "",
            "voltage_enabled_channel_numbers": "",
            "voltage_enabled_channel_cards": "",
            "voltage_enabled_channel_units": "",
            "voltage_enabled_channel_gains": "",
            "voltage_enabled_signal_ids_inferred": "",
        }

    enabled = signal_df[signal_df["enabled"] == True].copy()

    return {
        "voltage_num_channels_available": int(len(signal_df)),
        "voltage_num_channels_enabled": int(len(enabled)),
        "voltage_channel_names_all": compact_unique(signal_df["name"].tolist()),
        "voltage_channel_numbers_all": compact_unique(signal_df["channel"].tolist()),
        "voltage_channel_cards_all": compact_unique(signal_df["card"].tolist()),
        "voltage_enabled_channel_names": compact_unique(enabled["name"].tolist()),
        "voltage_enabled_channel_numbers": compact_unique(enabled["channel"].tolist()),
        "voltage_enabled_channel_cards": compact_unique(enabled["card"].tolist()),
        "voltage_enabled_channel_units": compact_unique(enabled["unit_name"].tolist()),
        "voltage_enabled_channel_gains": compact_unique(enabled["gain"].tolist()),
        "voltage_enabled_signal_ids_inferred": compact_unique(
            enabled["signal_id_inferred"].tolist()
        ),
    }


def summarize_display(
    plot_config_df: pd.DataFrame,
    visible_signal_df: pd.DataFrame,
) -> dict[str, Any]:
    """Summarize voltage-recorder plot/display settings."""
    visible_ids = (
        visible_signal_df["signal_id"].tolist()
        if not visible_signal_df.empty and "signal_id" in visible_signal_df
        else []
    )

    return {
        "voltage_num_plot_configs": int(len(plot_config_df)),
        "voltage_visible_signal_ids": compact_unique(visible_ids),
    }


def add_summary_row(
    rows: list[dict[str, Any]],
    *,
    category: str,
    variable: str,
    value: Any,
    unit: str = "",
    source_scope: str,
    xml_source: str,
    extraction_method: str,
    confidence: str,
    notes: str = "",
) -> None:
    if isinstance(value, list):
        value_out = ", ".join(str(x) for x in value)
    elif isinstance(value, dict):
        value_out = json.dumps(value)
    else:
        value_out = value

    rows.append(
        {
            "category": category,
            "variable": variable,
            "value": value_out,
            "unit": unit,
            "source_scope": source_scope,
            "xml_source": xml_source,
            "extraction_method": extraction_method,
            "confidence": confidence,
            "notes": notes,
        }
    )


def build_metadata_summary(
    root: ET.Element,
    session: dict[str, Any],
    experiment: dict[str, Any],
    signal_df: pd.DataFrame,
    plot_config_df: pd.DataFrame,
    visible_signal_df: pd.DataFrame,
) -> pd.DataFrame:
    """Build the table-style metadata summary used by downstream code."""
    rows: list[dict[str, Any]] = []

    timing = compute_voltage_timing(session, experiment)
    signal_summary = summarize_signals(signal_df)
    display_summary = summarize_display(plot_config_df, visible_signal_df)

    for variable, value in {
        "voltage_root_tag": session.get("root_tag"),
        "voltage_xml_datetime": session.get("xml_date_time"),
        "voltage_data_file": session.get("data_file"),
        "voltage_experiment_name": experiment.get("experiment_name"),
        "voltage_is_csv": session.get("is_csv"),
        "voltage_associated_linescan_profile_file": session.get(
            "associated_linescan_profile_file"
        ),
    }.items():
        add_summary_row(
            rows,
            category="file_identity",
            variable=variable,
            value=value,
            source_scope="root/experiment",
            xml_source="VRecSessionEntry / Experiment",
            extraction_method="direct element text",
            confidence="high" if value not in (None, "") else "low",
        )

    for variable, value in timing.items():
        if variable == "voltage_sampling_rate_hz":
            unit = "Hz"
        elif variable.endswith("_ms"):
            unit = "ms"
        elif variable.endswith("_s"):
            unit = "s"
        else:
            unit = ""

        notes = ""
        if variable == "voltage_duration_s":
            notes = "Calculated as SamplesAcquired / Experiment/Rate."
        elif variable == "voltage_duration_matches_configured":
            notes = (
                "Compares calculated duration_s with Experiment/AcquisitionTime. "
                "A mismatch may indicate early stop, synchronization behavior, or partial acquisition."
            )

        add_summary_row(
            rows,
            category="timing",
            variable=variable,
            value=value,
            unit=unit,
            source_scope="root/experiment/derived",
            xml_source="SamplesAcquired / Experiment/Rate / Experiment/AcquisitionTime",
            extraction_method="direct + calculated",
            confidence="high" if value not in (None, "") else "low",
            notes=notes,
        )

    for variable, value in {
        "voltage_trigger": experiment.get("trigger"),
        "voltage_trigger_count": experiment.get("trigger_count"),
        "voltage_lost_data": session.get("lost_data"),
        "voltage_lost_data_beyond": session.get("lost_data_beyond"),
        "voltage_automatically_adjust_time_when_synchronized": experiment.get(
            "automatically_adjust_time_when_synchronized"
        ),
        "voltage_x_axis_fit": experiment.get("x_axis_fit"),
        "voltage_x_axis_period_s": experiment.get("x_axis_period_s"),
        "voltage_divider": experiment.get("divider"),
    }.items():
        add_summary_row(
            rows,
            category="acquisition_integrity",
            variable=variable,
            value=value,
            unit="s" if variable.endswith("_s") else "",
            source_scope="root/experiment",
            xml_source="Experiment acquisition settings / root integrity flags",
            extraction_method="direct element text",
            confidence="high" if value not in (None, "") else "medium",
        )

    for variable, value in signal_summary.items():
        add_summary_row(
            rows,
            category="signals",
            variable=variable,
            value=value,
            source_scope="SignalList",
            xml_source="Experiment/SignalList/VRecSignal",
            extraction_method="direct element text / grouped counts",
            confidence="high",
        )

    for variable, value in display_summary.items():
        add_summary_row(
            rows,
            category="display",
            variable=variable,
            value=value,
            source_scope="PlotConfigList",
            xml_source="Experiment/PlotConfigList/VRPlotConfig",
            extraction_method="counted elements / direct element text",
            confidence="medium",
            notes=(
                "Visible signals describe displayed traces, not necessarily all acquired/enabled traces."
                if variable == "voltage_visible_signal_ids"
                else ""
            ),
        )

    return pd.DataFrame(rows)


def metadata_summary_to_dict(metadata_summary_df: pd.DataFrame) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if metadata_summary_df.empty:
        return out

    for _, row in metadata_summary_df.iterrows():
        variable = clean_string(row.get("variable"))
        if variable:
            out[variable] = row.get("value")

    return out


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------


def parse_voltage_xml_bytes(xml_bytes: bytes) -> dict[str, Any]:
    root = ET.parse(io.BytesIO(xml_bytes)).getroot()
    return parse_voltage_root(root)


def parse_voltage_xml_path(xml_path: str | Path) -> dict[str, Any]:
    root = ET.parse(xml_path).getroot()
    return parse_voltage_root(root)


def parse_voltage_root(root: ET.Element) -> dict[str, Any]:
    session = parse_session(root)
    experiment = parse_experiment(root)
    signal_df = parse_signals(root)

    enabled_signal_df = (
        signal_df[signal_df["enabled"] == True].copy()
        if not signal_df.empty and "enabled" in signal_df
        else pd.DataFrame()
    )

    plot_config_df, visible_signal_df = parse_plot_configs(root)
    raw_elements_df = parse_raw_elements(root)

    metadata_summary_df = build_metadata_summary(
        root=root,
        session=session,
        experiment=experiment,
        signal_df=signal_df,
        plot_config_df=plot_config_df,
        visible_signal_df=visible_signal_df,
    )

    metadata = metadata_summary_to_dict(metadata_summary_df)

    session_df = pd.DataFrame(
        [{"key": key, "value": value} for key, value in session.items()]
    )
    experiment_df = pd.DataFrame(
        [{"key": key, "value": value} for key, value in experiment.items()]
    )

    return {
        "metadata_summary": metadata_summary_df,
        "metadata": metadata,
        "session": session_df,
        "experiment": experiment_df,
        "signals": signal_df,
        "enabled_signals": enabled_signal_df,
        "plot_configs": plot_config_df,
        "visible_signals": visible_signal_df,
        "raw_elements": raw_elements_df,
    }


def export_audit_tables(
    parsed: dict[str, Any],
    output_dir: str | Path,
    stem: str,
) -> list[Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    exported: list[Path] = []
    for name in (
        "metadata_summary",
        "session",
        "experiment",
        "signals",
        "enabled_signals",
        "plot_configs",
        "visible_signals",
        "raw_elements",
    ):
        df = parsed.get(name)
        if isinstance(df, pd.DataFrame):
            path = output_path / f"{stem}_{name}.csv"
            df.to_csv(path, index=False)
            exported.append(path)

    return exported
