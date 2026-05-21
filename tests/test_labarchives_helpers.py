from __future__ import annotations

import json
from io import BytesIO
from typing import Any

from muronto_app.config import (
    ASP_KEY,
    CONFIG_CAPTION,
    CONFIG_FILENAME,
    CONFIG_PAGE_NAME,
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
from muronto_app.labarchives import (
    attachment_matches_config,
    create_subject_page_with_json,
    discover_subject_records,
    find_config_attachment,
    find_root_config_page,
    read_config_attachment,
    resolve_notebook_folder,
    save_config_attachment,
    save_surgery_attachment,
    save_surgery_file_attachment,
)
from muronto_app.subject import (
    ANIMAL_ID_KEY,
    EAR_TAG_KEY,
    SUBJECT_ATTACHMENT_CAPTION,
)
from muronto_app.surgery import (
    CAPTION_KEY,
    ENTRY_ID_KEY,
    FILENAME_KEY,
    MIME_TYPE_KEY,
    NOTE_UPLOAD_TYPE,
    SURGERY_ATTACHMENT_CAPTION,
    SURGERY_FILE_ATTACHMENT_CAPTION,
    UPLOAD_TYPE_KEY,
)


class FakeAttachment:
    def __init__(
        self,
        payload: bytes,
        *,
        filename: str = CONFIG_FILENAME,
        caption: str = CONFIG_CAPTION,
    ) -> None:
        self._payload = BytesIO(payload)
        self.filename = filename
        self.caption = caption
        self.closed = False

    def read(self) -> bytes:
        return self._payload.read()

    def close(self) -> None:
        self.closed = True


class FakeEntry:
    def __init__(
        self,
        payload: dict[str, Any] | str | bytes,
        *,
        caption: str = CONFIG_CAPTION,
        entry_id: str = "entry-id",
        filename: str = CONFIG_FILENAME,
    ) -> None:
        self.id = entry_id
        self.caption = caption
        self.filename = filename
        self.updated_content: Any | None = None
        if isinstance(payload, bytes):
            raw_payload = payload
        elif isinstance(payload, str):
            raw_payload = payload.encode("utf-8")
        else:
            raw_payload = json.dumps(payload).encode("utf-8")
        self.attachment = FakeAttachment(
            raw_payload,
            filename=filename,
            caption=caption,
        )

    def get_attachment(self) -> FakeAttachment:
        return self.attachment

    @property
    def content(self) -> Any | None:
        return self.updated_content

    @content.setter
    def content(self, value: Any) -> None:
        self.updated_content = value


class FakeTextEntry:
    content_type = "text entry"

    def __init__(
        self,
        content: str,
        *,
        entry_id: str = "text-entry",
    ) -> None:
        self.id = entry_id
        self._content = content
        self.updated_content: str | None = None

    @property
    def content(self) -> str:
        return self._content

    @content.setter
    def content(self, value: str) -> None:
        self._content = value
        self.updated_content = value


class FakeEntries(list[Any]):
    def __init__(self, entries: list[Any]) -> None:
        super().__init__(entries)
        self.created: tuple[dict[str, Any], str, str] | None = None
        self.created_attachment: tuple[bytes, str, str, str] | None = None

    def create_json_entry(
        self,
        config: dict[str, Any],
        *,
        filename: str,
        caption: str,
    ) -> tuple[FakeEntry, object]:
        self.created = (config, filename, caption)
        entry = FakeEntry(config, filename=filename, caption=caption)
        self.append(entry)
        return entry, object()

    def create(
        self,
        _cls: Any,
        attachment: Any,
        *,
        client_ip: str | None = None,
    ) -> FakeEntry:
        del client_ip
        attachment.seek(0)
        raw_payload = attachment.read()
        attachment.seek(0)
        self.created_attachment = (
            raw_payload,
            attachment.filename,
            attachment.caption,
            attachment.mime_type,
        )
        entry = FakeEntry(
            raw_payload,
            filename=attachment.filename,
            caption=attachment.caption,
            entry_id=f"entry-{len(self) + 1}",
        )
        self.append(entry)
        return entry


class FakePage:
    def __init__(
        self,
        entries: list[Any],
        *,
        name: str = CONFIG_PAGE_NAME,
    ) -> None:
        self.id = "page-id"
        self.entries = FakeEntries(entries)
        self.name = name

    def is_dir(self) -> bool:
        return False

    def as_page(self) -> "FakePage":
        return self


class FakeDirectory:
    def __init__(
        self,
        *,
        name: str = "Folder",
        children: list[Any] | None = None,
    ) -> None:
        self.name = name
        self.id = name
        self.children = children or []
        self.refreshed = 0

    def is_dir(self) -> bool:
        return True

    def as_dir(self) -> "FakeDirectory":
        return self

    def refresh(self) -> None:
        self.refreshed += 1


class FakeNotebook:
    def __init__(self, children: list[Any]) -> None:
        self.children = children

    def traverse(self, path: str) -> Any:
        for child in self.children:
            if f"/{child.name}" == path or child.name == path:
                return child
        raise KeyError(path)


class FakeSubjectContainer:
    def __init__(self, children: list[Any] | None = None) -> None:
        self.children = children or []
        self.refreshed = 0

    def refresh(self) -> None:
        self.refreshed += 1

    def create(self, _cls: Any, name: str) -> FakePage:
        page = FakePage([], name=name)
        self.children.append(page)
        return page


def config_payload() -> dict[str, Any]:
    payload = {
        SCHEMA_VERSION_KEY: SCHEMA_VERSION,
        DEFAULT_PROJECT_ID_KEY: "SEASIC",
        PROJECTS_KEY: {
            "SEASIC": {
                PROJECT_ID_KEY: "SEASIC",
                PROJECT_NAME_KEY: (
                    "Sensory Evidence Accumulation Synaptic Integration "
                    "in Cortex"
                ),
                LA_HOME_FOLDER_KEY: "/Experiments",
                PI_KEY: "Soohyun Lee",
                SPECIES_KEY: "Mouse",
                ASP_KEY: "UFNC-01",
            }
        },
        EMAIL_TO_INVESTIGATOR_KEY: {},
        EMAIL_TO_PROJECT_KEY: {},
        OPTIONS_KEY: DEFAULT_OPTIONS,
    }
    return payload


def test_find_root_config_page_only_matches_root_pages() -> None:
    page = FakePage([])
    notebook = FakeNotebook([FakeDirectory(), page])

    assert find_root_config_page(notebook) is page


def test_find_config_attachment_detects_caption_or_filename() -> None:
    entry = FakeEntry(config_payload(), caption="different")
    page = FakePage([entry])

    assert attachment_matches_config(entry)
    assert find_config_attachment(page) is entry


def test_read_config_attachment_returns_valid_config() -> None:
    entry = FakeEntry(config_payload())
    page = FakePage([entry])

    result = read_config_attachment(page)

    assert result.errors == []
    assert result.config is not None
    assert (
        result.config[PROJECTS_KEY]["SEASIC"][LA_HOME_FOLDER_KEY]
        == "/Experiments"
    )


def test_read_config_attachment_reports_invalid_json() -> None:
    entry = FakeEntry("{not json")
    page = FakePage([entry])

    result = read_config_attachment(page)

    assert result.entry is entry
    assert result.config is None
    assert "could not be decoded" in result.errors[0]


def test_save_config_attachment_updates_existing_entry() -> None:
    entry = FakeEntry(config_payload())
    page = FakePage([entry])

    saved = save_config_attachment(
        page,
        config_payload(),
        existing_entry=entry,
    )

    assert saved is entry
    assert entry.updated_content is not None
    assert entry.updated_content.filename == CONFIG_FILENAME
    assert entry.updated_content.caption == CONFIG_CAPTION


def test_save_config_attachment_updates_reference_text_entry() -> None:
    entry = FakeEntry(config_payload(), entry_id="config-entry")
    text_entry = FakeTextEntry(
        "<p>Reference Attachment: muronto_config</p>"
        "<p>Entry ID: config-entry</p>"
        "<pre>old preview</pre>"
    )
    page = FakePage([entry, text_entry])
    payload = config_payload()
    payload[PROJECTS_KEY]["SEASIC"][PROJECT_NAME_KEY] = "Updated project"

    saved = save_config_attachment(page, payload, existing_entry=entry)

    assert saved is entry
    assert text_entry.updated_content is not None
    assert "Reference Attachment: muronto_config" in text_entry.updated_content
    assert "Entry ID: config-entry" in text_entry.updated_content
    assert "Updated project" in text_entry.updated_content
    assert "old preview" not in text_entry.updated_content


def test_save_config_attachment_creates_when_missing() -> None:
    page = FakePage([])

    saved = save_config_attachment(page, config_payload())

    assert saved is page.entries[-1]
    assert page.entries.created is not None
    assert page.entries.created[1:] == (CONFIG_FILENAME, CONFIG_CAPTION)


def test_resolve_notebook_folder_returns_configured_folder() -> None:
    folder = FakeDirectory(name="Experiments")
    notebook = FakeNotebook([folder])

    assert resolve_notebook_folder(notebook, "/Experiments") is folder


def test_create_subject_page_with_json_blocks_duplicate_child_name() -> None:
    existing_page = FakePage([], name="123-4567")
    container = FakeSubjectContainer([existing_page])

    try:
        create_subject_page_with_json(
            container,
            {"animal_id": "123-4567"},
        )
    except ValueError as exc:
        assert "already exists" in str(exc)
    else:
        raise AssertionError("Expected duplicate subject page to be rejected.")


def test_create_subject_page_with_json_creates_page_and_attachment() -> None:
    container = FakeSubjectContainer()
    payload = {
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
    }

    result = create_subject_page_with_json(container, payload)

    assert result.page.name == "123-4567"
    assert result.attachment_entry is result.page.entries[-1]
    assert result.page.entries.created == (
        payload,
        "123-4567.json",
        SUBJECT_ATTACHMENT_CAPTION,
    )
    assert container.refreshed == 2


def test_discover_subject_records_recurses_folders() -> None:
    subject_payload = {
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
    }
    subject_page = FakePage(
        [
            FakeEntry(
                subject_payload,
                filename="123-4567.json",
                caption=SUBJECT_ATTACHMENT_CAPTION,
            )
        ],
        name="123-4567",
    )
    nested_folder = FakeDirectory(name="Nested", children=[subject_page])
    root_folder = FakeDirectory(name="Root", children=[nested_folder])

    records = discover_subject_records(root_folder)

    assert len(records) == 1
    assert records[0].page is subject_page
    assert records[0].payload[ANIMAL_ID_KEY] == "123-4567"
    assert records[0].payload[EAR_TAG_KEY] == "123"
    assert root_folder.refreshed == 1
    assert nested_folder.refreshed == 1


def test_save_surgery_attachment_creates_and_updates_by_filename() -> None:
    page = FakePage([], name="123-4567")
    payload = {
        "project_id": "SEASIC",
        "investigator": "APF",
        "animal_id": "123-4567",
        "ear_tag": "123",
        "surgeon": "SL",
        "surgery_date": "20260511",
        "preop_cnn": "123456",
        "postop_cnn": "654321",
    }

    created = save_surgery_attachment(page, payload)

    assert created.created
    assert created.attachment_entry is page.entries[-1]
    assert page.entries.created == (
        payload,
        "123-4567_surgery_20260511.json",
        SURGERY_ATTACHMENT_CAPTION,
    )

    updated_payload = {**payload, "surgeon": "JGL"}
    updated = save_surgery_attachment(page, updated_payload)

    assert not updated.created
    assert updated.attachment_entry is created.attachment_entry
    assert len(page.entries) == 1
    assert page.entries[0].updated_content is not None
    assert (
        page.entries[0].updated_content.filename
        == "123-4567_surgery_20260511.json"
    )
    assert (
        page.entries[0].updated_content.caption == SURGERY_ATTACHMENT_CAPTION
    )


def test_save_surgery_attachment_updates_reference_text_entry() -> None:
    entry = FakeEntry(
        {
            "project_id": "SEASIC",
            "investigator": "APF",
            "animal_id": "123-4567",
            "ear_tag": "123",
            "surgeon": "SL",
            "surgery_date": "20260511",
            "preop_cnn": "123456",
            "postop_cnn": "654321",
        },
        filename="123-4567_surgery_20260511.json",
        caption=SURGERY_ATTACHMENT_CAPTION,
        entry_id="surgery-entry",
    )
    text_entry = FakeTextEntry(
        "<p>Reference Attachment: surgery</p>"
        "<p>Entry ID: surgery-entry</p>"
        "<pre>old preview</pre>"
    )
    page = FakePage([entry, text_entry], name="123-4567")

    result = save_surgery_attachment(
        page,
        {
            "project_id": "SEASIC",
            "investigator": "APF",
            "animal_id": "123-4567",
            "ear_tag": "123",
            "surgeon": "JGL",
            "surgery_date": "20260511",
            "preop_cnn": "123456",
            "postop_cnn": "654321",
        },
    )

    assert not result.created
    assert result.attachment_entry is entry
    assert text_entry.updated_content is not None
    assert SURGERY_ATTACHMENT_CAPTION in text_entry.updated_content
    assert "Entry ID: surgery-entry" in text_entry.updated_content
    assert "JGL" in text_entry.updated_content
    assert "old preview" not in text_entry.updated_content


def test_save_surgery_file_attachment_creates_reference() -> None:
    page = FakePage([], name="123-4567")

    result = save_surgery_file_attachment(
        page,
        payload=b"notes",
        filename="123-4567_surgery_20260511_note_upload_1_notes.pdf",
        mime_type="application/pdf",
        upload_type=NOTE_UPLOAD_TYPE,
    )

    assert result.created
    assert result.attachment_entry is page.entries[-1]
    assert page.entries.created_attachment == (
        b"notes",
        "123-4567_surgery_20260511_note_upload_1_notes.pdf",
        SURGERY_FILE_ATTACHMENT_CAPTION,
        "application/pdf",
    )
    assert result.reference == {
        UPLOAD_TYPE_KEY: NOTE_UPLOAD_TYPE,
        ENTRY_ID_KEY: "entry-1",
        FILENAME_KEY: "123-4567_surgery_20260511_note_upload_1_notes.pdf",
        CAPTION_KEY: SURGERY_FILE_ATTACHMENT_CAPTION,
        MIME_TYPE_KEY: "application/pdf",
    }


def test_save_surgery_file_attachment_updates_existing_match() -> None:
    entry = FakeEntry(
        b"old notes",
        filename="123-4567_surgery_20260511_note_upload_1_notes.pdf",
        caption=SURGERY_FILE_ATTACHMENT_CAPTION,
        entry_id="existing-entry",
    )
    page = FakePage([entry], name="123-4567")

    result = save_surgery_file_attachment(
        page,
        payload=b"new notes",
        filename="123-4567_surgery_20260511_note_upload_1_notes.pdf",
        mime_type="application/pdf",
        upload_type=NOTE_UPLOAD_TYPE,
    )

    assert not result.created
    assert result.attachment_entry is entry
    assert len(page.entries) == 1
    assert entry.updated_content is not None
    assert entry.updated_content.filename == (
        "123-4567_surgery_20260511_note_upload_1_notes.pdf"
    )
    assert entry.updated_content.caption == SURGERY_FILE_ATTACHMENT_CAPTION
    assert entry.updated_content.mime_type == "application/pdf"
    assert entry.updated_content.read() == b"new notes"
    assert result.reference[ENTRY_ID_KEY] == "existing-entry"
