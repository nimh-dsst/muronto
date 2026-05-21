from __future__ import annotations

import html
import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, time
from io import BytesIO
from pathlib import Path
from typing import Any

from labapi import AttachmentEntry, NotebookPage
from streamlit.testing.v1 import AppTest

from muronto_app.config import (
    ASP_KEY,
    DEFAULT_OPTIONS,
    DEFAULT_PROJECT_ID_KEY,
    EMAIL_TO_INVESTIGATOR_KEY,
    EMAIL_TO_PROJECT_KEY,
    LA_HOME_FOLDER_KEY,
    OPTIONS_KEY,
    PI_KEY,
    PROJECT_ID_KEY,
    PROJECT_NAME_KEY,
    PROJECTS_KEY,
    SCHEMA_VERSION,
    SCHEMA_VERSION_KEY,
    SPECIES_KEY,
)
from muronto_app.state import (
    CONFIG_STATE_KEY,
    SELECTED_NOTEBOOK_NAME_STATE_KEY,
    SELECTED_NOTEBOOK_STATE_KEY,
    USER_STATE_KEY,
)
from muronto_app.subject import SUBJECT_ATTACHMENT_CAPTION
from muronto_app.surgery import SURGERY_ATTACHMENT_CAPTION


@dataclass
class FakeUser:
    email: str


class FakeAttachment:
    def __init__(
        self,
        payload: bytes,
        *,
        filename: str,
        caption: str,
    ) -> None:
        self._payload = BytesIO(payload)
        self.filename = filename
        self.caption = caption
        self.closed = False

    def read(self) -> bytes:
        return self._payload.read()

    def close(self) -> None:
        self.closed = True


class FakeAttachmentEntry:
    def __init__(
        self,
        payload: dict[str, Any] | bytes,
        *,
        entry_id: str,
        filename: str,
        caption: str,
    ) -> None:
        self.id = entry_id
        self.filename = filename
        self.caption = caption
        if isinstance(payload, bytes):
            self._raw_payload = payload
        else:
            self._raw_payload = json.dumps(payload).encode("utf-8")

    def get_attachment(self) -> FakeAttachment:
        return FakeAttachment(
            self._raw_payload,
            filename=self.filename,
            caption=self.caption,
        )

    @property
    def content(self) -> None:
        return None

    @content.setter
    def content(self, value: Any) -> None:
        seek = getattr(value, "seek", None)
        if callable(seek):
            seek(0)

        raw_payload = value.read()
        if callable(seek):
            seek(0)

        if isinstance(raw_payload, str):
            raw_payload = raw_payload.encode("utf-8")

        self._raw_payload = raw_payload
        self.filename = getattr(value, "filename", self.filename)
        self.caption = getattr(value, "caption", self.caption)


class FakeTextEntry:
    content_type = "text entry"

    def __init__(self, content: str) -> None:
        self.content = content


class FakeEntries(list[Any]):
    def create_json_entry(
        self,
        payload: dict[str, Any],
        *,
        filename: str,
        caption: str,
    ) -> tuple[FakeAttachmentEntry, FakeTextEntry]:
        entry = FakeAttachmentEntry(
            payload,
            entry_id=f"entry-{len(self) + 1}",
            filename=filename,
            caption=caption,
        )
        text_entry = FakeTextEntry(
            json_reference_text(payload, entry_id=entry.id, caption=caption)
        )
        self.extend([entry, text_entry])
        return entry, text_entry

    def create(
        self,
        _cls: type[AttachmentEntry],
        attachment: Any,
        *,
        client_ip: str | None = None,
    ) -> FakeAttachmentEntry:
        del client_ip
        attachment.seek(0)
        raw_payload = attachment.read()
        attachment.seek(0)
        entry = FakeAttachmentEntry(
            raw_payload,
            entry_id=f"entry-{len(self) + 1}",
            filename=attachment.filename,
            caption=attachment.caption,
        )
        self.append(entry)
        return entry


class FakePage:
    def __init__(self, name: str, page_id: str) -> None:
        self.name = name
        self.id = page_id
        self.entries = FakeEntries()

    def is_dir(self) -> bool:
        return False

    def as_page(self) -> FakePage:
        return self


class FakeHomeFolder:
    def __init__(self, children: list[FakePage] | None = None) -> None:
        self.name = "Experiments"
        self.id = "experiments-folder"
        self.children = children or []
        self.refreshed = 0

    def is_dir(self) -> bool:
        return True

    def as_dir(self) -> FakeHomeFolder:
        return self

    def refresh(self) -> None:
        self.refreshed += 1

    def create(self, _cls: type[NotebookPage], name: str) -> FakePage:
        page = FakePage(name, page_id=f"page-{len(self.children) + 1}")
        self.children.append(page)
        return page


class FakeNotebook:
    def __init__(self, home_folder: FakeHomeFolder) -> None:
        self.children = [home_folder]
        self._home_folder = home_folder

    def traverse(self, path: str) -> FakeHomeFolder:
        if path == "/Experiments":
            return self._home_folder
        raise KeyError(path)


def json_reference_text(
    payload: dict[str, Any],
    *,
    entry_id: str,
    caption: str,
) -> str:
    preview_json = html.escape(json.dumps(dict(payload), indent=4))
    return f"""
<p>Reference Attachment: {html.escape(caption)}</p>
<p>Entry ID: {html.escape(entry_id)}</p>
<pre>
{preview_json}
</pre>
"""


def config_payload() -> dict[str, Any]:
    return {
        SCHEMA_VERSION_KEY: SCHEMA_VERSION,
        DEFAULT_PROJECT_ID_KEY: "SEASIC",
        PROJECTS_KEY: {
            "SEASIC": {
                PROJECT_ID_KEY: "SEASIC",
                PROJECT_NAME_KEY: "Surgery Streamlit Test",
                LA_HOME_FOLDER_KEY: "/Experiments",
                PI_KEY: "Soohyun Lee",
                SPECIES_KEY: "Mouse",
                ASP_KEY: "UFNC-01",
            }
        },
        EMAIL_TO_INVESTIGATOR_KEY: {},
        EMAIL_TO_PROJECT_KEY: {},
        OPTIONS_KEY: deepcopy(DEFAULT_OPTIONS),
    }


def seed_subject_page() -> FakePage:
    page = FakePage("123-4567", page_id="page-1")
    page.entries.create_json_entry(
        {
            "animal_id": "123-4567",
            "ear_tag": "123",
            "ccn": "123456",
            "sex": "M",
            "strain_1": "Ai14",
            "genotype_1": "Het",
            "dob": "20240102",
            "dow": "20240109",
            "source_type": "JAX",
            "parent_ccn": "",
        },
        filename="123-4567.json",
        caption=SUBJECT_ATTACHMENT_CAPTION,
    )
    return page


def surgery_page_app(home_folder: FakeHomeFolder) -> AppTest:
    app = AppTest.from_file(
        Path(__file__).parents[1] / "pages" / "2_Surgery.py"
    )
    app.session_state[USER_STATE_KEY] = FakeUser("user@example.com")
    app.session_state[CONFIG_STATE_KEY] = config_payload()
    app.session_state[SELECTED_NOTEBOOK_NAME_STATE_KEY] = "Test Notebook"
    app.session_state[SELECTED_NOTEBOOK_STATE_KEY] = FakeNotebook(home_folder)
    return app


def attachment_payload(entry: FakeAttachmentEntry) -> dict[str, Any]:
    attachment = entry.get_attachment()
    try:
        return json.loads(attachment.read().decode("utf-8"))
    finally:
        attachment.close()


def page_surgery_attachment(page: FakePage) -> FakeAttachmentEntry:
    entries = [
        entry
        for entry in page.entries
        if isinstance(entry, FakeAttachmentEntry)
        and entry.caption == SURGERY_ATTACHMENT_CAPTION
    ]
    assert len(entries) == 1
    return entries[0]


def page_surgery_text_entry(page: FakePage) -> FakeTextEntry:
    surgery_entry = page_surgery_attachment(page)
    marker = f"Entry ID: {surgery_entry.id}"
    entries = [
        entry
        for entry in page.entries
        if isinstance(entry, FakeTextEntry) and marker in entry.content
    ]
    assert len(entries) == 1
    return entries[0]


def test_surgery_page_defaults_post_infusion_flow_test_to_na() -> None:
    app = surgery_page_app(FakeHomeFolder([seed_subject_page()])).run()

    assert not app.exception
    assert (
        app.selectbox(
            key=(
                "surgery_procedure_1_injection_1_infusion_1_"
                "post_infusion_flow_test"
            )
        ).value
        == "n/a"
    )


def test_surgery_page_medications_are_opt_in() -> None:
    app = surgery_page_app(FakeHomeFolder([seed_subject_page()])).run()

    assert not app.exception
    assert "surgery_medication_1" not in [
        widget.key for widget in app.selectbox
    ]
    assert "surgery_medication_1_conc_mgml" not in [
        widget.key for widget in app.number_input
    ]
    assert "surgery_medication_1_volume" not in [
        widget.key for widget in app.number_input
    ]

    app.button(key="surgery_add_medication").click().run()

    assert not app.exception
    assert app.selectbox(key="surgery_medication_1")
    assert app.number_input(key="surgery_medication_1_conc_mgml")
    assert app.number_input(key="surgery_medication_1_volume")


def test_surgery_page_create_then_edit_updates_json_and_text() -> None:
    subject_page = seed_subject_page()
    app = surgery_page_app(FakeHomeFolder([subject_page])).run()

    app.button(key="surgery_add_medication").click().run()
    app.selectbox(key="surgery_procedure_1_category").select("Implant").run()

    app.selectbox(key="surgery_surgeon").select("SL")
    app.date_input(key="surgery_date").set_value(date(2026, 5, 11))
    app.text_input(key="surgery_preop_cnn").set_value("123456")
    app.text_input(key="surgery_postop_cnn").set_value("654321")
    app.number_input(key="surgery_weight_pre_g").set_value(20.0)
    app.number_input(key="surgery_weight_post_g").set_value(19.5)
    app.selectbox(key="surgery_medication_1").select("Meloxicam")
    app.number_input(key="surgery_medication_1_conc_mgml").set_value(5.0)
    app.number_input(key="surgery_medication_1_volume").set_value(0.1)
    app.time_input(key="surgery_start_time").set_value(time(9, 0))
    app.time_input(key="surgery_end_time").set_value(time(10, 0))
    app.number_input(key="surgery_bregma_lambda_dist_mm").set_value(4.2)
    app.selectbox(key="surgery_procedure_1_implant_type").select(
        "Cranial Window"
    )
    app.selectbox(
        key="surgery_procedure_1_cranial_window_headplate_type"
    ).select("Standard_Y")
    app.selectbox(
        key="surgery_procedure_1_cranial_window_coverslip_type"
    ).select("Standard Single")
    app.selectbox(
        key="surgery_procedure_1_cranial_window_coverslip_diameter"
    ).select("3.5")
    app.selectbox(
        key="surgery_procedure_1_cranial_window_coverslip_thickness"
    ).select("1.5")
    app.selectbox(key="surgery_procedure_1_cranial_window_region").select("S1")
    app.number_input(
        key="surgery_procedure_1_cranial_window_center_ap"
    ).set_value(1.0)
    app.number_input(
        key="surgery_procedure_1_cranial_window_center_ml"
    ).set_value(2.0)
    app.selectbox(key="surgery_procedure_1_cranial_window_well_type").select(
        "Cement"
    )
    app.text_area(key="surgery_general_notes").set_value("initial note")
    app.button(key="surgery_submit").click().run()

    assert not app.exception
    surgery_entry = page_surgery_attachment(subject_page)
    surgery_text_entry = page_surgery_text_entry(subject_page)
    created_payload = attachment_payload(surgery_entry)
    assert created_payload["general_notes"] == "initial note"
    assert "initial note" in surgery_text_entry.content

    app.toggle(key="surgery_edit_existing").set_value(True).run()
    edit_form_key = f"surgery_edit_{surgery_entry.id.replace('-', '_')}"
    assert (
        app.text_area(key=f"{edit_form_key}_general_notes").value
        == "initial note"
    )

    app.text_area(key=f"{edit_form_key}_general_notes").set_value(
        "edited note"
    )
    app.button(key=f"{edit_form_key}_submit").click().run()

    assert not app.exception
    edited_payload = attachment_payload(surgery_entry)
    assert edited_payload["general_notes"] == "edited note"
    assert surgery_entry.filename == "123-4567_surgery_20260511.json"
    assert (
        len(
            [
                entry
                for entry in subject_page.entries
                if isinstance(entry, FakeAttachmentEntry)
                and entry.caption == SURGERY_ATTACHMENT_CAPTION
            ]
        )
        == 1
    )
    assert "edited note" in surgery_text_entry.content
    assert "initial note" not in surgery_text_entry.content
