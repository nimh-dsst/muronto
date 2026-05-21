from __future__ import annotations

import html
import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any

from labapi import NotebookPage
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
from muronto_app.subject import (
    SUBJECT_ATTACHMENT_CAPTION,
    SUBJECT_STATUS_INCOMPLETE,
    SUBJECT_STATUS_KEY,
    SUBJECT_VALIDATION_ERRORS_KEY,
)


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
        payload: dict[str, Any],
        *,
        entry_id: str,
        filename: str,
        caption: str,
    ) -> None:
        self.id = entry_id
        self.filename = filename
        self.caption = caption
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
    def __init__(self) -> None:
        self.name = "Experiments"
        self.id = "experiments-folder"
        self.children: list[FakePage] = []
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
                PROJECT_NAME_KEY: "Subject Streamlit Test",
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


def subject_page_app(home_folder: FakeHomeFolder) -> AppTest:
    app = AppTest.from_file(
        Path(__file__).parents[1] / "pages" / "1_Subject.py"
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


def page_subject_attachment(page: FakePage) -> FakeAttachmentEntry:
    entries = [
        entry
        for entry in page.entries
        if isinstance(entry, FakeAttachmentEntry)
        and entry.caption == SUBJECT_ATTACHMENT_CAPTION
    ]
    assert len(entries) == 1
    return entries[0]


def page_text_entry(page: FakePage) -> FakeTextEntry:
    entries = [
        entry for entry in page.entries if isinstance(entry, FakeTextEntry)
    ]
    assert len(entries) == 1
    return entries[0]


def error_values(app: AppTest) -> list[str]:
    return [error.value for error in app.error]


def warning_values(app: AppTest) -> list[str]:
    return [warning.value for warning in app.warning]


def test_subject_page_immediately_validates_regex_fields() -> None:
    app = subject_page_app(FakeHomeFolder()).run()

    app.text_input(key="subject_create_animal_id").set_value("1234567")
    app.text_input(key="subject_create_ear_tag").set_value("12")
    app.text_input(key="subject_create_ccn").set_value("abcdef")
    app.selectbox(key="subject_create_source_type").select("Breeding")
    app.run()
    app.text_input(key="subject_create_parent_ccn").set_value("12345").run()

    errors = error_values(app)
    assert any(
        "Animal ID must match the regex pattern" in error for error in errors
    )
    assert any(
        "ear_tag must match the regex pattern" in error for error in errors
    )
    assert any("ccn must match the regex pattern" in error for error in errors)
    assert any(
        "parent_ccn must match the regex pattern" in error for error in errors
    )

    app.text_input(key="subject_create_animal_id").set_value("123-4567")
    app.text_input(key="subject_create_ear_tag").set_value("123")
    app.text_input(key="subject_create_ccn").set_value("123456")
    app.text_input(key="subject_create_parent_ccn").set_value("654321").run()

    assert not error_values(app)


def test_subject_page_create_then_edit_updates_json_and_text() -> None:
    home_folder = FakeHomeFolder()
    app = subject_page_app(home_folder).run()

    app.text_input(key="subject_create_animal_id").set_value("123-4567")
    app.text_input(key="subject_create_ear_tag").set_value("123")
    app.text_input(key="subject_create_ccn").set_value("123456")
    app.selectbox(key="subject_create_strain_1").select("Ai14")
    app.selectbox(key="subject_create_genotype_1").select("Het")
    app.date_input(key="subject_create_dob").set_value(date(2024, 1, 2))
    app.date_input(key="subject_create_dow").set_value(date(2024, 1, 9))
    app.selectbox(key="subject_create_source_type").select("JAX")
    app.button(key="subject_create_submit").click().run()

    assert not app.exception
    assert len(home_folder.children) == 1
    page = home_folder.children[0]
    subject_entry = page_subject_attachment(page)
    text_entry = page_text_entry(page)
    created_payload = attachment_payload(subject_entry)
    assert created_payload["animal_id"] == "123-4567"
    assert created_payload["ccn"] == "123456"
    assert "123456" in text_entry.content

    app.toggle(key="subject_edit_existing").set_value(True).run()
    edit_form_key = f"subject_edit_{page.id}"
    assert app.text_input(key=f"{edit_form_key}_ccn").value == "123456"

    app.text_input(key=f"{edit_form_key}_ear_tag").set_value("456")
    app.text_input(key=f"{edit_form_key}_ccn").set_value("654321")
    app.button(key=f"{edit_form_key}_submit").click().run()

    assert not app.exception
    assert len(page.entries) == 2
    edited_payload = attachment_payload(subject_entry)
    assert edited_payload["animal_id"] == "123-4567"
    assert edited_payload["ear_tag"] == "456"
    assert edited_payload["ccn"] == "654321"
    assert subject_entry.filename == "123-4567.json"
    assert "654321" in text_entry.content
    assert "123456" not in text_entry.content


def test_subject_page_saves_and_completes_incomplete_record() -> None:
    home_folder = FakeHomeFolder()
    app = subject_page_app(home_folder).run()

    app.text_input(key="subject_create_animal_id").set_value("123-4567")
    app.button(key="subject_create_submit").click().run()

    assert not app.exception
    assert len(home_folder.children) == 1
    page = home_folder.children[0]
    subject_entry = page_subject_attachment(page)
    payload = attachment_payload(subject_entry)
    assert payload[SUBJECT_STATUS_KEY] == SUBJECT_STATUS_INCOMPLETE
    assert "ear_tag is required." in payload[SUBJECT_VALIDATION_ERRORS_KEY]
    assert "ccn is required." in payload[SUBJECT_VALIDATION_ERRORS_KEY]
    assert any(
        "Saved an incomplete subject record" in warning
        for warning in warning_values(app)
    )

    app.toggle(key="subject_edit_existing").set_value(True).run()
    edit_form_key = f"subject_edit_{page.id}"
    assert app.text_input(key=f"{edit_form_key}_ear_tag").value == ""
    assert app.text_input(key=f"{edit_form_key}_ccn").value == ""

    app.text_input(key=f"{edit_form_key}_ear_tag").set_value("123")
    app.text_input(key=f"{edit_form_key}_ccn").set_value("123456")
    app.selectbox(key=f"{edit_form_key}_strain_1").select("Ai14")
    app.date_input(key=f"{edit_form_key}_dob").set_value(date(2024, 1, 2))
    app.date_input(key=f"{edit_form_key}_dow").set_value(date(2024, 1, 9))
    app.text_input(key=f"{edit_form_key}_parent_ccn").set_value("654321")
    app.button(key=f"{edit_form_key}_submit").click().run()

    assert not app.exception
    completed_payload = attachment_payload(subject_entry)
    assert completed_payload["animal_id"] == "123-4567"
    assert completed_payload["ear_tag"] == "123"
    assert completed_payload["ccn"] == "123456"
    assert SUBJECT_STATUS_KEY not in completed_payload
    assert SUBJECT_VALIDATION_ERRORS_KEY not in completed_payload
