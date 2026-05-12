from __future__ import annotations

import re
from datetime import date, time
from typing import Any, TypedDict

import streamlit as st
from labapi import ApiError

from muronto_app.config import (
    COVERSLIP_DIAMETER_OPTIONS_KEY,
    COVERSLIP_THICKNESS_OPTIONS_KEY,
    COVERSLIP_TYPE_OPTIONS_KEY,
    CRANIAL_WINDOW_REGION_OPTIONS_KEY,
    HEADPLATE_TYPE_OPTIONS_KEY,
    LA_HOME_FOLDER_KEY,
    MEDICATION_OPTIONS_KEY,
    OPTIONS_KEY,
    OTHER_CHOICE,
    PROJECT_ID_KEY,
    SITE_OPTIONS_KEY,
    SURGEON_OPTIONS_KEY,
    VIRUS_OPTIONS_KEY,
    VIRUS_SOURCE_OPTIONS_KEY,
    choice_options,
    clean_string,
    investigator_for_user,
    normalize_options,
)
from muronto_app.labarchives import (
    SubjectRecord,
    discover_subject_records,
    find_root_config_page,
    resolve_notebook_folder,
    save_config_attachment,
    save_surgery_attachment,
)
from muronto_app.page_helpers import render_project_context
from muronto_app.state import (
    CONFIG_ATTACHMENT_STATE_KEY,
    CONFIG_PAGE_ID_STATE_KEY,
    CONFIG_PAGE_STATE_KEY,
    CONFIG_STATE_KEY,
    SELECTED_NOTEBOOK_STATE_KEY,
)
from muronto_app.subject import (
    ANIMAL_ID_KEY,
    DOB_KEY,
    EAR_TAG_KEY,
    GENOTYPE_KEY,
    SEX_KEY,
    STRAIN_OPTIONS_KEY,
)
from muronto_app.surgery import (
    AP_KEY,
    CENTER_AP_KEY,
    CENTER_ML_KEY,
    CNN_PATTERN_TEXT,
    COVERSLIP_DIAMETER_KEY,
    COVERSLIP_THICKNESS_KEY,
    COVERSLIP_TYPE_KEY,
    CRANIAL_WINDOW_IMPLANT_TYPE,
    CRANIAL_WINDOW_KEY,
    DILUTION_KEY,
    DV_KEY,
    HEADPLATE_TYPE_KEY,
    HEMISPHERE_KEY,
    HEMISPHERE_OPTIONS,
    IMPLANT_CATEGORY,
    IMPLANT_TYPE_KEY,
    IMPLANT_TYPE_OPTIONS,
    INFUSION_RATE_NLMIN_KEY,
    INFUSION_VOLUME_NL_KEY,
    ML_KEY,
    NOTES_KEY,
    POST_INFUSION_FLOW_TEST_KEY,
    POST_INFUSION_FLOW_TEST_OPTIONS,
    REGION_KEY,
    SITE_KEY,
    STOCK_TITER_KEY,
    STOCK_TITER_PATTERN_TEXT,
    SURGERY_CATEGORY_KEY,
    SURGERY_CATEGORY_OPTIONS,
    VIRAL_INJECTION_CATEGORY,
    VIRUS_ID_KEY,
    VIRUS_KEY,
    VIRUS_SOURCE_KEY,
    VIRUS_STOCK_KEY,
    WELL_TYPE_KEY,
    WELL_TYPE_OPTIONS,
    SurgeryValidationError,
    build_surgery_payload,
    format_surgery_date,
    format_surgery_time,
    medication_names,
    procedure_option_values,
    with_surgery_options,
)

st.set_page_config(page_title="Muronto Surgery", layout="centered")

SURGERY_MEDICATION_COUNT_KEY = "surgery_medication_count"
SURGERY_PROCEDURE_COUNT_KEY = "surgery_procedure_count"


class PerioperativeValues(TypedDict):
    weight_pre_g: int | float | None
    weight_post_g: int | float | None
    medications: list[dict[str, object]]
    start_time: time | None
    end_time: time | None
    bregma_lambda_dist_mm: int | float | None


class SurgicalOptionValues(TypedDict):
    sites: list[str]
    viruses: list[str]
    virus_sources: list[str]


def render_text_guidance(text: str) -> None:
    st.markdown(text)


def stable_key_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return cleaned[:48] or "value"


def render_surgeon_select(options: dict[str, list[str]]) -> str:
    choices = choice_options(options, SURGEON_OPTIONS_KEY)
    selected = st.selectbox("Surgeon", options=choices, key="surgery_surgeon")
    if selected != OTHER_CHOICE:
        return selected

    return clean_string(
        st.text_input(
            "New Surgeon",
            key="surgery_surgeon_other",
        )
    )


def render_medication_select(
    options: dict[str, list[str]],
    index: int,
) -> str:
    choices = choice_options(options, MEDICATION_OPTIONS_KEY)
    selected = st.selectbox(
        f"Medication {index}",
        options=choices,
        key=f"surgery_medication_{index}",
    )
    if selected != OTHER_CHOICE:
        return selected

    return clean_string(
        st.text_input(
            f"New Medication {index}",
            key=f"surgery_medication_{index}_other",
        )
    )


def render_surgery_date() -> date | None:
    selected_date = st.date_input(
        "Surgery Date",
        value=None,
        key="surgery_date",
        format="YYYY/MM/DD",
    )
    if isinstance(selected_date, date):
        st.write(format_surgery_date(selected_date))
        return selected_date
    return None


def render_surgery_time(label: str, key: str) -> time | None:
    selected_time = st.time_input(
        label,
        value=None,
        key=key,
        step=60,
    )
    if isinstance(selected_time, time):
        st.write(format_surgery_time(selected_time))
        return selected_time
    return None


def add_reusable_surgery_option(
    *,
    notebook: Any,
    config: dict[str, Any],
    option_key: str,
    value: str,
) -> None:
    cleaned_value = clean_string(value)
    if not cleaned_value:
        st.warning("Enter a value before adding it.")
        return

    updated_config, changed = with_surgery_options(
        config,
        surgeon="",
        sites=[cleaned_value] if option_key == SITE_OPTIONS_KEY else [],
        viruses=[cleaned_value] if option_key == VIRUS_OPTIONS_KEY else [],
        virus_sources=(
            [cleaned_value] if option_key == VIRUS_SOURCE_OPTIONS_KEY else []
        ),
        headplate_types=(
            [cleaned_value] if option_key == HEADPLATE_TYPE_OPTIONS_KEY else []
        ),
        coverslip_types=(
            [cleaned_value] if option_key == COVERSLIP_TYPE_OPTIONS_KEY else []
        ),
        coverslip_diameters=(
            [cleaned_value]
            if option_key == COVERSLIP_DIAMETER_OPTIONS_KEY
            else []
        ),
        coverslip_thicknesses=(
            [cleaned_value]
            if option_key == COVERSLIP_THICKNESS_OPTIONS_KEY
            else []
        ),
        cranial_window_regions=(
            [cleaned_value]
            if option_key == CRANIAL_WINDOW_REGION_OPTIONS_KEY
            else []
        ),
    )
    if not changed:
        return

    config_page = st.session_state.get(CONFIG_PAGE_STATE_KEY)
    if config_page is None:
        config_page = find_root_config_page(notebook)

    if config_page is None:
        st.warning(
            "Could not find muronto_config to save the reusable option."
        )
        return

    attachment_entry = save_config_attachment(
        config_page,
        updated_config,
        existing_entry=st.session_state.get(CONFIG_ATTACHMENT_STATE_KEY),
    )
    st.session_state[CONFIG_STATE_KEY] = updated_config
    st.session_state[CONFIG_ATTACHMENT_STATE_KEY] = attachment_entry
    st.session_state[CONFIG_PAGE_STATE_KEY] = config_page
    st.session_state[CONFIG_PAGE_ID_STATE_KEY] = config_page.id


def add_option_and_select(
    *,
    notebook: Any,
    config: dict[str, Any],
    option_key: str,
    value: str,
    select_key: str,
    default_key: str,
) -> None:
    cleaned_value = clean_string(value)
    if not cleaned_value:
        st.warning("Enter a value before adding it.")
        return

    add_reusable_surgery_option(
        notebook=notebook,
        config=config,
        option_key=option_key,
        value=cleaned_value,
    )
    st.session_state.pop(select_key, None)
    st.session_state[default_key] = cleaned_value
    st.rerun()


def render_select_with_immediate_other(
    *,
    label: str,
    options: dict[str, list[str]],
    options_key: str,
    widget_key: str,
    other_prompt: str,
    notebook: Any,
    config: dict[str, Any],
) -> str:
    choices = choice_options(options, options_key)
    default_key = f"{widget_key}_default"
    default_value = clean_string(st.session_state.pop(default_key, ""))
    index = choices.index(default_value) if default_value in choices else 0
    selected = st.selectbox(
        label,
        options=choices,
        index=index,
        key=widget_key,
    )
    if selected != OTHER_CHOICE:
        return selected

    new_value = st.text_input(
        other_prompt,
        key=f"{widget_key}_other",
    )
    if st.button(
        f"Add {label}",
        key=f"{widget_key}_add",
        use_container_width=True,
    ):
        add_option_and_select(
            notebook=notebook,
            config=config,
            option_key=options_key,
            value=new_value,
            select_key=widget_key,
            default_key=default_key,
        )
    return clean_string(new_value)


def render_virus_multiselect(
    *,
    options: dict[str, list[str]],
    widget_key: str,
    notebook: Any,
    config: dict[str, Any],
) -> list[str]:
    choices = choice_options(options, VIRUS_OPTIONS_KEY)
    default_key = f"{widget_key}_default"
    default_values = st.session_state.pop(default_key, None)
    selected = st.multiselect(
        "Viruses",
        options=choices,
        default=default_values if isinstance(default_values, list) else None,
        key=widget_key,
    )
    selected_viruses = [
        clean_string(virus)
        for virus in selected
        if virus != OTHER_CHOICE and clean_string(virus)
    ]

    if OTHER_CHOICE not in selected:
        return selected_viruses

    new_virus = st.text_input(
        "New Virus",
        key=f"{widget_key}_other",
    )
    if st.button(
        "Add Virus",
        key=f"{widget_key}_add",
        use_container_width=True,
    ):
        cleaned_virus = clean_string(new_virus)
        if not cleaned_virus:
            st.warning("Enter a virus before adding it.")
            return selected_viruses

        add_reusable_surgery_option(
            notebook=notebook,
            config=config,
            option_key=VIRUS_OPTIONS_KEY,
            value=cleaned_virus,
        )
        st.session_state.pop(widget_key, None)
        st.session_state[default_key] = [*selected_viruses, cleaned_virus]
        st.rerun()

    return selected_viruses


def subject_label(record: SubjectRecord) -> str:
    animal_id = record.payload.get(ANIMAL_ID_KEY, "Unknown")
    ear_tag = record.payload.get(EAR_TAG_KEY, "")
    return f"{animal_id} - Ear Tag {ear_tag}" if ear_tag else animal_id


def subject_strain_genotypes(
    payload: dict[str, str],
) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    index = 1
    while (
        f"{STRAIN_OPTIONS_KEY}_{index}" in payload
        or f"{GENOTYPE_KEY}_{index}" in payload
    ):
        strain = clean_string(payload.get(f"{STRAIN_OPTIONS_KEY}_{index}"))
        genotype = clean_string(payload.get(f"{GENOTYPE_KEY}_{index}"))
        if strain or genotype:
            pairs.append((strain, genotype))
        index += 1
    return pairs


def render_selected_subject(record: SubjectRecord) -> None:
    payload = record.payload
    st.write(f"Animal ID: {payload.get(ANIMAL_ID_KEY, '')}")
    st.write(f"Ear Tag: {payload.get(EAR_TAG_KEY, '')}")
    st.write(f"Sex: {payload.get(SEX_KEY, '')}")
    st.write(f"DOB: {payload.get(DOB_KEY, '')}")

    pairs = subject_strain_genotypes(payload)
    if not pairs:
        st.write("Strain/genotype: Not recorded")
        return

    for index, (strain, genotype) in enumerate(pairs, start=1):
        st.write(f"strain_{index}: {strain}")
        st.write(f"genotype_{index}: {genotype}")


def increment_medication_count() -> None:
    st.session_state[SURGERY_MEDICATION_COUNT_KEY] = (
        st.session_state.get(SURGERY_MEDICATION_COUNT_KEY, 1) + 1
    )


def render_medications(
    options: dict[str, list[str]],
) -> list[dict[str, object]]:
    st.session_state.setdefault(SURGERY_MEDICATION_COUNT_KEY, 1)

    medications: list[dict[str, object]] = []
    for index in range(1, st.session_state[SURGERY_MEDICATION_COUNT_KEY] + 1):
        medication = render_medication_select(options, index)
        conc_mgml = st.number_input(
            "Concentration (mg/ml)",
            min_value=0.0,
            value=None,
            step=0.1,
            key=f"surgery_medication_{index}_conc_mgml",
        )
        volume = st.number_input(
            "Volume (ml)",
            min_value=0.0,
            value=None,
            step=0.01,
            key=f"surgery_medication_{index}_volume",
        )
        medications.append(
            {
                "medication": medication,
                "conc_mgml": conc_mgml,
                "volume": volume,
            }
        )

    return medications


def render_perioperative_monitoring(
    options: dict[str, list[str]],
) -> PerioperativeValues:
    with st.expander(
        "Perioperative Monitoring & Medications",
        expanded=True,
    ):
        weight_pre_g = st.number_input(
            "Weight Pre (grams)",
            min_value=0.0,
            value=None,
            step=0.1,
            key="surgery_weight_pre_g",
        )
        weight_post_g = st.number_input(
            "Weight Post (grams)",
            min_value=0.0,
            value=None,
            step=0.1,
            key="surgery_weight_post_g",
        )

        st.markdown("#### Medications")
        if st.button(
            "Add medication",
            help="Add another medication entry.",
            use_container_width=True,
        ):
            increment_medication_count()
            st.rerun()
        medications = render_medications(options)

        start_time = render_surgery_time("Start Time", "surgery_start_time")
        end_time = render_surgery_time("End Time", "surgery_end_time")
        bregma_lambda_dist_mm = st.number_input(
            "Bregma Lambda Distance (mm)",
            min_value=0.0,
            value=None,
            step=0.1,
            key="surgery_bregma_lambda_dist_mm",
        )

    return {
        "weight_pre_g": weight_pre_g,
        "weight_post_g": weight_post_g,
        "medications": medications,
        "start_time": start_time,
        "end_time": end_time,
        "bregma_lambda_dist_mm": bregma_lambda_dist_mm,
    }


def increment_procedure_count() -> None:
    st.session_state[SURGERY_PROCEDURE_COUNT_KEY] = (
        st.session_state.get(SURGERY_PROCEDURE_COUNT_KEY, 1) + 1
    )


def procedure_injection_count_key(procedure_index: int) -> str:
    return f"surgery_procedure_{procedure_index}_injection_count"


def injection_infusion_count_key(
    procedure_index: int,
    injection_index: int,
) -> str:
    return (
        f"surgery_procedure_{procedure_index}_"
        f"injection_{injection_index}_infusion_count"
    )


def increment_injection_count(procedure_index: int) -> None:
    count_key = procedure_injection_count_key(procedure_index)
    st.session_state[count_key] = st.session_state.get(count_key, 1) + 1


def increment_infusion_count(
    procedure_index: int,
    injection_index: int,
) -> None:
    count_key = injection_infusion_count_key(
        procedure_index,
        injection_index,
    )
    st.session_state[count_key] = st.session_state.get(count_key, 1) + 1


def render_virus_attributes(
    *,
    procedure_index: int,
    injection_index: int,
    virus: str,
    options: dict[str, list[str]],
    notebook: Any,
    config: dict[str, Any],
) -> dict[str, object]:
    virus_key = (
        f"surgery_procedure_{procedure_index}_injection_{injection_index}_"
        f"virus_{stable_key_part(virus)}"
    )
    st.markdown(f"##### {virus}")
    virus_source = render_select_with_immediate_other(
        label="Virus Source",
        options=options,
        options_key=VIRUS_SOURCE_OPTIONS_KEY,
        widget_key=f"{virus_key}_source",
        other_prompt="New Virus Source",
        notebook=notebook,
        config=config,
    )
    virus_id = st.text_input(
        "Virus ID",
        key=f"{virus_key}_virus_id",
    )
    virus_stock = st.text_input(
        "Virus Stock",
        key=f"{virus_key}_virus_stock",
    )
    render_text_guidance(
        "Stock Titer must match the regex pattern "
        f"`{STOCK_TITER_PATTERN_TEXT}`, for example `2_10_13`."
    )
    stock_titer = st.text_input(
        "Stock Titer",
        key=f"{virus_key}_stock_titer",
    )
    dilution = st.text_input(
        "Dilution",
        key=f"{virus_key}_dilution",
    )
    infusion_rate_nlmin = st.number_input(
        "Infusion Rate (nl/min)",
        min_value=0.0,
        value=None,
        step=1.0,
        key=f"{virus_key}_infusion_rate_nlmin",
    )
    return {
        VIRUS_KEY: virus,
        VIRUS_SOURCE_KEY: virus_source,
        VIRUS_ID_KEY: virus_id,
        VIRUS_STOCK_KEY: virus_stock,
        STOCK_TITER_KEY: stock_titer,
        DILUTION_KEY: dilution,
        INFUSION_RATE_NLMIN_KEY: infusion_rate_nlmin,
    }


def render_infusions(
    *,
    procedure_index: int,
    injection_index: int,
) -> list[dict[str, object]]:
    count_key = injection_infusion_count_key(
        procedure_index,
        injection_index,
    )
    st.session_state.setdefault(count_key, 1)

    if st.button(
        "Add infusion location",
        key=(
            f"surgery_procedure_{procedure_index}_"
            f"injection_{injection_index}_add_infusion"
        ),
        use_container_width=True,
    ):
        increment_infusion_count(procedure_index, injection_index)
        st.rerun()

    infusions: list[dict[str, object]] = []
    for infusion_index in range(1, st.session_state[count_key] + 1):
        prefix = (
            f"surgery_procedure_{procedure_index}_"
            f"injection_{injection_index}_infusion_{infusion_index}"
        )
        st.markdown(f"##### Infusion Location {infusion_index}")
        ap = st.number_input(
            "AP",
            value=None,
            step=0.1,
            key=f"{prefix}_ap",
        )
        ml = st.number_input(
            "ML",
            value=None,
            step=0.1,
            key=f"{prefix}_ml",
        )
        dv = st.number_input(
            "DV",
            value=None,
            step=0.1,
            key=f"{prefix}_dv",
        )
        infusion_volume_nl = st.number_input(
            "Infusion Volume (nl)",
            min_value=0.0,
            value=None,
            step=10.0,
            key=f"{prefix}_infusion_volume_nl",
        )
        post_infusion_flow_test = st.selectbox(
            "Post Infusion Flow Test",
            options=POST_INFUSION_FLOW_TEST_OPTIONS,
            key=f"{prefix}_post_infusion_flow_test",
        )
        notes = st.text_input(
            "Notes",
            key=f"{prefix}_notes",
        )
        infusions.append(
            {
                AP_KEY: ap,
                ML_KEY: ml,
                DV_KEY: dv,
                INFUSION_VOLUME_NL_KEY: infusion_volume_nl,
                POST_INFUSION_FLOW_TEST_KEY: post_infusion_flow_test,
                NOTES_KEY: notes,
            }
        )
    return infusions


def render_injection(
    *,
    procedure_index: int,
    injection_index: int,
    options: dict[str, list[str]],
    notebook: Any,
    config: dict[str, Any],
) -> dict[str, object]:
    prefix = f"surgery_procedure_{procedure_index}_injection_{injection_index}"
    st.markdown(f"#### Injection {injection_index}")
    site = render_select_with_immediate_other(
        label="Site",
        options=options,
        options_key=SITE_OPTIONS_KEY,
        widget_key=f"{prefix}_site",
        other_prompt="New Site",
        notebook=notebook,
        config=config,
    )
    hemisphere = st.selectbox(
        "hemisphere",
        options=HEMISPHERE_OPTIONS,
        key=f"{prefix}_hemisphere",
    )
    selected_viruses = render_virus_multiselect(
        options=options,
        widget_key=f"{prefix}_viruses",
        notebook=notebook,
        config=config,
    )
    viruses = [
        render_virus_attributes(
            procedure_index=procedure_index,
            injection_index=injection_index,
            virus=virus,
            options=options,
            notebook=notebook,
            config=config,
        )
        for virus in selected_viruses
    ]

    st.markdown("##### Infusion Locations")
    infusions = render_infusions(
        procedure_index=procedure_index,
        injection_index=injection_index,
    )
    return {
        SITE_KEY: site,
        HEMISPHERE_KEY: hemisphere,
        "viruses": viruses,
        "infusions": infusions,
    }


def render_viral_injection_procedure(
    *,
    procedure_index: int,
    options: dict[str, list[str]],
    notebook: Any,
    config: dict[str, Any],
) -> dict[str, object]:
    count_key = procedure_injection_count_key(procedure_index)
    st.session_state.setdefault(count_key, 1)
    if st.button(
        "Add injection",
        key=f"surgery_procedure_{procedure_index}_add_injection",
        use_container_width=True,
    ):
        increment_injection_count(procedure_index)
        st.rerun()

    injections = [
        render_injection(
            procedure_index=procedure_index,
            injection_index=injection_index,
            options=options,
            notebook=notebook,
            config=config,
        )
        for injection_index in range(1, st.session_state[count_key] + 1)
    ]
    return {
        SURGERY_CATEGORY_KEY: VIRAL_INJECTION_CATEGORY,
        "injections": injections,
    }


def render_implant_type(
    *,
    procedure_index: int,
) -> str:
    choices = [*IMPLANT_TYPE_OPTIONS, OTHER_CHOICE]
    selected = st.selectbox(
        "Implant Type",
        options=choices,
        key=f"surgery_procedure_{procedure_index}_implant_type",
    )
    if selected != OTHER_CHOICE:
        return selected

    return clean_string(
        st.text_input(
            "New Implant Type",
            key=f"surgery_procedure_{procedure_index}_implant_type_other",
        )
    )


def render_cranial_window_implant(
    *,
    procedure_index: int,
    options: dict[str, list[str]],
    notebook: Any,
    config: dict[str, Any],
) -> dict[str, object]:
    prefix = f"surgery_procedure_{procedure_index}_cranial_window"
    headplate_type = render_select_with_immediate_other(
        label="Headplate Type",
        options=options,
        options_key=HEADPLATE_TYPE_OPTIONS_KEY,
        widget_key=f"{prefix}_headplate_type",
        other_prompt="New Headplate Type",
        notebook=notebook,
        config=config,
    )
    coverslip_type = render_select_with_immediate_other(
        label="Coverslip Type",
        options=options,
        options_key=COVERSLIP_TYPE_OPTIONS_KEY,
        widget_key=f"{prefix}_coverslip_type",
        other_prompt="New Coverslip Type",
        notebook=notebook,
        config=config,
    )
    coverslip_diameter = render_select_with_immediate_other(
        label="Coverslip Diameter",
        options=options,
        options_key=COVERSLIP_DIAMETER_OPTIONS_KEY,
        widget_key=f"{prefix}_coverslip_diameter",
        other_prompt="New Coverslip Diameter",
        notebook=notebook,
        config=config,
    )
    coverslip_thickness = render_select_with_immediate_other(
        label="Coverslip Thickness",
        options=options,
        options_key=COVERSLIP_THICKNESS_OPTIONS_KEY,
        widget_key=f"{prefix}_coverslip_thickness",
        other_prompt="New Coverslip Thickness",
        notebook=notebook,
        config=config,
    )
    region = render_select_with_immediate_other(
        label="Region",
        options=options,
        options_key=CRANIAL_WINDOW_REGION_OPTIONS_KEY,
        widget_key=f"{prefix}_region",
        other_prompt="New Region",
        notebook=notebook,
        config=config,
    )
    center_ap = st.number_input(
        "Center AP",
        value=None,
        step=0.1,
        key=f"{prefix}_center_ap",
    )
    center_ml = st.number_input(
        "Center ML",
        value=None,
        step=0.1,
        key=f"{prefix}_center_ml",
    )
    well_type = st.selectbox(
        "Well Type",
        options=WELL_TYPE_OPTIONS,
        key=f"{prefix}_well_type",
    )
    notes = st.text_input(
        "Notes",
        key=f"{prefix}_notes",
    )

    return {
        HEADPLATE_TYPE_KEY: headplate_type,
        COVERSLIP_TYPE_KEY: coverslip_type,
        COVERSLIP_DIAMETER_KEY: coverslip_diameter,
        COVERSLIP_THICKNESS_KEY: coverslip_thickness,
        REGION_KEY: region,
        CENTER_AP_KEY: center_ap,
        CENTER_ML_KEY: center_ml,
        WELL_TYPE_KEY: well_type,
        NOTES_KEY: notes,
    }


def render_implant_procedure(
    *,
    procedure_index: int,
    options: dict[str, list[str]],
    notebook: Any,
    config: dict[str, Any],
) -> dict[str, object]:
    implant_type = render_implant_type(procedure_index=procedure_index)
    procedure: dict[str, object] = {
        SURGERY_CATEGORY_KEY: IMPLANT_CATEGORY,
        IMPLANT_TYPE_KEY: implant_type,
    }
    if implant_type != CRANIAL_WINDOW_IMPLANT_TYPE:
        st.info("Only Cranial Window implant fields are implemented yet.")
        return procedure

    procedure[CRANIAL_WINDOW_KEY] = render_cranial_window_implant(
        procedure_index=procedure_index,
        options=options,
        notebook=notebook,
        config=config,
    )
    return procedure


def render_surgical_procedures(
    *,
    options: dict[str, list[str]],
    notebook: Any,
    config: dict[str, Any],
) -> list[dict[str, object]]:
    st.subheader("Surgical Procedures")
    st.session_state.setdefault(SURGERY_PROCEDURE_COUNT_KEY, 1)
    if st.button(
        "Add surgical procedure",
        key="surgery_add_procedure",
        use_container_width=True,
    ):
        increment_procedure_count()
        st.rerun()

    procedures: list[dict[str, object]] = []
    for procedure_index in range(
        1,
        st.session_state[SURGERY_PROCEDURE_COUNT_KEY] + 1,
    ):
        is_latest_procedure = (
            procedure_index == st.session_state[SURGERY_PROCEDURE_COUNT_KEY]
        )
        with st.expander(
            f"Procedure {procedure_index}",
            expanded=is_latest_procedure,
        ):
            category = st.selectbox(
                "Subject Category",
                options=SURGERY_CATEGORY_OPTIONS,
                key=f"surgery_procedure_{procedure_index}_category",
            )
            if category == IMPLANT_CATEGORY:
                procedures.append(
                    render_implant_procedure(
                        procedure_index=procedure_index,
                        options=options,
                        notebook=notebook,
                        config=config,
                    )
                )
                continue

            procedures.append(
                render_viral_injection_procedure(
                    procedure_index=procedure_index,
                    options=options,
                    notebook=notebook,
                    config=config,
                )
            )
    return procedures


def save_reusable_surgery_options(
    *,
    notebook: Any,
    config: dict[str, Any],
    surgeon: str,
    medications: list[str],
    sites: list[str],
    viruses: list[str],
    virus_sources: list[str],
    headplate_types: list[str],
    coverslip_types: list[str],
    coverslip_diameters: list[str],
    coverslip_thicknesses: list[str],
    cranial_window_regions: list[str],
) -> None:
    updated_config, changed = with_surgery_options(
        config,
        surgeon=surgeon,
        medications=medications,
        sites=sites,
        viruses=viruses,
        virus_sources=virus_sources,
        headplate_types=headplate_types,
        coverslip_types=coverslip_types,
        coverslip_diameters=coverslip_diameters,
        coverslip_thicknesses=coverslip_thicknesses,
        cranial_window_regions=cranial_window_regions,
    )
    if not changed:
        return

    config_page = st.session_state.get(CONFIG_PAGE_STATE_KEY)
    if config_page is None:
        config_page = find_root_config_page(notebook)

    if config_page is None:
        st.warning(
            "Saved the surgery record, but could not find muronto_config to "
            "save reusable surgery options."
        )
        return

    attachment_entry = save_config_attachment(
        config_page,
        updated_config,
        existing_entry=st.session_state.get(CONFIG_ATTACHMENT_STATE_KEY),
    )
    st.session_state[CONFIG_STATE_KEY] = updated_config
    st.session_state[CONFIG_ATTACHMENT_STATE_KEY] = attachment_entry
    st.session_state[CONFIG_PAGE_STATE_KEY] = config_page
    st.session_state[CONFIG_PAGE_ID_STATE_KEY] = config_page.id


def load_subject_records(
    notebook: Any,
    project: dict[str, str],
) -> list[SubjectRecord] | None:
    try:
        home_folder = resolve_notebook_folder(
            notebook,
            project[LA_HOME_FOLDER_KEY],
        )
        return discover_subject_records(home_folder)
    except ApiError as exc:
        st.error(f"Unable to load subjects from LabArchives: {exc}")
    except ValueError as exc:
        st.error(str(exc))
    return None


def render_surgery_form(
    *,
    notebook: Any,
    config: dict[str, Any],
    project: dict[str, str],
    investigator: str,
    selected_subject: SubjectRecord,
) -> None:
    subject_payload = selected_subject.payload
    options = normalize_options(config.get(OPTIONS_KEY))

    with st.expander("Surgery Details", expanded=True):
        surgeon = render_surgeon_select(options)
        surgery_date = render_surgery_date()

        render_text_guidance(
            "PreOp CNN must match the regex pattern "
            f"`{CNN_PATTERN_TEXT}`, for example `123456`."
        )
        preop_cnn = st.text_input("PreOp CNN", key="surgery_preop_cnn")

        render_text_guidance(
            "PostOp CNN must match the regex pattern "
            f"`{CNN_PATTERN_TEXT}`, for example `123456`."
        )
        postop_cnn = st.text_input("PostOp CNN", key="surgery_postop_cnn")

    perioperative_values = render_perioperative_monitoring(options)
    surgical_procedures = render_surgical_procedures(
        options=options,
        notebook=notebook,
        config=config,
    )

    submitted = st.button(
        "Save surgery record",
        type="primary",
        use_container_width=True,
    )
    if not submitted:
        return

    try:
        payload = build_surgery_payload(
            project_id=project[PROJECT_ID_KEY],
            investigator=investigator,
            animal_id=subject_payload.get(ANIMAL_ID_KEY, ""),
            ear_tag=subject_payload.get(EAR_TAG_KEY, ""),
            surgeon=surgeon,
            surgery_date=surgery_date,
            preop_cnn=preop_cnn,
            postop_cnn=postop_cnn,
            weight_pre_g=perioperative_values["weight_pre_g"],
            weight_post_g=perioperative_values["weight_post_g"],
            medications=perioperative_values["medications"],
            start_time=perioperative_values["start_time"],
            end_time=perioperative_values["end_time"],
            bregma_lambda_dist_mm=perioperative_values[
                "bregma_lambda_dist_mm"
            ],
            surgical_procedures=surgical_procedures,
        )
    except SurgeryValidationError as exc:
        st.error("Complete the surgery form before saving the record.")
        for error in exc.errors:
            st.caption(error)
        return

    try:
        result = save_surgery_attachment(selected_subject.page, payload)
    except ApiError as exc:
        st.error(f"Unable to save the surgery record: {exc}")
        return
    except ValueError as exc:
        st.error(str(exc))
        return

    try:
        (
            sites,
            viruses,
            virus_sources,
            headplate_types,
            coverslip_types,
            coverslip_diameters,
            coverslip_thicknesses,
            cranial_window_regions,
        ) = procedure_option_values(payload)
        save_reusable_surgery_options(
            notebook=notebook,
            config=config,
            surgeon=clean_string(payload["surgeon"]),
            medications=medication_names(payload),
            sites=sites,
            viruses=viruses,
            virus_sources=virus_sources,
            headplate_types=headplate_types,
            coverslip_types=coverslip_types,
            coverslip_diameters=coverslip_diameters,
            coverslip_thicknesses=coverslip_thicknesses,
            cranial_window_regions=cranial_window_regions,
        )
    except ApiError as exc:
        st.warning(
            "Saved the surgery record, but could not save the reusable "
            f"surgery options to muronto_config: {exc}"
        )

    action = "Created" if result.created else "Updated"
    st.success(f"{action} surgery record for `{payload[ANIMAL_ID_KEY]}`.")
    with st.expander("Surgery JSON", expanded=True):
        st.json(payload)


def main() -> None:
    context = render_project_context("Surgery")
    if context is None:
        return

    notebook = st.session_state.get(SELECTED_NOTEBOOK_STATE_KEY)
    _user, config, project = context
    if notebook is None or not isinstance(config, dict):
        st.warning("Select a notebook and complete muronto_config first.")
        st.page_link("Project.py", label="Open Project")
        return

    investigator = investigator_for_user(config, _user.email)

    st.subheader("Surgery")
    st.write(f"Project ID: {project[PROJECT_ID_KEY]}")
    st.write(f"Investigator: {investigator}")

    with st.expander("Subject Information", expanded=True):
        subject_records = load_subject_records(notebook, project)
        if subject_records is None:
            return
        if not subject_records:
            st.info(
                "No subject JSON records were found in the project folder."
            )
            return

        selected_subject_index = st.selectbox(
            "Subject",
            options=list(range(len(subject_records))),
            format_func=lambda index: subject_label(subject_records[index]),
            key="surgery_subject",
        )
        selected_subject = subject_records[selected_subject_index]
        render_selected_subject(selected_subject)

    render_surgery_form(
        notebook=notebook,
        config=config,
        project=project,
        investigator=investigator,
        selected_subject=selected_subject,
    )


if __name__ == "__main__":
    main()
