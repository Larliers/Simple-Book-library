from __future__ import annotations

from dataclasses import dataclass, field

from bookhub.ui.models.resource import ResourceItem


@dataclass(slots=True)
class UiState:
    sort_by: str = "title"
    filter: str = ""
    page: int = 1
    page_size: int = 50


@dataclass(slots=True)
class UiInputEnvelope:
    request_id: str
    task_id: str
    view_mode: str
    data_source: dict[str, list[ResourceItem]]
    ui_state: UiState
    trace_id: str


class LibraryViewModel:
    def __init__(self) -> None:
        self.view_mode = "waterfall"
        self.ui_state = UiState()
        self.resources = self._seed_resources()

    def set_query(self, query: str) -> None:
        self.ui_state.filter = query.strip().lower()

    def set_view_mode(self, mode: str) -> None:
        if mode in {"list", "waterfall"}:
            self.view_mode = mode

    def filtered_resources(self) -> list[ResourceItem]:
        query = self.ui_state.filter
        if not query:
            return list(self.resources)
        return [
            item
            for item in self.resources
            if query in item.title.lower()
            or query in item.author.lower()
            or any(query in tag.lower() for tag in item.tags)
        ]

    def build_envelope(self) -> UiInputEnvelope:
        return UiInputEnvelope(
            request_id="req-ui-outline",
            task_id="task-library-render",
            view_mode=self.view_mode,
            data_source={"resources": self.filtered_resources()},
            ui_state=self.ui_state,
            trace_id="trace-ui-outline-001",
        )

    @staticmethod
    def _seed_resources() -> list[ResourceItem]:
        return [
            ResourceItem(
                resource_id="b001",
                title="Architectural Patterns",
                author="Elena Rostova",
                status="READING",
                tags=["Design", "2024"],
                path=r"D:\Library\Architectural Patterns.pdf",
            ),
            ResourceItem(
                resource_id="b002",
                title="The Grid System",
                author="Josef Muller-Brockmann",
                status="FINISHED",
                tags=["Classic", "Theory"],
                path=r"D:\Library\The Grid System.pdf",
            ),
            ResourceItem(
                resource_id="b003",
                title="Neural Networks",
                author="Dr. Aris Thorne",
                status="READING",
                tags=["Science"],
                path=r"D:\Library\Neural Networks.pdf",
            ),
            ResourceItem(
                resource_id="b004",
                title="Minimalism in Life",
                author="Sato Kenji",
                status="UNREAD",
                tags=["Lifestyle"],
                path=r"D:\Library\Minimalism in Life.pdf",
            ),
            ResourceItem(
                resource_id="b005",
                title="Legacy Systems",
                author="Markus Hoffman",
                status="READING",
                tags=["History"],
                path=r"D:\Library\Legacy Systems.pdf",
            ),
        ]

