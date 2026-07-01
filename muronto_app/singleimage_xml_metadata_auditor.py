# singleimage_xml_metadata_auditor.py

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
    out: dict[str, Any] = {}

    if shard is None:
        return out

    for pv in shard.findall("PVStateValue"):
        key = pv.attrib.get("key", "")
        if not key:
            continue

        if "value" in pv.attrib:
            out[key] = pv.attrib.get("value")

        for indexed in pv.findall("IndexedValue"):
            index = indexed.attrib.get("index", "")
            description = indexed.attrib.get("description", "")
            indexed_key = f"{key}.{index}"

            if "value" in indexed.attrib:
                out[indexed_key] = indexed.attrib.get("value")

            if description:
                out[f"{indexed_key}.description"] = description

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


def parse_extra_parameters(frame: ET.Element) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    extra = frame.find("ExtraParameters")
    if extra is None:
        return pd.DataFrame(rows)

    for param_i, child in enumerate(list(extra), start=1):
        rows.append(
            {
                "extra_parameter_index": param_i,
                "tag": child.tag,
                "text": clean_string(child.text),
                "attributes_json": json.dumps(dict(child.attrib)),
            }
        )

    return pd.DataFrame(rows)


def parse_frames(root: ET.Element) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    frame_rows: list[dict[str, Any]] = []
    file_rows: list[dict[str, Any]] = []
    extra_rows: list[dict[str, Any]] = []
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

            extra_df = parse_extra_parameters(frame)
            if not extra_df.empty:
                for _, row in extra_df.iterrows():
                    row_dict = dict(row)
                    row_dict.update(
                        {
                            "global_frame_index": global_frame_counter,
                            "sequence_index": seq_i,
                            "sequence_cycle": sequence_cycle,
                            "frame_index_within_sequence": frame_i,
                        }
                    )
                    extra_rows.append(row_dict)

    return (
        pd.DataFrame(frame_rows),
        pd.DataFrame(file_rows),
        pd.DataFrame(extra_rows),
    )


def element_to_flat_rows(
    elem: ET.Element,
    *,
    path: str = "",
    rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
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


def parse_raw_elements(root: ET.Element) -> pd.DataFrame:
    return pd.DataFrame(element_to_flat_rows(root))


# ---------------------------------------------------------------------
# Summary helpers
# ---------------------------------------------------------------------


def get_global_value(global_state: dict[str, Any], candidates: list[str]) -> Any:
    for key in candidates:
        if key in global_state:
            return global_state[key]
    return None


def compute_timing(
    frame_df: pd.DataFrame,
    global_state: dict[str, Any],
) -> dict[str, Any]:
    frame_period_global_s = clean_float(global_state.get("framePeriod"))
    frame_rate_global_hz = (
        1.0 / frame_period_global_s
        if frame_period_global_s and frame_period_global_s > 0
        else None
    )

    if frame_df.empty or "relative_time_s" not in frame_df:
        return {
            "singleimage_frame_count_total": 0,
            "singleimage_first_frame_relative_time_s": None,
            "singleimage_last_frame_relative_time_s": None,
            "singleimage_duration_s": None,
            "singleimage_frame_period_global_s": frame_period_global_s,
            "singleimage_frame_rate_global_hz": frame_rate_global_hz,
        }

    rel = pd.to_numeric(frame_df["relative_time_s"], errors="coerce").dropna()

    first_time = float(rel.iloc[0]) if len(rel) else None
    last_time = float(rel.iloc[-1]) if len(rel) else None
    duration_s = (
        last_time - first_time
        if first_time is not None and last_time is not None
        else None
    )

    return {
        "singleimage_frame_count_total": int(len(frame_df)),
        "singleimage_first_frame_relative_time_s": first_time,
        "singleimage_last_frame_relative_time_s": last_time,
        "singleimage_duration_s": duration_s,
        "singleimage_frame_period_global_s": frame_period_global_s,
        "singleimage_frame_rate_global_hz": frame_rate_global_hz,
    }


def summarize_sequences(sequence_df: pd.DataFrame) -> dict[str, Any]:
    if sequence_df.empty:
        return {
            "singleimage_sequence_types": "",
            "singleimage_num_sequences": 0,
            "singleimage_sequence_cycle": "",
            "singleimage_sequence_time": "",
        }

    return {
        "singleimage_sequence_types": compact_unique(
            sequence_df["sequence_type"].dropna().tolist()
            if "sequence_type" in sequence_df
            else []
        ),
        "singleimage_num_sequences": int(len(sequence_df)),
        "singleimage_sequence_cycle": compact_unique(
            sequence_df["sequence_cycle"].dropna().tolist()
            if "sequence_cycle" in sequence_df
            else []
        ),
        "singleimage_sequence_time": compact_unique(
            sequence_df["sequence_time"].dropna().tolist()
            if "sequence_time" in sequence_df
            else []
        ),
    }


def summarize_channels(file_df: pd.DataFrame) -> dict[str, Any]:
    if file_df.empty:
        return {
            "singleimage_image_filename": "",
            "singleimage_files_per_frame": None,
            "singleimage_num_channels_recorded": None,
            "singleimage_channel_numbers_recorded": "",
            "singleimage_channel_names_recorded": "",
        }

    files_per_frame_counts = file_df.groupby("global_frame_index").size()
    files_per_frame = (
        int(files_per_frame_counts.mode().iloc[0])
        if len(files_per_frame_counts)
        else None
    )

    return {
        "singleimage_image_filename": compact_unique(
            file_df["filename"].dropna().tolist()
            if "filename" in file_df
            else []
        ),
        "singleimage_files_per_frame": files_per_frame,
        "singleimage_num_channels_recorded": len(
            [
                x
                for x in compact_unique(
                    file_df["channel_number"].dropna().tolist()
                ).split(", ")
                if x
            ]
        ),
        "singleimage_channel_numbers_recorded": compact_unique(
            file_df["channel_number"].dropna().tolist()
            if "channel_number" in file_df
            else []
        ),
        "singleimage_channel_names_recorded": compact_unique(
            file_df["channel_name"].dropna().tolist()
            if "channel_name" in file_df
            else []
        ),
    }


def summarize_geometry(global_state: dict[str, Any]) -> dict[str, Any]:
    pixels_per_line = clean_float(global_state.get("pixelsPerLine"))
    lines_per_frame = clean_float(global_state.get("linesPerFrame"))

    mpp_x = clean_float(global_state.get("micronsPerPixel.XAxis"))
    mpp_y = clean_float(global_state.get("micronsPerPixel.YAxis"))

    fov_x = pixels_per_line * mpp_x if pixels_per_line and mpp_x else None
    fov_y = lines_per_frame * mpp_y if lines_per_frame and mpp_y else None

    return {
        "singleimage_pixels_per_line": pixels_per_line,
        "singleimage_lines_per_frame": lines_per_frame,
        "singleimage_resolution_pix": (
            f"{int(pixels_per_line)}x{int(lines_per_frame)}"
            if pixels_per_line and lines_per_frame
            else ""
        ),
        "singleimage_microns_per_pixel_x": mpp_x,
        "singleimage_microns_per_pixel_y": mpp_y,
        "singleimage_fov_size_x_um": fov_x,
        "singleimage_fov_size_y_um": fov_y,
        "singleimage_fov_size_um": (
            f"{fov_x:.2f}x{fov_y:.2f}"
            if fov_x is not None and fov_y is not None
            else ""
        ),
    }


def summarize_global_optics(global_state: dict[str, Any]) -> dict[str, Any]:
    return {
        "singleimage_objective_name": get_global_value(
            global_state,
            ["objectiveLens", "objectiveLens.0"],
        ),
        "singleimage_objective_magnification": clean_float(
            get_global_value(global_state, ["objectiveLensMag"])
        ),
        "singleimage_objective_na": clean_float(
            get_global_value(global_state, ["objectiveLensNA"])
        ),
        "singleimage_optical_zoom": clean_float(global_state.get("opticalZoom")),
        "singleimage_laser_wavelength_nm": clean_float(
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
        "singleimage_stage_x": clean_float(
            global_state.get("positionCurrent.XAxis.0")
        ),
        "singleimage_stage_y": clean_float(
            global_state.get("positionCurrent.YAxis.0")
        ),
        "singleimage_z_focus": clean_float(
            global_state.get("positionCurrent.Z Focus.0")
            or global_state.get("positionCurrent.ZAxis.0")
        ),
        "singleimage_etl_position_global": clean_float(
            global_state.get("positionCurrent.Optotune ETL 10-30.1")
            or global_state.get("positionCurrent.Optotune ETL 10-30.0")
        ),
        "singleimage_piezo_position_global": clean_float(
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
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    root_attrs = root.attrib
    timing = compute_timing(frame_df, global_state)
    sequences = summarize_sequences(sequence_df)
    channels = summarize_channels(file_df)
    geometry = summarize_geometry(global_state)
    optics = summarize_global_optics(global_state)
    position = summarize_position(global_state)

    for variable, value in {
        "singleimage_pv_version": root_attrs.get("version"),
        "singleimage_xml_date_time": root_attrs.get("date"),
    }.items():
        add_summary_row(
            rows,
            category="file_identity",
            variable=variable,
            value=value,
            source_scope="root",
            xml_source=f"PVScan@{variable}",
            extraction_method="direct attribute",
            confidence="high" if value not in (None, "") else "low",
        )

    for variable, value in sequences.items():
        add_summary_row(
            rows,
            category="acquisition",
            variable=variable,
            value=value,
            source_scope="sequence",
            xml_source="Sequence attributes",
            extraction_method="direct attribute / counted elements",
            confidence="high" if value not in (None, "") else "medium",
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
            source_scope="frame/global",
            xml_source="Frame@relativeTime / PVStateShard.framePeriod",
            extraction_method="direct + derived",
            confidence="high" if value not in (None, "") else "medium",
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
            confidence="high" if value not in (None, "") else "low",
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
                "um" if variable.startswith("singleimage_fov") else
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
        )

    for laser_index in range(3):
        key = f"laserPower.{laser_index}"
        value = global_state.get(key, "")
        add_summary_row(
            rows,
            category="laser",
            variable=f"singleimage_laser_power_{laser_index}",
            value=value,
            source_scope="global",
            xml_source=f"PVStateShard.{key}",
            extraction_method="fixed raw laserPower index extraction",
            confidence="medium" if value != "" else "low",
        )

    key = "twophotonLaserPower.0"
    value = global_state.get(key, "")
    add_summary_row(
        rows,
        category="laser",
        variable="singleimage_twophoton_laser_power_0",
        value=value,
        source_scope="global",
        xml_source=f"PVStateShard.{key}",
        extraction_method="fixed raw twophotonLaserPower index extraction",
        confidence="medium" if value != "" else "low",
    )

    for pmt_index in range(2):
        key = f"pmtGain.{pmt_index}"
        value = global_state.get(key, "")
        add_summary_row(
            rows,
            category="pmt",
            variable=f"singleimage_pmt_gain_{pmt_index}",
            value=value,
            source_scope="global",
            xml_source=f"PVStateShard.{key}",
            extraction_method="fixed pmtGain index extraction",
            confidence="medium" if value != "" else "low",
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


def parse_singleimage_xml_bytes(
    xml_bytes: bytes,
    *,
    filename: str = "",
) -> dict[str, Any]:
    root = ET.parse(io.BytesIO(xml_bytes)).getroot()
    return parse_singleimage_root(root, filename=filename)


def parse_singleimage_xml_path(xml_path: str | Path) -> dict[str, Any]:
    path = Path(xml_path)
    root = ET.parse(path).getroot()
    return parse_singleimage_root(root, filename=path.name)


def parse_singleimage_root(
    root: ET.Element,
    *,
    filename: str = "",
) -> dict[str, Any]:
    global_state = parse_global_state(root)
    sequence_df = parse_sequences(root)
    frame_df, file_df, extra_parameters_df = parse_frames(root)
    raw_elements_df = parse_raw_elements(root)

    metadata_summary_df = build_metadata_summary(
        root=root,
        global_state=global_state,
        sequence_df=sequence_df,
        frame_df=frame_df,
        file_df=file_df,
    )

    filename = clean_string(filename)
    if filename:
        filename_row = {
            "category": "file_identity",
            "variable": "singleimage_xml_filename",
            "value": filename,
            "unit": "",
            "source_scope": "file",
            "xml_source": "selected file path",
            "extraction_method": "file name from selected SingleImage XML path",
            "confidence": "high",
            "notes": "",
        }

        metadata_summary_df = pd.concat(
            [
                pd.DataFrame([filename_row]),
                metadata_summary_df,
            ],
            ignore_index=True,
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
        "extra_parameters": extra_parameters_df,
        "sequences": sequence_df,
        "global_state": global_state_df,
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
        "frames",
        "files",
        "extra_parameters",
        "sequences",
        "global_state",
        "raw_elements",
    ):
        df = parsed.get(name)
        if isinstance(df, pd.DataFrame):
            path = output_path / f"{stem}_{name}.csv"
            df.to_csv(path, index=False)
            exported.append(path)

    return exported