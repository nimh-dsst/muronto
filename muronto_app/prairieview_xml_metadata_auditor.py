# prairieview_xml_metadata_auditor.py

from __future__ import annotations

import io
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

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


# ---------------------------------------------------------------------
# Basic cleaning helpers
# ---------------------------------------------------------------------


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


# ---------------------------------------------------------------------
# XML flattening and low-level parsers
# ---------------------------------------------------------------------


def flatten_pvstate_shard(shard: ET.Element | None) -> dict[str, Any]:
    """Flatten a PrairieView PVStateShard into a dotted-key dictionary.

    Examples of generated keys:
        framePeriod
        laserPower.0
        laserPower.0.description
        positionCurrent.XAxis.0
        positionCurrent.Z Focus.0
        positionCurrent.Optotune ETL 10-30.1
    """
    out: dict[str, Any] = {}

    if shard is None:
        return out

    for pv in shard.findall("PVStateValue"):
        key = pv.attrib.get("key", "")
        if not key:
            continue

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

            # Pattern 1A: IndexedValue > SubindexedValues > SubindexedValue
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

        # Pattern 2: PVStateValue > SubindexedValues > SubindexedValue
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
    rows: list[dict[str, Any]] = []
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
    files: list[dict[str, Any]] = []
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
    frame_rows: list[dict[str, Any]] = []
    file_rows: list[dict[str, Any]] = []
    global_frame_counter = 0

    for seq_i, seq in enumerate(root.findall("Sequence"), start=1):
        sequence_type = seq.attrib.get("type")
        sequence_cycle = seq.attrib.get("cycle")

        for frame_i, frame in enumerate(seq.findall("Frame"), start=1):
            global_frame_counter += 1
            frame_state = flatten_pvstate_shard(frame.find("PVStateShard"))

            frame_row: dict[str, Any] = {
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


# ---------------------------------------------------------------------
# Summary / inference helpers
# ---------------------------------------------------------------------


def get_global_value(global_state: dict[str, Any], candidates: list[str]) -> Any:
    for key in candidates:
        if key in global_state:
            return global_state[key]
    return None


def find_keys_containing(keys: list[str], patterns: tuple[str, ...]) -> list[str]:
    return [
        key
        for key in keys
        if any(pattern in key.lower() for pattern in patterns)
    ]


def compute_timing(
    frame_df: pd.DataFrame,
    global_state: dict[str, Any],
) -> dict[str, Any]:
    if frame_df.empty or "relative_time_s" not in frame_df:
        frame_period_global_s = clean_float(global_state.get("framePeriod"))
        frame_rate_global_hz = (
            1.0 / frame_period_global_s
            if frame_period_global_s and frame_period_global_s > 0
            else None
        )
        return {
            "frame_count_total": 0,
            "first_frame_relative_time_s": None,
            "last_frame_relative_time_s": None,
            "duration_s": None,
            "frame_period_actual_s": None,
            "frame_rate_actual_hz": None,
            "frame_period_global_s": frame_period_global_s,
            "frame_rate_global_hz": frame_rate_global_hz,
            "frame_period_global_matches_actual": None,
        }

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
    if frame_df.empty:
        return pd.DataFrame()

    state_cols = [col for col in frame_df.columns if col.startswith("state.")]
    state_keys = [col.replace("state.", "", 1) for col in state_cols]

    z_state_keys = find_keys_containing(state_keys, Z_LIKE_PATTERNS)
    z_global_keys = find_keys_containing(list(global_state.keys()), Z_LIKE_PATTERNS)
    preferred_keys = list(dict.fromkeys(z_state_keys + z_global_keys))

    rows: list[dict[str, Any]] = []
    current_values: dict[str, Any] = {
        key: global_state.get(key)
        for key in preferred_keys
        if key in global_state
    }

    for _, row in frame_df.iterrows():
        frame_out: dict[str, Any] = {
            "global_frame_index": row["global_frame_index"],
            "sequence_index": row["sequence_index"],
            "sequence_cycle": row["sequence_cycle"],
            "frame_index_within_sequence": row["frame_index_within_sequence"],
            "relative_time_s": row["relative_time_s"],
        }

        changed_keys: list[str] = []

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
    if z_audit_df.empty:
        return None

    candidate_cols = [
        col
        for col in z_audit_df.columns
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
        col
        for col in candidate_cols
        if numeric_unique_count(col) > 1
    ]

    for col in varying_cols:
        if "etl" in col.lower() or "optotune" in col.lower():
            return col

    for col in varying_cols:
        if "piezo" in col.lower():
            return col

    if varying_cols:
        return varying_cols[0]

    for col in candidate_cols:
        if (
            "etl" in col.lower() or "optotune" in col.lower()
        ) and has_numeric_values(col):
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
    global_state: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    depth_col = choose_depth_column(z_audit_df)

    sequence_types = set(
        sequence_df.get("sequence_type", pd.Series(dtype=str)).dropna()
    )
    sequence_type_text = " ".join(str(x) for x in sequence_types)
    is_zseries = "ZSeries" in sequence_type_text

    plane_source = depth_col or "none_detected"

    def z_focus_value() -> float | None:
        return clean_float(
            global_state.get("positionCurrent.Z Focus.0")
            or global_state.get("positionCurrent.ZAxis.0")
        )

    def global_laser_power_0() -> float | None:
        return clean_float(global_state.get("laserPower.0"))

    def frame_state_value(
        frame_row: pd.Series,
        state_key: str,
    ) -> float | None:
        col = f"state.{state_key}"
        if col not in frame_row:
            return None
        return clean_float(frame_row.get(col))

    def global_state_value(state_key: str | None) -> float | None:
        if not state_key:
            return None
        return clean_float(global_state.get(state_key))

    def representative_zseries_frames(num_planes: int) -> pd.DataFrame:
        if frame_df.empty:
            return pd.DataFrame()

        frames_per_sequence = (
            frame_df.groupby("sequence_index")["frame_index_within_sequence"]
            .max()
            .dropna()
        )

        representative_sequences = frames_per_sequence[
            frames_per_sequence == num_planes
        ]

        if len(representative_sequences):
            representative_sequence_index = representative_sequences.index[0]
        else:
            representative_sequence_index = frame_df["sequence_index"].iloc[0]

        return (
            frame_df[
                frame_df["sequence_index"] == representative_sequence_index
            ]
            .sort_values("frame_index_within_sequence")
            .head(num_planes)
        )

    focus = z_focus_value()
    default_laser = global_laser_power_0()

    plane_depths: list[float | None] = []
    plane_relative_depths: list[float | None] = []
    laser_power_at_plane_depths: list[float | None] = []

    if frame_df.empty:
        num_planes = 1
        plane_depths = [focus if focus is not None else 0.0]
        plane_relative_depths = [0.0]
        laser_power_at_plane_depths = [default_laser]

    elif not is_zseries:
        num_planes = 1
        plane_depths = [focus if focus is not None else 0.0]
        plane_relative_depths = [0.0]
        laser_power_at_plane_depths = [default_laser]

    else:
        frames_per_sequence = (
            frame_df.groupby("sequence_index")["frame_index_within_sequence"]
            .max()
            .dropna()
        )

        num_planes = (
            int(frames_per_sequence.mode().iloc[0])
            if len(frames_per_sequence)
            else 1
        )

        depth_col_text = clean_string(depth_col).lower()
        global_depth_value = global_state_value(depth_col)

        frames = representative_zseries_frames(num_planes)

        for _, frame_row in frames.iterrows():
            frame_depth_value = (
                frame_state_value(frame_row, depth_col)
                if depth_col
                else None
            )

            frame_laser_value = frame_state_value(frame_row, "laserPower.0")
            laser_value = (
                frame_laser_value
                if frame_laser_value is not None
                else default_laser
            )

            if "etl" in depth_col_text or "optotune" in depth_col_text:
                relative_depth = (
                    frame_depth_value
                    if frame_depth_value is not None
                    else global_depth_value
                )
                if relative_depth is None:
                    relative_depth = 0.0

                if focus is not None:
                    plane_depth = round(focus + relative_depth, 6)
                else:
                    plane_depth = relative_depth

            elif "piezo" in depth_col_text:
                plane_depth = (
                    frame_depth_value
                    if frame_depth_value is not None
                    else focus
                )

                if plane_depth is None:
                    plane_depth = 0.0

                relative_depth = (
                    round(plane_depth - focus, 6)
                    if focus is not None
                    else None
                )

                if plane_source == depth_col and frame_depth_value is None:
                    plane_source = f"{depth_col} + Z Focus fallback"

            else:
                raw_depth = (
                    frame_depth_value
                    if frame_depth_value is not None
                    else global_depth_value
                )

                if raw_depth is None:
                    raw_depth = 0.0

                if focus is not None:
                    plane_depth = round(focus + raw_depth, 6)
                    relative_depth = raw_depth
                else:
                    plane_depth = raw_depth
                    relative_depth = None

            plane_depths.append(plane_depth)
            plane_relative_depths.append(relative_depth)
            laser_power_at_plane_depths.append(laser_value)

        if len(plane_depths) < num_planes:
            missing = num_planes - len(plane_depths)
            plane_depths.extend([focus if focus is not None else 0.0] * missing)
            plane_relative_depths.extend([0.0] * missing)
            laser_power_at_plane_depths.extend([default_laser] * missing)

    plane_rows = [
        {
            "plane_index_in_volume": i,
            "frame_index_in_volume": i,
            "plane_depth": plane_depth,
            "plane_relative_depth": relative_depth,
            "laser_power": laser_power,
            "plane_depth_source": plane_source,
            "laser_power_source": (
                "Frame laserPower.0 if present; "
                "otherwise global laserPower.0"
            ),
        }
        for i, (plane_depth, relative_depth, laser_power) in enumerate(
            zip(
                plane_depths,
                plane_relative_depths,
                laser_power_at_plane_depths,
            ),
            start=1,
        )
    ]

    complete_volumes = len(frame_df) // num_planes if num_planes else None
    leftover_frames = len(frame_df) % num_planes if num_planes else None

    timing = compute_timing(frame_df, {})
    frame_rate = timing.get("frame_rate_actual_hz")
    volume_rate = frame_rate / num_planes if frame_rate and num_planes else None

    summary = {
        "num_planes_inferred": num_planes,
        "plane_depths": plane_depths,
        "plane_relative_depths": plane_relative_depths,
        "laser_power_at_plane_depths": laser_power_at_plane_depths,
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
            "channel_numbers_recorded": "",
            "channel_names_recorded": "",
        }

    files_per_frame_counts = file_df.groupby("global_frame_index").size()
    files_per_frame = (
        int(files_per_frame_counts.mode().iloc[0])
        if len(files_per_frame_counts)
        else None
    )

    channel_numbers = compact_unique(
        sorted(file_df["channel_number"].dropna().unique().tolist())
    )
    channel_names = compact_unique(
        sorted(file_df["channel_name"].dropna().unique().tolist())
    )

    return {
        "files_per_frame": files_per_frame,
        "num_channels_recorded": len([x for x in channel_numbers.split(", ") if x]),
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
    global_state: dict[str, Any],
    sequence_df: pd.DataFrame,
    frame_df: pd.DataFrame,
    file_df: pd.DataFrame,
    plane_df: pd.DataFrame,
    plane_summary: dict[str, Any],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    timing = compute_timing(frame_df, global_state)
    channels = summarize_channels(file_df)
    geometry = summarize_geometry(global_state)
    optics = summarize_global_optics(global_state)
    position = summarize_position(global_state)

    root_attrs = root.attrib

    for variable, value in {
        "pv_version": root_attrs.get("version"),
        "xml_date_time": root_attrs.get("date"),
    }.items():
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

    sequence_types = compact_unique(
        sequence_df["sequence_type"].dropna().unique().tolist()
        if "sequence_type" in sequence_df
        else []
    )
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
                "Hz" if "rate" in variable else
                "s" if (
                    "period" in variable
                    or "time" in variable
                    or "duration" in variable
                ) else ""
            ),
            source_scope=(
                "frame"
                if (
                    "actual" in variable
                    or "count" in variable
                    or "time" in variable
                    or "duration" in variable
                    or "matches" in variable
                )
                else "global"
            ),
            xml_source="Frame@relativeTime / PVStateShard.framePeriod",
            extraction_method=(
                "computed from frame timestamps"
                if (
                    "actual" in variable
                    or "count" in variable
                    or "duration" in variable
                    or "matches" in variable
                )
                else "direct global PVState"
            ),
            confidence="high" if (
                "actual" in variable
                or "count" in variable
                or "matches" in variable
            ) else "medium",
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
                "um" if variable.startswith("fov") else
                "um/pixel" if "microns_per_pixel" in variable else
                "pixels" if "pixels" in variable or "lines" in variable else ""
            ),
            source_scope="global/derived",
            xml_source="PVStateShard pixelsPerLine, linesPerFrame, micronsPerPixel",
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
            notes="Global position may represent initial/current state, not necessarily frame-confirmed.",
        )

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
                if value == "" else ""
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
            if value == "" else ""
        ),
    )

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
                if value == "" else ""
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
            extraction_method="inferred from depth values and repeated frame pattern",
            confidence=(
                "high"
                if variable in (
                    "num_planes_inferred",
                    "plane_depths",
                    "plane_relative_depths",
                    "laser_power_at_plane_depths",
                )                else "medium"
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


def parse_prairieview_xml_bytes(xml_bytes: bytes) -> dict[str, Any]:
    root = ET.parse(io.BytesIO(xml_bytes)).getroot()
    return parse_prairieview_root(root)


def parse_prairieview_xml_path(xml_path: str | Path) -> dict[str, Any]:
    root = ET.parse(xml_path).getroot()
    return parse_prairieview_root(root)


def parse_prairieview_root(root: ET.Element) -> dict[str, Any]:
    global_state = parse_global_state(root)
    sequence_df = parse_sequences(root)
    frame_df, file_df = parse_frames(root)
    z_audit_df = infer_z_values(frame_df, global_state)
    plane_df, plane_summary = infer_planes(
        frame_df,
        z_audit_df,
        sequence_df,
        global_state,
    )

    metadata_summary_df = build_metadata_summary(
        root=root,
        global_state=global_state,
        sequence_df=sequence_df,
        frame_df=frame_df,
        file_df=file_df,
        plane_df=plane_df,
        plane_summary=plane_summary,
    )

    metadata = metadata_summary_to_dict(metadata_summary_df)

    global_state_df = pd.DataFrame(
        [{"key": key, "value": value} for key, value in global_state.items()]
    )

    return {
        "metadata_summary": metadata_summary_df,
        "metadata": metadata,
        "frames": frame_df,
        "files": file_df,
        "z_audit": z_audit_df,
        "planes": plane_df,
        "sequences": sequence_df,
        "global_state": global_state_df,
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
        "frames",
        "files",
        "z_audit",
        "planes",
        "sequences",
        "global_state",
    ):
        df = parsed.get(name)
        if isinstance(df, pd.DataFrame):
            path = output_path / f"{stem}_{name}.csv"
            df.to_csv(path, index=False)
            exported.append(path)

    return exported
