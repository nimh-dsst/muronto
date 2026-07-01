# markpoints_xml_metadata_auditor.py

from __future__ import annotations

import io
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pandas as pd


# ---------------------------------------------------------------------
# Basic cleaning helpers
# ---------------------------------------------------------------------


def clean_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def clean_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None

        parsed = float(value)

        if pd.isna(parsed):
            return None

        return parsed

    except (TypeError, ValueError):
        return None


def clean_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None

        parsed = int(float(value))

        if pd.isna(parsed):
            return None

        return parsed

    except (TypeError, ValueError):
        return None


def clean_bool(value: Any) -> bool | None:
    text = clean_string(value).lower()
    if text == "true":
        return True
    if text == "false":
        return False
    return None


def compact_unique(values: list[Any]) -> str:
    cleaned: list[str] = []
    for value in values:
        text = clean_string(value)
        if text and text not in cleaned:
            cleaned.append(text)
    return ", ".join(cleaned)


def compact_list(values: list[Any]) -> str:
    cleaned: list[str] = []
    for value in values:
        text = clean_string(value)
        if text:
            cleaned.append(text)
    return ", ".join(cleaned)


def parse_float_list(value: Any) -> list[float]:
    text = clean_string(value)
    if not text:
        return []

    values: list[float] = []
    for item in text.split(","):
        parsed = clean_float(item)
        if parsed is not None:
            values.append(parsed)

    return values


def parse_int_range_list(value: Any) -> list[int]:
    """Parse PrairieView point index strings like '1-10' or '1,3,5-7'."""
    text = clean_string(value)
    if not text:
        return []

    indices: list[int] = []
    for part in text.split(","):
        part = clean_string(part)
        if not part:
            continue

        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start = clean_int(start_text)
            end = clean_int(end_text)
            if start is None or end is None:
                continue
            step = 1 if end >= start else -1
            indices.extend(range(start, end + step, step))
            continue

        parsed = clean_int(part)
        if parsed is not None:
            indices.append(parsed)

    return indices


def element_to_flat_rows(
    elem: ET.Element,
    *,
    path: str = "",
    rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Flatten the XML tree into simple audit rows."""
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
# Filename helpers
# ---------------------------------------------------------------------


def infer_source_tseries_from_filename(filename: str) -> str:
    """Infer source TSeries token from a MarkPoints filename."""
    text = clean_string(filename)
    match = re.search(r"(TSeries-\d{8}-\d{4}-\d+)", text)
    return match.group(1) if match else ""


def infer_cycle_from_filename(filename: str) -> int | None:
    """Infer Cycle number from a MarkPoints filename."""
    text = clean_string(filename)
    match = re.search(r"Cycle(\d+)", text)
    if not match:
        return None
    return clean_int(match.group(1))


# ---------------------------------------------------------------------
# Low-level XML parsers
# ---------------------------------------------------------------------


def parse_series(root: ET.Element) -> dict[str, Any]:
    """Parse root-level PVMarkPointSeriesElements fields."""
    return {
        "root_tag": root.tag,
        "category": root.attrib.get("Category", ""),
        "name": root.attrib.get("Name", ""),
        "iterations": clean_int(root.attrib.get("Iterations")),
        "iteration_delay": clean_float(root.attrib.get("IterationDelay")),
        "calc_funct_map": clean_bool(root.attrib.get("CalcFunctMap")),
    }


def parse_markpoint_elements(root: ET.Element) -> pd.DataFrame:
    """Parse PVMarkPointElement elements."""
    rows: list[dict[str, Any]] = []

    for element_i, element in enumerate(
        root.findall("PVMarkPointElement"),
        start=1,
    ):
        custom_laser_percent_raw = element.attrib.get("CustomLaserPercent", "")
        custom_laser_percent_values = parse_float_list(custom_laser_percent_raw)

        rows.append(
            {
                "markpoint_element_index": element_i,
                "repetitions": clean_int(element.attrib.get("Repetitions")),
                "uncaging_laser": element.attrib.get("UncagingLaser", ""),
                "uncaging_laser_power": clean_float(
                    element.attrib.get("UncagingLaserPower")
                ),
                "custom_laser_percent_raw": custom_laser_percent_raw,
                "custom_laser_percent_values": ", ".join(
                    str(value) for value in custom_laser_percent_values
                ),
                "num_custom_laser_percent_values": len(
                    custom_laser_percent_values
                ),
                "trigger_frequency": element.attrib.get("TriggerFrequency", ""),
                "trigger_selection": element.attrib.get("TriggerSelection", ""),
                "trigger_count": clean_int(element.attrib.get("TriggerCount")),
                "async_sync_frequency": element.attrib.get(
                    "AsyncSyncFrequency",
                    "",
                ),
                "voltage_output_category_name": element.attrib.get(
                    "VoltageOutputCategoryName",
                    "",
                ),
                "voltage_rec_category_name": element.attrib.get(
                    "VoltageRecCategoryName",
                    "",
                ),
                "parameter_set": element.attrib.get("parameterSet", ""),
            }
        )

    return pd.DataFrame(rows)


def parse_galvo_elements(root: ET.Element) -> pd.DataFrame:
    """Parse PVGalvoPointElement elements."""
    rows: list[dict[str, Any]] = []

    markpoint_elements = root.findall("PVMarkPointElement")

    for element_i, markpoint_element in enumerate(markpoint_elements, start=1):
        for galvo_i, galvo in enumerate(
            markpoint_element.findall("PVGalvoPointElement"),
            start=1,
        ):
            indices_raw = galvo.attrib.get("Indices", "")
            indices = parse_int_range_list(indices_raw)

            rows.append(
                {
                    "markpoint_element_index": element_i,
                    "galvo_element_index": galvo_i,
                    "initial_delay_ms": clean_float(
                        galvo.attrib.get("InitialDelay")
                    ),
                    "inter_point_delay_ms": clean_float(
                        galvo.attrib.get("InterPointDelay")
                    ),
                    "duration_ms": clean_float(galvo.attrib.get("Duration")),
                    "spiral_revolutions": clean_float(
                        galvo.attrib.get("SpiralRevolutions")
                    ),
                    "all_points_at_once": clean_bool(
                        galvo.attrib.get("AllPointsAtOnce")
                    ),
                    "use_3d": clean_bool(galvo.attrib.get("Use3D")),
                    "points_label": galvo.attrib.get("Points", ""),
                    "indices_raw": indices_raw,
                    "indices_expanded": ", ".join(str(index) for index in indices),
                    "num_indices_declared": len(indices),
                    "num_point_elements": len(galvo.findall("Point")),
                }
            )

    return pd.DataFrame(rows)


def parse_points(root: ET.Element) -> pd.DataFrame:
    """Parse individual Point elements.

    Output rows preserve the order in which points appear in the XML.
    CustomLaserPercent values are matched by point order.
    """
    rows: list[dict[str, Any]] = []

    markpoint_elements = root.findall("PVMarkPointElement")

    for element_i, markpoint_element in enumerate(markpoint_elements, start=1):
        custom_laser_percent_values = parse_float_list(
            markpoint_element.attrib.get("CustomLaserPercent", "")
        )
        uncaging_laser_power = clean_float(
            markpoint_element.attrib.get("UncagingLaserPower")
        )

        for galvo_i, galvo in enumerate(
            markpoint_element.findall("PVGalvoPointElement"),
            start=1,
        ):
            for point_order, point in enumerate(galvo.findall("Point"), start=1):
                point_index = clean_int(point.attrib.get("Index"))
                custom_laser_percent = (
                    custom_laser_percent_values[point_order - 1]
                    if point_order <= len(custom_laser_percent_values)
                    else None
                )

                inferred_point_power = None
                if (
                    uncaging_laser_power is not None
                    and custom_laser_percent is not None
                ):
                    inferred_point_power = (
                        uncaging_laser_power * custom_laser_percent
                    )

                rows.append(
                    {
                        "markpoint_element_index": element_i,
                        "galvo_element_index": galvo_i,
                        "point_order_in_xml": point_order,
                        "point_index": point_index,
                        "x_normalized": clean_float(point.attrib.get("X")),
                        "y_normalized": clean_float(point.attrib.get("Y")),
                        "z": clean_float(point.attrib.get("Z")),
                        "is_spiral": clean_bool(point.attrib.get("IsSpiral")),
                        "spiral_width_normalized": clean_float(
                            point.attrib.get("SpiralWidth")
                        ),
                        "spiral_height_normalized": clean_float(
                            point.attrib.get("SpiralHeight")
                        ),
                        "spiral_size_um": clean_float(
                            point.attrib.get("SpiralSizeInMicrons")
                        ),
                        "custom_laser_percent": custom_laser_percent,
                        "uncaging_laser_power": uncaging_laser_power,
                        "inferred_point_power": inferred_point_power,
                        "inferred_point_power_method": (
                            "UncagingLaserPower * CustomLaserPercent. "
                            "Interpret cautiously; PrairieView units and "
                            "calibration are not independently verified here."
                            if inferred_point_power is not None
                            else ""
                        ),
                    }
                )

    return pd.DataFrame(rows)


def parse_raw_elements(root: ET.Element) -> pd.DataFrame:
    return pd.DataFrame(element_to_flat_rows(root))


# ---------------------------------------------------------------------
# Summary / inference helpers
# ---------------------------------------------------------------------


def first_nonblank(series: pd.Series | list[Any], default: Any = "") -> Any:
    values = series.tolist() if isinstance(series, pd.Series) else series
    for value in values:
        if value not in ("", None) and not pd.isna(value):
            return value
    return default


def numeric_summary(values: pd.Series) -> dict[str, float | None]:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return {
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
        }

    return {
        "min": float(numeric.min()),
        "max": float(numeric.max()),
        "mean": float(numeric.mean()),
        "median": float(numeric.median()),
    }


def summarize_markpoints(
    series: dict[str, Any],
    markpoint_df: pd.DataFrame,
    galvo_df: pd.DataFrame,
    point_df: pd.DataFrame,
) -> dict[str, Any]:
    """Create broad MarkPoints summary fields."""
    summary: dict[str, Any] = {
        "markpoints_root_tag": series.get("root_tag", ""),
        "markpoints_group_name": series.get("name", ""),
        "markpoints_category": series.get("category", ""),
        "markpoints_iterations": series.get("iterations"),
        "markpoints_iteration_delay_ms": series.get("iteration_delay"),
        "markpoints_calc_funct_map": series.get("calc_funct_map"),
        "markpoints_num_markpoint_elements": int(len(markpoint_df)),
        "markpoints_num_galvo_elements": int(len(galvo_df)),
        "markpoints_num_points": int(len(point_df)),
    }

    if not markpoint_df.empty:
        summary.update(
            {
                "markpoints_repetitions": first_nonblank(
                    markpoint_df["repetitions"]
                ),
                "markpoints_uncaging_laser": first_nonblank(
                    markpoint_df["uncaging_laser"]
                ),
                "markpoints_uncaging_laser_power": first_nonblank(
                    markpoint_df["uncaging_laser_power"]
                ),
                "markpoints_custom_laser_percent": first_nonblank(
                    markpoint_df["custom_laser_percent_values"]
                ),
                "markpoints_num_custom_laser_percent_values": first_nonblank(
                    markpoint_df["num_custom_laser_percent_values"]
                ),
                "markpoints_trigger_frequency": first_nonblank(
                    markpoint_df["trigger_frequency"]
                ),
                "markpoints_trigger_selection": first_nonblank(
                    markpoint_df["trigger_selection"]
                ),
                "markpoints_trigger_count": first_nonblank(
                    markpoint_df["trigger_count"]
                ),
                "markpoints_async_sync_frequency": first_nonblank(
                    markpoint_df["async_sync_frequency"]
                ),
                "markpoints_voltage_output_category_name": first_nonblank(
                    markpoint_df["voltage_output_category_name"]
                ),
                "markpoints_voltage_rec_category_name": first_nonblank(
                    markpoint_df["voltage_rec_category_name"]
                ),
                "markpoints_parameter_set": first_nonblank(
                    markpoint_df["parameter_set"]
                ),
            }
        )
    else:
        summary.update(
            {
                "markpoints_repetitions": None,
                "markpoints_uncaging_laser": "",
                "markpoints_uncaging_laser_power": None,
                "markpoints_custom_laser_percent": "",
                "markpoints_num_custom_laser_percent_values": 0,
                "markpoints_trigger_frequency": "",
                "markpoints_trigger_selection": "",
                "markpoints_trigger_count": None,
                "markpoints_async_sync_frequency": "",
                "markpoints_voltage_output_category_name": "",
                "markpoints_voltage_rec_category_name": "",
                "markpoints_parameter_set": "",
            }
        )

    if not galvo_df.empty:
        summary.update(
            {
                "markpoints_initial_delay_ms": first_nonblank(
                    galvo_df["initial_delay_ms"]
                ),
                "markpoints_inter_point_delay_ms": first_nonblank(
                    galvo_df["inter_point_delay_ms"]
                ),
                "markpoints_duration_ms": first_nonblank(
                    galvo_df["duration_ms"]
                ),
                "markpoints_spiral_revolutions": first_nonblank(
                    galvo_df["spiral_revolutions"]
                ),
                "markpoints_all_points_at_once": first_nonblank(
                    galvo_df["all_points_at_once"]
                ),
                "markpoints_use_3d": first_nonblank(galvo_df["use_3d"]),
                "markpoints_points_label": first_nonblank(
                    galvo_df["points_label"]
                ),
                "markpoints_indices_raw": first_nonblank(
                    galvo_df["indices_raw"]
                ),
                "markpoints_indices_expanded": first_nonblank(
                    galvo_df["indices_expanded"]
                ),
                "markpoints_num_indices_declared": first_nonblank(
                    galvo_df["num_indices_declared"]
                ),
            }
        )
    else:
        summary.update(
            {
                "markpoints_initial_delay_ms": None,
                "markpoints_inter_point_delay_ms": None,
                "markpoints_duration_ms": None,
                "markpoints_spiral_revolutions": None,
                "markpoints_all_points_at_once": None,
                "markpoints_use_3d": None,
                "markpoints_points_label": "",
                "markpoints_indices_raw": "",
                "markpoints_indices_expanded": "",
                "markpoints_num_indices_declared": 0,
            }
        )

    if not point_df.empty:
        x_stats = numeric_summary(point_df["x_normalized"])
        y_stats = numeric_summary(point_df["y_normalized"])
        spiral_size_stats = numeric_summary(point_df["spiral_size_um"])
        custom_laser_stats = numeric_summary(point_df["custom_laser_percent"])
        inferred_power_stats = numeric_summary(point_df["inferred_point_power"])

        summary.update(
            {
                "markpoints_point_indices": compact_list(
                    point_df["point_index"].tolist()
                ),
                "markpoints_x_normalized_values": compact_list(
                    point_df["x_normalized"].tolist()
                ),
                "markpoints_y_normalized_values": compact_list(
                    point_df["y_normalized"].tolist()
                ),
                "markpoints_custom_laser_percent_by_point": compact_list(
                    point_df["custom_laser_percent"].tolist()
                ),
                "markpoints_inferred_point_power_by_point": compact_list(
                    point_df["inferred_point_power"].tolist()
                ),
                "markpoints_spiral_size_um_values": compact_list(
                    point_df["spiral_size_um"].tolist()
                ),
                "markpoints_all_points_spiral": bool(
                    point_df["is_spiral"].dropna().all()
                ),
                "markpoints_any_points_have_z": bool(
                    pd.to_numeric(point_df["z"], errors="coerce")
                    .notna()
                    .any()
                ),
                "markpoints_x_normalized_min": x_stats["min"],
                "markpoints_x_normalized_max": x_stats["max"],
                "markpoints_y_normalized_min": y_stats["min"],
                "markpoints_y_normalized_max": y_stats["max"],
                "markpoints_spiral_size_um_min": spiral_size_stats["min"],
                "markpoints_spiral_size_um_max": spiral_size_stats["max"],
                "markpoints_custom_laser_percent_min": custom_laser_stats[
                    "min"
                ],
                "markpoints_custom_laser_percent_max": custom_laser_stats[
                    "max"
                ],
                "markpoints_inferred_point_power_min": inferred_power_stats[
                    "min"
                ],
                "markpoints_inferred_point_power_max": inferred_power_stats[
                    "max"
                ],
            }
        )
    else:
        summary.update(
            {
                "markpoints_point_indices": "",
                "markpoints_x_normalized_values": "",
                "markpoints_y_normalized_values": "",
                "markpoints_custom_laser_percent_by_point": "",
                "markpoints_inferred_point_power_by_point": "",
                "markpoints_spiral_size_um_values": "",
                "markpoints_all_points_spiral": None,
                "markpoints_any_points_have_z": False,
                "markpoints_x_normalized_min": None,
                "markpoints_x_normalized_max": None,
                "markpoints_y_normalized_min": None,
                "markpoints_y_normalized_max": None,
                "markpoints_spiral_size_um_min": None,
                "markpoints_spiral_size_um_max": None,
                "markpoints_custom_laser_percent_min": None,
                "markpoints_custom_laser_percent_max": None,
                "markpoints_inferred_point_power_min": None,
                "markpoints_inferred_point_power_max": None,
            }
        )

    return summary


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
    series: dict[str, Any],
    markpoint_df: pd.DataFrame,
    galvo_df: pd.DataFrame,
    point_df: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    summary = summarize_markpoints(
        series,
        markpoint_df,
        galvo_df,
        point_df,
    )

    categories: dict[str, str] = {
        "markpoints_root_tag": "file_identity",
        "markpoints_group_name": "file_identity",
        "markpoints_category": "file_identity",
        "markpoints_iterations": "program",
        "markpoints_iteration_delay_ms": "program",
        "markpoints_calc_funct_map": "program",
        "markpoints_num_markpoint_elements": "structure",
        "markpoints_num_galvo_elements": "structure",
        "markpoints_num_points": "structure",
        "markpoints_repetitions": "timing",
        "markpoints_initial_delay_ms": "timing",
        "markpoints_inter_point_delay_ms": "timing",
        "markpoints_duration_ms": "timing",
        "markpoints_trigger_frequency": "trigger",
        "markpoints_trigger_selection": "trigger",
        "markpoints_trigger_count": "trigger",
        "markpoints_async_sync_frequency": "trigger",
        "markpoints_uncaging_laser": "laser",
        "markpoints_uncaging_laser_power": "laser",
        "markpoints_custom_laser_percent": "laser",
        "markpoints_num_custom_laser_percent_values": "laser",
        "markpoints_custom_laser_percent_by_point": "laser",
        "markpoints_inferred_point_power_by_point": "laser",
        "markpoints_inferred_point_power_min": "laser",
        "markpoints_inferred_point_power_max": "laser",
        "markpoints_custom_laser_percent_min": "laser",
        "markpoints_custom_laser_percent_max": "laser",
        "markpoints_all_points_at_once": "spatial_pattern",
        "markpoints_use_3d": "spatial_pattern",
        "markpoints_points_label": "spatial_pattern",
        "markpoints_indices_raw": "spatial_pattern",
        "markpoints_indices_expanded": "spatial_pattern",
        "markpoints_num_indices_declared": "spatial_pattern",
        "markpoints_point_indices": "spatial_pattern",
        "markpoints_all_points_spiral": "spatial_pattern",
        "markpoints_spiral_revolutions": "spatial_pattern",
        "markpoints_spiral_size_um_values": "spatial_pattern",
        "markpoints_spiral_size_um_min": "spatial_pattern",
        "markpoints_spiral_size_um_max": "spatial_pattern",
        "markpoints_x_normalized_values": "spatial_position",
        "markpoints_y_normalized_values": "spatial_position",
        "markpoints_x_normalized_min": "spatial_position",
        "markpoints_x_normalized_max": "spatial_position",
        "markpoints_y_normalized_min": "spatial_position",
        "markpoints_y_normalized_max": "spatial_position",
        "markpoints_any_points_have_z": "spatial_position",
        "markpoints_voltage_output_category_name": "synchronization",
        "markpoints_voltage_rec_category_name": "synchronization",
        "markpoints_parameter_set": "program",
    }

    units: dict[str, str] = {
        "markpoints_iteration_delay_ms": "ms",
        "markpoints_initial_delay_ms": "ms",
        "markpoints_inter_point_delay_ms": "ms",
        "markpoints_duration_ms": "ms",
        "markpoints_spiral_size_um_values": "um",
        "markpoints_spiral_size_um_min": "um",
        "markpoints_spiral_size_um_max": "um",
    }

    notes: dict[str, str] = {
        "markpoints_inter_point_delay_ms": (
            "Interpret cautiously when AllPointsAtOnce is True."
        ),
        "markpoints_uncaging_laser_power": (
            "Raw PrairieView UncagingLaserPower value; units/calibration are "
            "not independently verified by this parser."
        ),
        "markpoints_inferred_point_power_by_point": (
            "Calculated as UncagingLaserPower * CustomLaserPercent. "
            "Interpret cautiously unless this relationship is verified."
        ),
        "markpoints_inferred_point_power_min": (
            "Calculated from inferred point powers; interpret cautiously."
        ),
        "markpoints_inferred_point_power_max": (
            "Calculated from inferred point powers; interpret cautiously."
        ),
        "markpoints_x_normalized_values": (
            "X appears to be normalized MarkPoints coordinate, not microns."
        ),
        "markpoints_y_normalized_values": (
            "Y appears to be normalized MarkPoints coordinate, not microns."
        ),
        "markpoints_any_points_have_z": (
            "Use3D may be True even when individual Point elements lack Z."
        ),
    }

    for variable, value in summary.items():
        add_summary_row(
            rows,
            category=categories.get(variable, "markpoints"),
            variable=variable,
            value=value,
            unit=units.get(variable, ""),
            source_scope="markpoints_xml",
            xml_source="PVMarkPointSeriesElements / PVMarkPointElement / PVGalvoPointElement / Point",
            extraction_method=(
                "direct XML attribute or derived summary from point table"
            ),
            confidence=(
                "medium"
                if variable.startswith("markpoints_inferred_point_power")
                else "high"
            ),
            notes=notes.get(variable, ""),
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


def parse_markpoints_xml_bytes(
    xml_bytes: bytes,
    *,
    filename: str = "",
) -> dict[str, Any]:
    root = ET.parse(io.BytesIO(xml_bytes)).getroot()
    return parse_markpoints_root(root, filename=filename)


def parse_markpoints_xml_path(xml_path: str | Path) -> dict[str, Any]:
    path = Path(xml_path)
    root = ET.parse(path).getroot()
    return parse_markpoints_root(root, filename=path.name)


def parse_markpoints_root(
    root: ET.Element,
    *,
    filename: str = "",
) -> dict[str, Any]:
    series = parse_series(root)
    markpoint_df = parse_markpoint_elements(root)
    galvo_df = parse_galvo_elements(root)
    point_df = parse_points(root)
    raw_elements_df = parse_raw_elements(root)

    metadata_summary_df = build_metadata_summary(
        root=root,
        series=series,
        markpoint_df=markpoint_df,
        galvo_df=galvo_df,
        point_df=point_df,
    )

    metadata = metadata_summary_to_dict(metadata_summary_df)

    filename = clean_string(filename)
    if filename:
        file_row = {
            "category": "file_identity",
            "variable": "markpoints_xml_filename",
            "value": filename,
            "unit": "",
            "source_scope": "file",
            "xml_source": "selected file path",
            "extraction_method": "file name from selected MarkPoints XML path",
            "confidence": "high",
            "notes": "",
        }
        source_row = {
            "category": "file_identity",
            "variable": "markpoints_source_tseries",
            "value": infer_source_tseries_from_filename(filename),
            "unit": "",
            "source_scope": "file",
            "xml_source": "selected file path",
            "extraction_method": "inferred from MarkPoints filename",
            "confidence": "medium",
            "notes": "",
        }
        cycle_row = {
            "category": "file_identity",
            "variable": "markpoints_cycle",
            "value": infer_cycle_from_filename(filename),
            "unit": "",
            "source_scope": "file",
            "xml_source": "selected file path",
            "extraction_method": "inferred from MarkPoints filename",
            "confidence": "medium",
            "notes": "",
        }

        metadata_summary_df = pd.concat(
            [
                pd.DataFrame([file_row, source_row, cycle_row]),
                metadata_summary_df,
            ],
            ignore_index=True,
        )
        metadata = metadata_summary_to_dict(metadata_summary_df)

    series_df = pd.DataFrame(
        [{"key": key, "value": value} for key, value in series.items()]
    )

    return {
        "metadata_summary": metadata_summary_df,
        "metadata": metadata,
        "series": series_df,
        "markpoints": markpoint_df,
        "galvo_elements": galvo_df,
        "points": point_df,
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
        "series",
        "markpoints",
        "galvo_elements",
        "points",
        "raw_elements",
    ):
        df = parsed.get(name)
        if isinstance(df, pd.DataFrame):
            path = output_path / f"{stem}_{name}.csv"
            df.to_csv(path, index=False)
            exported.append(path)

    return exported