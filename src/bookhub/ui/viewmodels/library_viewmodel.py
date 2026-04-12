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
        self.resources: list[ResourceItem] = []
        self._refresh_search_suggestions("")

    def set_resources(self, resources: list[ResourceItem]) -> None:
        self.resources = list(resources)
        self._refresh_search_suggestions(self.ui_state.filter)

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

    def filtered_resources(self, include_missing: bool = False) -> list[ResourceItem]:
        source = [item for item in self.resources if bool(item.is_missing) is include_missing]
        query = self.ui_state.filter
        if not query:
            return list(source)
        return [
            item
            for item in source
            if query in item.title.lower()
            or query in item.author.lower()
            or any(query in tag.lower() for tag in item.tags)
            or query in item.path.lower()
        ]

    def build_envelope(self) -> UiInputEnvelope:
        return UiInputEnvelope(
            request_id="req-ui-outline",
            task_id="task-library-render",
            view_mode=self.view_mode,
            data_source={"resources": self.filtered_resources(include_missing=False)},
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
            if item.is_missing:
                continue
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

        authors = {
            resource.author
            for resource in self.resources
            if resource.author and not resource.is_missing and (not query or query in resource.author.lower())
        }
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
