from __future__ import annotations

import json
from io import BytesIO
from typing import Any

from muronto_app.config import (
    CONFIG_CAPTION,
    CONFIG_FILENAME,
    CONFIG_PAGE_NAME,
    DEFAULT_OPTIONS,
    EMAIL_TO_INVESTIGATOR_KEY,
    LA_HOME_FOLDER_KEY,
    OPTIONS_KEY,
)
from muronto_app.labarchives import (
    attachment_matches_config,
    create_subject_page_with_json,
    find_config_attachment,
    find_root_config_page,
    read_config_attachment,
    resolve_notebook_folder,
    save_config_attachment,
)
from muronto_app.subject import SUBJECT_ATTACHMENT_CAPTION


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
        payload: dict[str, Any] | str,
        *,
        caption: str = CONFIG_CAPTION,
        filename: str = CONFIG_FILENAME,
    ) -> None:
        self.caption = caption
        self.filename = filename
        self.updated_content: Any | None = None
        raw_payload = (
            payload.encode("utf-8")
            if isinstance(payload, str)
            else json.dumps(payload).encode("utf-8")
        )
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


class FakeEntries(list[FakeEntry]):
    def __init__(self, entries: list[FakeEntry]) -> None:
        super().__init__(entries)
        self.created: tuple[dict[str, Any], str, str] | None = None

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


class FakePage:
    def __init__(
        self,
        entries: list[FakeEntry],
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
    def __init__(self, *, name: str = "Folder") -> None:
        self.name = name

    def is_dir(self) -> bool:
        return True

    def as_dir(self) -> "FakeDirectory":
        return self


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
        "project_id": "SEASIC",
        "project_name": (
            "Sensory Evidence Accumulation Synaptic Integration in Cortex"
        ),
        "LA_Home_Folder": "/Experiments",
        "Investigator": "APF",
        "PI": "Soohyun Lee",
        "Species": "Mouse",
        "ASP": "UFNC-01",
        EMAIL_TO_INVESTIGATOR_KEY: {},
        OPTIONS_KEY: {**DEFAULT_OPTIONS, LA_HOME_FOLDER_KEY: ["/Experiments"]},
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
    assert result.config[LA_HOME_FOLDER_KEY] == "/Experiments"


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
