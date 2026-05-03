from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ResourceItem:
    resource_id: str
    title: str
    author: str = ""
    status: str = "UNREAD"
    tags: list[str] = field(default_factory=list)
    resource_type: str = "book"
    path: str = ""
    thumbnail_path: str | None = None
    publisher: str | None = None
    language: str | None = None
    is_missing: bool = False
    file_name: str = ""
    extension: str = ""
    info_text: str | None = None
    cover_image_path: str | None = None
    image_count: int = 0
