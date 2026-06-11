from __future__ import annotations

from dataclasses import dataclass, field

from bookhub.ui.models.resource import ResourceItem


SEARCH_FIELD_PREFIXES = {"title", "author", "tag"}


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
        self.set_search_suggestions_for_query("")

    def set_resources(self, resources: list[ResourceItem]) -> None:
        self.resources = list(resources)
        self.set_search_suggestions_for_query(self.ui_state.filter)

    def set_query(self, query: str) -> None:
        self.ui_state.filter = query.strip().lower()

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
        return [item for item in source if self._matches_query(item, query)]

    def build_envelope(self) -> UiInputEnvelope:
        return UiInputEnvelope(
            request_id="req-ui-outline",
            task_id="task-library-render",
            view_mode=self.view_mode,
            data_source={"resources": self.filtered_resources(include_missing=False)},
            ui_state=self.ui_state,
            trace_id="trace-ui-outline-001",
        )

    def search_suggestions_for_query(self, raw_query: str) -> list[dict[str, str]]:
        query = raw_query.strip().lower()
        suggestions: list[dict[str, str]] = [
            {
                "group": "History",
                "label": "Bauhaus principles",
                "description": "Recent search",
                "query_value": "bauhaus",
            }
        ]

        tags = {
            tag
            for resource in self.resources
            if not resource.is_missing
            for tag in resource.tags
            if tag and (not query or self._matches_tag_query(tag, query))
        }
        for tag in sorted(tags):
            suggestions.append(
                {
                    "group": "Tags",
                    "label": tag,
                    "description": "Tag",
                    "query_value": f"tag:{tag}",
                }
            )

        for item in self.resources:
            if item.is_missing:
                continue
            if query and not self._matches_query(item, query):
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
            if resource.author
            and not resource.is_missing
            and (not query or self._matches_author_query(resource.author, query))
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
        return suggestions[:10]

    def set_search_suggestions_for_query(self, raw_query: str) -> None:
        self.ui_state.search_suggestions = self.search_suggestions_for_query(raw_query)

    def _matches_query(self, item: ResourceItem, query: str) -> bool:
        field, value = self._parse_query(query)
        if not value:
            return True
        if field == "title":
            return value in item.title.lower()
        if field == "author":
            return value in item.author.lower()
        if field == "tag":
            return any(value in tag.lower() for tag in item.tags)
        return (
            value in item.title.lower()
            or value in item.author.lower()
            or any(value in tag.lower() for tag in item.tags)
            or value in item.path.lower()
        )

    def _matches_author_query(self, author: str, query: str) -> bool:
        field, value = self._parse_query(query)
        if field and field != "author":
            return False
        return not value or value in author.lower()

    def _matches_tag_query(self, tag: str, query: str) -> bool:
        field, value = self._parse_query(query)
        if field and field != "tag":
            return False
        return not value or value in tag.lower()

    @staticmethod
    def _parse_query(query: str) -> tuple[str | None, str]:
        if ":" not in query:
            return None, query
        prefix, value = query.split(":", 1)
        prefix = prefix.strip().lower()
        if prefix not in SEARCH_FIELD_PREFIXES:
            return None, query
        return prefix, value.strip().lower()
