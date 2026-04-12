from __future__ import annotations

from dataclasses import dataclass, field

from bookhub.ui.models.resource import ResourceItem


@dataclass(slots=True)
class UiState:
    sort_by: str = "title"
    filter: str = ""
    page: int = 1
    page_size: int = 50
    search_suggestions: list[dict[str, str]] = field(default_factory=list)
    selected_resource_id: str | None = None
    active_plugin: str = "Metadata Fetcher"
    settings_section: str = "general"


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
        self._refresh_search_suggestions("")

    def set_query(self, query: str) -> None:
        self.ui_state.filter = query.strip().lower()
        self._refresh_search_suggestions(query)

    def set_view_mode(self, mode: str) -> None:
        if mode in {"list", "waterfall"}:
            self.view_mode = mode

    def set_selected_resource(self, resource_id: str | None) -> None:
        self.ui_state.selected_resource_id = resource_id

    def set_active_plugin(self, plugin_name: str) -> None:
        self.ui_state.active_plugin = plugin_name

    def set_settings_section(self, section: str) -> None:
        self.ui_state.settings_section = section

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

    def _refresh_search_suggestions(self, raw_query: str) -> None:
        query = raw_query.strip().lower()
        suggestions: list[dict[str, str]] = [
            {
                "group": "History",
                "label": "Bauhaus principles",
                "description": "Recent search",
                "query_value": "bauhaus",
            }
        ]

        for item in self.resources:
            if query and query not in item.title.lower() and query not in item.author.lower():
                continue
            suggestions.append(
                {
                    "group": "Books",
                    "label": item.title,
                    "description": item.author,
                    "query_value": item.title,
                }
            )

        authors = {resource.author for resource in self.resources if not query or query in resource.author.lower()}
        for author in sorted(authors):
            suggestions.append(
                {
                    "group": "Authors",
                    "label": author,
                    "description": "Author",
                    "query_value": author,
                }
            )

        self.ui_state.search_suggestions = suggestions[:10]

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
                thumbnail_path=r"",
            ),
            ResourceItem(
                resource_id="b002",
                title="The Grid System",
                author="Josef Muller-Brockmann",
                status="FINISHED",
                tags=["Classic", "Theory"],
                path=r"D:\Library\The Grid System.pdf",
                thumbnail_path=r"",
            ),
            ResourceItem(
                resource_id="b003",
                title="Neural Networks",
                author="Dr. Aris Thorne",
                status="READING",
                tags=["Science"],
                path=r"D:\Library\Neural Networks.pdf",
                thumbnail_path=r"",
            ),
            ResourceItem(
                resource_id="b004",
                title="Minimalism in Life",
                author="Sato Kenji",
                status="UNREAD",
                tags=["Lifestyle"],
                path=r"D:\Library\Minimalism in Life.pdf",
                thumbnail_path=r"",
            ),
            ResourceItem(
                resource_id="b005",
                title="Legacy Systems",
                author="Markus Hoffman",
                status="READING",
                tags=["History"],
                path=r"D:\Library\Legacy Systems.pdf",
                thumbnail_path=r"",
            ),
        ]
