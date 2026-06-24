# prairieview_xml_deep_parser.py

from __future__ import annotations

import json
import re
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Any
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd


Z_LIKE_PATTERNS = (
    "etl",
    "optotune",
    "piezo",
    "zaxis",
    "z axis",
    "z-focus",
    "z focus",
    "focus",
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


def clean_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def clean_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def flatten_pvstate_shard(shard: ET.Element | None) -> dict[str, Any]:
    out: dict[str, Any] = {}

    if shard is None:
        return out

    for pv in shard.findall("PVStateValue"):
        key = pv.attrib.get("key", "")

        if "value" in pv.attrib:
            out[key] = pv.attrib.get("value")

        # Pattern 1: PVStateValue > IndexedValue
        for indexed in pv.findall("IndexedValue"):
            index = indexed.attrib.get("index", "")
            description = indexed.attrib.get("description", "")
            indexed_key = f"{key}.{index}"

            if "value" in indexed.attrib:
                out[indexed_key] = indexed.attrib.get("value")

            if description:
                out[f"{indexed_key}.description"] = description
                out[f"{key}.{description}"] = indexed.attrib.get("value")

            for sub_group in indexed.findall("SubindexedValues"):
                sub_index = sub_group.attrib.get("index", "")

                for sub in sub_group.findall("SubindexedValue"):
                    sub_subindex = sub.attrib.get("subindex", "")
                    value = sub.attrib.get("value")
                    sub_description = sub.attrib.get("description", "")

                    generic_key = f"{indexed_key}.{sub_index}.{sub_subindex}"
                    out[generic_key] = value

                    if sub_description:
                        out[f"{generic_key}.description"] = sub_description
                        out[f"{key}.{sub_description}.{sub_subindex}"] = value

        # Pattern 2: PVStateValue > SubindexedValues
        for sub_group in pv.findall("SubindexedValues"):
            sub_index = sub_group.attrib.get("index", "")

            for sub in sub_group.findall("SubindexedValue"):
                sub_subindex = sub.attrib.get("subindex", "")
                value = sub.attrib.get("value")
                description = sub.attrib.get("description", "")

                generic_key = f"{key}.{sub_index}.{sub_subindex}"
                out[generic_key] = value

                if description:
                    out[f"{generic_key}.description"] = description
                    out[f"{key}.{description}.{sub_subindex}"] = value

    return out


def parse_global_state(root: ET.Element) -> dict[str, Any]:
    return flatten_pvstate_shard(root.find("PVStateShard"))


def parse_sequences(root: ET.Element) -> pd.DataFrame:
    rows = []
    for seq_i, seq in enumerate(root.findall("Sequence"), start=1):
        rows.append(
            {
                "sequence_index": seq_i,
                "sequence_type": seq.attrib.get("type"),
                "sequence_cycle": seq.attrib.get("cycle"),
                "sequence_time": seq.attrib.get("time"),
                "sequence_bidirectional_z": seq.attrib.get("bidirectionalZ"),
            }
        )
    return pd.DataFrame(rows)


def parse_file_elements(frame: ET.Element) -> list[dict[str, Any]]:
    files = []
    for file_i, file_el in enumerate(frame.findall("File"), start=1):
        files.append(
            {
                "file_index_within_frame": file_i,
                "filename": file_el.attrib.get("filename"),
                "channel_number": file_el.attrib.get("channel"),
                "channel_name": file_el.attrib.get("channelName"),
                "page": file_el.attrib.get("page"),
            }
        )
    return files


def parse_frames(root: ET.Element) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame_rows = []
    file_rows = []

    global_frame_counter = 0

    for seq_i, seq in enumerate(root.findall("Sequence"), start=1):
        sequence_type = seq.attrib.get("type")
        sequence_cycle = seq.attrib.get("cycle")

        for frame_i, frame in enumerate(seq.findall("Frame"), start=1):
            global_frame_counter += 1

            frame_state = flatten_pvstate_shard(frame.find("PVStateShard"))

            frame_row = {
                "global_frame_index": global_frame_counter,
                "sequence_index": seq_i,
                "sequence_type": sequence_type,
                "sequence_cycle": sequence_cycle,
                "frame_index_within_sequence": frame_i,
                "frame_index_xml": frame.attrib.get("index"),
                "relative_time_s": clean_float(frame.attrib.get("relativeTime")),
                "absolute_time": frame.attrib.get("absoluteTime"),
                "parameter_set": frame.attrib.get("parameterSet"),
                "frame_state_json": json.dumps(frame_state),
            }

            for key, value in frame_state.items():
                frame_row[f"state.{key}"] = value

            frame_rows.append(frame_row)

            for file_info in parse_file_elements(frame):
                file_info.update(
                    {
                        "global_frame_index": global_frame_counter,
                        "sequence_index": seq_i,
                        "sequence_cycle": sequence_cycle,
                        "frame_index_within_sequence": frame_i,
                    }
                )
                file_rows.append(file_info)

    return pd.DataFrame(frame_rows), pd.DataFrame(file_rows)


def get_global_value(global_state: dict[str, Any], candidates: list[str]) -> Any:
    for key in candidates:
        if key in global_state:
            return global_state[key]
    return None


def find_keys_containing(keys: list[str], patterns: tuple[str, ...]) -> list[str]:
    hits = []
    for key in keys:
        key_lower = key.lower()
        if any(pattern in key_lower for pattern in patterns):
            hits.append(key)
    return hits


def compute_timing(frame_df: pd.DataFrame, global_state: dict[str, Any]) -> dict[str, Any]:
    rel = pd.to_numeric(frame_df["relative_time_s"], errors="coerce").dropna()
    diffs = rel.diff().dropna()

    frame_period_actual_s = float(diffs.median()) if len(diffs) else None
    frame_rate_actual_hz = (
        1.0 / frame_period_actual_s
        if frame_period_actual_s and frame_period_actual_s > 0
        else None
    )

    first_time = float(rel.iloc[0]) if len(rel) else None
    last_time = float(rel.iloc[-1]) if len(rel) else None
    duration_s = (
        last_time - first_time
        if first_time is not None and last_time is not None
        else None
    )

    frame_period_global_s = clean_float(global_state.get("framePeriod"))
    frame_rate_global_hz = (
        1.0 / frame_period_global_s
        if frame_period_global_s and frame_period_global_s > 0
        else None
    )

    matches = None
    if frame_period_actual_s is not None and frame_period_global_s is not None:
        matches = abs(frame_period_actual_s - frame_period_global_s) < 1e-4

    return {
        "frame_count_total": int(len(frame_df)),
        "first_frame_relative_time_s": first_time,
        "last_frame_relative_time_s": last_time,
        "duration_s": duration_s,
        "frame_period_actual_s": frame_period_actual_s,
        "frame_rate_actual_hz": frame_rate_actual_hz,
        "frame_period_global_s": frame_period_global_s,
        "frame_rate_global_hz": frame_rate_global_hz,
        "frame_period_global_matches_actual": matches,
    }


def infer_z_values(
    frame_df: pd.DataFrame,
    global_state: dict[str, Any],
) -> pd.DataFrame:
    """
    Build frame-by-frame Z/depth audit.

    PrairieView often only writes changed state values into frame-level PVStateShard.
    So this function forward-fills from global state when a frame lacks its own value.
    """
    state_cols = [col for col in frame_df.columns if col.startswith("state.")]
    state_keys = [col.replace("state.", "", 1) for col in state_cols]

    z_state_keys = find_keys_containing(state_keys, Z_LIKE_PATTERNS)
    z_global_keys = find_keys_containing(list(global_state.keys()), Z_LIKE_PATTERNS)

    preferred_keys = list(dict.fromkeys(z_state_keys + z_global_keys))

    rows = []
    current_values: dict[str, Any] = {
        key: global_state.get(key) for key in preferred_keys if key in global_state
    }

    for _, row in frame_df.iterrows():
        frame_out = {
            "global_frame_index": row["global_frame_index"],
            "sequence_index": row["sequence_index"],
            "sequence_cycle": row["sequence_cycle"],
            "frame_index_within_sequence": row["frame_index_within_sequence"],
            "relative_time_s": row["relative_time_s"],
        }

        changed_keys = []

        for key in preferred_keys:
            col = f"state.{key}"
            if col in frame_df.columns:
                raw_value = row.get(col)
                if pd.notna(raw_value):
                    current_values[key] = raw_value
                    changed_keys.append(key)

            frame_out[key] = current_values.get(key)

        frame_out["z_changed_keys_this_frame"] = "; ".join(changed_keys)
        rows.append(frame_out)

    return pd.DataFrame(rows)


def choose_depth_column(z_audit_df: pd.DataFrame) -> str | None:
    """
    Choose the best column for inferring imaging planes.

    Prefer depth-control devices that vary across frames/cycles:
    ETL > Piezo > other varying Z-like values.
    Avoid choosing static mechanical Z focus when ETL/piezo varies.
    """
    if z_audit_df.empty:
        return None

    candidate_cols = [
        col for col in z_audit_df.columns
        if any(pattern in col.lower() for pattern in Z_LIKE_PATTERNS)
    ]

    if not candidate_cols:
        return None

    def numeric_unique_count(col: str) -> int:
        values = pd.to_numeric(z_audit_df[col], errors="coerce")
        return int(values.dropna().round(6).nunique())

    def has_numeric_values(col: str) -> bool:
        return pd.to_numeric(z_audit_df[col], errors="coerce").notna().any()

    varying_cols = [
        col for col in candidate_cols
        if numeric_unique_count(col) > 1
    ]

    # Best case: ETL varies.
    for col in varying_cols:
        if "etl" in col.lower():
            return col

    # Next best: piezo varies.
    for col in varying_cols:
        if "piezo" in col.lower():
            return col

    # Then any other varying Z-like value.
    if varying_cols:
        return varying_cols[0]

    # If nothing varies, return a static ETL/piezo/Z column if present.
    for col in candidate_cols:
        if "etl" in col.lower() and has_numeric_values(col):
            return col

    for col in candidate_cols:
        if "piezo" in col.lower() and has_numeric_values(col):
            return col

    for col in candidate_cols:
        if has_numeric_values(col):
            return col

    return None


def infer_planes(
    frame_df: pd.DataFrame,
    z_audit_df: pd.DataFrame,
    sequence_df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    depth_col = choose_depth_column(z_audit_df)

    sequence_types = set(sequence_df.get("sequence_type", pd.Series(dtype=str)).dropna())
    sequence_type_text = " ".join(str(x) for x in sequence_types)

    if depth_col is None:
        num_planes = 1
        plane_depths = [0.0]
        plane_source = "none_detected"
    else:
        depth_values = pd.to_numeric(z_audit_df[depth_col], errors="coerce")
        unique_depths = sorted(depth_values.dropna().round(6).unique().tolist())

        if "ZSeries" in sequence_type_text and len(unique_depths) > 1:
            plane_depths = unique_depths
            num_planes = len(unique_depths)
            plane_source = depth_col
        elif len(unique_depths) > 1:
            plane_depths = unique_depths
            num_planes = len(unique_depths)
            plane_source = depth_col
        else:
            num_planes = 1
            plane_depths = unique_depths or [0.0]
            plane_source = depth_col

    plane_rows = []
    for i, depth in enumerate(plane_depths, start=1):
        plane_rows.append(
            {
                "plane_number": i,
                "relative_depth_value": depth,
                "relative_depth_source": plane_source,
            }
        )

    complete_volumes = len(frame_df) // num_planes if num_planes else None
    leftover_frames = len(frame_df) % num_planes if num_planes else None

    timing = compute_timing(frame_df, {})
    frame_rate = timing.get("frame_rate_actual_hz")
    volume_rate = frame_rate / num_planes if frame_rate and num_planes else None

    summary = {
        "num_planes_inferred": num_planes,
        "plane_relative_depths": plane_depths,
        "plane_depth_source": plane_source,
        "num_volumes_complete": complete_volumes,
        "leftover_frames_after_complete_volumes": leftover_frames,
        "volume_rate_hz": volume_rate,
    }

    return pd.DataFrame(plane_rows), summary


def summarize_channels(file_df: pd.DataFrame) -> dict[str, Any]:
    if file_df.empty:
        return {
            "files_per_frame": None,
            "num_channels_recorded": None,
            "channel_numbers_recorded": [],
            "channel_names_recorded": [],
        }

    files_per_frame_counts = file_df.groupby("global_frame_index").size()
    files_per_frame = (
        int(files_per_frame_counts.mode().iloc[0])
        if len(files_per_frame_counts)
        else None
    )

    channel_numbers = sorted(
        clean for clean in file_df["channel_number"].dropna().unique().tolist()
    )
    channel_names = sorted(
        clean for clean in file_df["channel_name"].dropna().unique().tolist()
    )

    return {
        "files_per_frame": files_per_frame,
        "num_channels_recorded": len(channel_numbers),
        "channel_numbers_recorded": channel_numbers,
        "channel_names_recorded": channel_names,
    }


def summarize_geometry(global_state: dict[str, Any]) -> dict[str, Any]:
    pixels_per_line = clean_float(global_state.get("pixelsPerLine"))
    lines_per_frame = clean_float(global_state.get("linesPerFrame"))

    mpp_x = clean_float(global_state.get("micronsPerPixel.XAxis"))
    mpp_y = clean_float(global_state.get("micronsPerPixel.YAxis"))

    fov_x = pixels_per_line * mpp_x if pixels_per_line and mpp_x else None
    fov_y = lines_per_frame * mpp_y if lines_per_frame and mpp_y else None

    return {
        "pixels_per_line": pixels_per_line,
        "lines_per_frame": lines_per_frame,
        "resolution_pix": (
            f"{int(pixels_per_line)}x{int(lines_per_frame)}"
            if pixels_per_line and lines_per_frame
            else ""
        ),
        "microns_per_pixel_x": mpp_x,
        "microns_per_pixel_y": mpp_y,
        "fov_size_x_um": fov_x,
        "fov_size_y_um": fov_y,
        "fov_size_um": (
            f"{fov_x:.2f}x{fov_y:.2f}"
            if fov_x is not None and fov_y is not None
            else ""
        ),
    }


def summarize_global_optics(global_state: dict[str, Any]) -> dict[str, Any]:
    return {
        "objective_name": get_global_value(
            global_state,
            ["objectiveLens", "objectiveLens.0"],
        ),
        "objective_magnification": clean_float(
            get_global_value(global_state, ["objectiveLensMag"])
        ),
        "objective_na": clean_float(
            get_global_value(global_state, ["objectiveLensNA"])
        ),
        "optical_zoom": clean_float(global_state.get("opticalZoom")),
        "laser_wavelength_nm": clean_float(
            get_global_value(
                global_state,
                [
                    "laserWavelength",
                    "laserWavelength.0",
                    "laserWavelength.Excitation 1",
                    "laserWavelength.DeepSee",
                ],
            )
        ),
    }


def summarize_position(global_state: dict[str, Any]) -> dict[str, Any]:
    return {
        "stage_x": clean_float(global_state.get("positionCurrent.XAxis.0")),
        "stage_y": clean_float(global_state.get("positionCurrent.YAxis.0")),
        "z_focus": clean_float(
            global_state.get("positionCurrent.Z Focus.0")
            or global_state.get("positionCurrent.ZAxis.0")
        ),
        "etl_position_global": clean_float(
            global_state.get("positionCurrent.Optotune ETL 10-30.1")
            or global_state.get("positionCurrent.Optotune ETL 10-30.0")
        ),
        "piezo_position_global": clean_float(
            global_state.get("positionCurrent.Bruker 400 μm Piezo.1")
            or global_state.get("positionCurrent.Bruker 400 µm Piezo.1")
            or global_state.get("positionCurrent.Bruker 400 μm Piezo.0")
            or global_state.get("positionCurrent.Bruker 400 µm Piezo.0")
        ),
    }


def collect_entries(global_state: dict[str, Any], prefix: str) -> list[dict[str, Any]]:
    entries = []
    for key, value in global_state.items():
        if key == prefix or key.startswith(prefix + "."):
            entries.append({"key": key, "value": value})
    return entries


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
    if isinstance(value, (list, dict)):
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
    global_state: dict[str, Any],
    sequence_df: pd.DataFrame,
    frame_df: pd.DataFrame,
    file_df: pd.DataFrame,
    plane_df: pd.DataFrame,
    plane_summary: dict[str, Any],
) -> pd.DataFrame:
    rows = []

    timing = compute_timing(frame_df, global_state)
    channels = summarize_channels(file_df)
    geometry = summarize_geometry(global_state)
    optics = summarize_global_optics(global_state)
    position = summarize_position(global_state)

    root_attrs = root.attrib

    base_items = {
        "pv_version": root_attrs.get("version"),
        "xml_date_time": root_attrs.get("date"),
    }

    for variable, value in base_items.items():
        add_summary_row(
            rows,
            category="file_identity",
            variable=variable,
            value=value,
            source_scope="root",
            xml_source=f"PVScan@{variable}",
            extraction_method="direct attribute",
            confidence="high",
        )

    sequence_types = sequence_df["sequence_type"].dropna().unique().tolist()
    add_summary_row(
        rows,
        category="acquisition",
        variable="sequence_types",
        value=sequence_types,
        source_scope="sequence",
        xml_source="Sequence@type",
        extraction_method="direct attribute",
        confidence="high",
    )

    add_summary_row(
        rows,
        category="acquisition",
        variable="num_sequences_or_cycles",
        value=len(sequence_df),
        source_scope="sequence",
        xml_source="Sequence",
        extraction_method="counted elements",
        confidence="high",
    )

    for variable, value in timing.items():
        add_summary_row(
            rows,
            category="timing",
            variable=variable,
            value=value,
            unit=(
                "s"
                if "period" in variable
                or "time" in variable
                or "duration" in variable
                else "Hz"
                if "rate" in variable
                else ""
            ),
            source_scope=(
                "frame"
                if "actual" in variable
                or "count" in variable
                or "time" in variable
                or "duration" in variable
                else "global"
            ),
            xml_source="Frame@relativeTime / PVStateShard.framePeriod",
            extraction_method=(
                "computed from frame timestamps"
                if "actual" in variable
                or "count" in variable
                or "duration" in variable
                else "direct global PVState"
            ),
            confidence=(
                "high"
                if "actual" in variable or "count" in variable
                else "medium"
            ),
        )

    for variable, value in channels.items():
        add_summary_row(
            rows,
            category="channel",
            variable=variable,
            value=value,
            source_scope="file",
            xml_source="Frame/File",
            extraction_method="direct file attributes / grouped counts",
            confidence="high",
        )

    for variable, value in optics.items():
        add_summary_row(
            rows,
            category="optics",
            variable=variable,
            value=value,
            unit="nm" if "wavelength" in variable else "",
            source_scope="global",
            xml_source="PVStateShard",
            extraction_method="direct global PVState",
            confidence="high" if value not in (None, "") else "low",
        )

    for variable, value in geometry.items():
        add_summary_row(
            rows,
            category="imaging_geometry",
            variable=variable,
            value=value,
            unit=(
                "um"
                if variable.startswith("fov")
                else "um/pixel"
                if "microns_per_pixel" in variable
                else "pixels"
                if "pixels" in variable or "lines" in variable
                else ""
            ),
            source_scope="global/derived",
            xml_source=(
                "PVStateShard pixelsPerLine, linesPerFrame, micronsPerPixel"
            ),
            extraction_method="direct + derived",
            confidence="high" if value not in (None, "") else "low",
        )

    for variable, value in position.items():
        add_summary_row(
            rows,
            category="position",
            variable=variable,
            value=value,
            unit="um",
            source_scope="global",
            xml_source="PVStateShard.positionCurrent",
            extraction_method="direct global PVState",
            confidence="medium",
            notes=(
                "Global position may represent initial/current state, "
                "not necessarily frame-confirmed."
            ),
        )

    # ------------------------------------------------------------
    # Laser power: fixed raw PrairieView power rows
    # ------------------------------------------------------------
    # These rows intentionally preserve PrairieView's indexed structure.
    # They do not try to infer laser names from descriptions.
    # Missing XML values are left blank.
    for laser_index in range(3):
        key = f"laserPower.{laser_index}"
        value = global_state.get(key, "")

        add_summary_row(
            rows,
            category="laser",
            variable=f"laser_power_{laser_index}",
            value=value,
            source_scope="global",
            xml_source=f"PVStateShard.{key}",
            extraction_method="fixed raw laserPower index extraction",
            confidence="medium" if value != "" else "low",
            notes=(
                "Blank means this laserPower index was not present in the XML."
                if value == ""
                else ""
            ),
        )

    key = "twophotonLaserPower.0"
    value = global_state.get(key, "")
    add_summary_row(
        rows,
        category="laser",
        variable="twophoton_laser_power_0",
        value=value,
        source_scope="global",
        xml_source=f"PVStateShard.{key}",
        extraction_method="fixed raw twophotonLaserPower index extraction",
        confidence="medium" if value != "" else "low",
        notes=(
            "Blank means twophotonLaserPower.0 was not present in the XML."
            if value == ""
            else ""
        ),
    )

    # ------------------------------------------------------------
    # PMT gains: two PMTs only
    # ------------------------------------------------------------
    for pmt_index in range(2):
        key = f"pmtGain.{pmt_index}"
        value = global_state.get(key, "")

        add_summary_row(
            rows,
            category="pmt",
            variable=f"pmt_gain_{pmt_index}",
            value=value,
            source_scope="global",
            xml_source=f"PVStateShard.{key}",
            extraction_method="fixed pmtGain index extraction",
            confidence="medium" if value != "" else "low",
            notes=(
                "Blank means this pmtGain index was not present in the XML."
                if value == ""
                else ""
            ),
        )

    for variable, value in plane_summary.items():
        add_summary_row(
            rows,
            category="planes",
            variable=variable,
            value=value,
            unit="Hz" if "rate" in variable else "",
            source_scope="frame/global/inferred",
            xml_source="Sequence type + frame-level Z/ETL/Piezo state",
            extraction_method=(
                "inferred from depth values and repeated frame pattern"
            ),
            confidence=(
                "high"
                if variable in ("num_planes_inferred", "plane_relative_depths")
                else "medium"
            ),
        )

    return pd.DataFrame(rows)


def parse_prairieview_xml(xml_path: Path) -> dict[str, pd.DataFrame]:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    global_state = parse_global_state(root)
    sequence_df = parse_sequences(root)
    frame_df, file_df = parse_frames(root)
    z_audit_df = infer_z_values(frame_df, global_state)
    plane_df, plane_summary = infer_planes(frame_df, z_audit_df, sequence_df)

    session_summary_df = build_metadata_summary(
        root=root,
        global_state=global_state,
        sequence_df=sequence_df,
        frame_df=frame_df,
        file_df=file_df,
        plane_df=plane_df,
        plane_summary=plane_summary,
    )

    global_state_df = pd.DataFrame(
        [{"key": key, "value": value} for key, value in global_state.items()]
    )

    return {
        "metadata_summary": session_summary_df,
        "frames": frame_df,
        "files": file_df,
        "z_audit": z_audit_df,
        "planes": plane_df,
        "sequences": sequence_df,
        "global_state": global_state_df,
    }


def export_dataframes(xml_path: Path, dfs: dict[str, pd.DataFrame]) -> None:
    output_dir = xml_path.parent
    stem = xml_path.stem

    for name, df in dfs.items():
        out_path = output_dir / f"{stem}_{name}.csv"
        df.to_csv(out_path, index=False)
        print(f"Saved: {out_path}")


def main() -> None:
    xml_path = pick_xml_file()
    print(f"Selected: {xml_path}")

    dfs = parse_prairieview_xml(xml_path)
    export_dataframes(xml_path, dfs)

    print("\nMetadata summary preview:")
    print(dfs["metadata_summary"].to_string(index=False))


if __name__ == "__main__":
    main()