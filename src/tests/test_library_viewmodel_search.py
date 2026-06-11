from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bookhub.ui.models.resource import ResourceItem
from bookhub.ui.viewmodels.library_viewmodel import LibraryViewModel


def _resource(
    resource_id: str,
    title: str,
    author: str,
    tags: list[str],
    path: str,
) -> ResourceItem:
    return ResourceItem(
        resource_id=resource_id,
        title=title,
        author=author,
        tags=tags,
        resource_type="text_novel",
        path=path,
    )


class LibraryViewModelSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.view_model = LibraryViewModel()
        self.view_model.set_resources(
            [
                _resource("text-1", "异界之眸", "烟烬先生", ["奇幻", "完结"], "D:/txt/eye.txt"),
                _resource("text-2", "雨夜记录", "KrankheitRan", ["悬疑"], "D:/txt/rain.txt"),
            ]
        )

    def test_text_search_matches_tags_with_plain_query(self) -> None:
        self.view_model.set_query("奇幻")
        self.assertEqual([item.resource_id for item in self.view_model.filtered_resources()], ["text-1"])

    def test_text_search_supports_field_prefixes(self) -> None:
        self.view_model.set_query("tag:悬疑")
        self.assertEqual([item.resource_id for item in self.view_model.filtered_resources()], ["text-2"])

        self.view_model.set_query("author:烟烬")
        self.assertEqual([item.resource_id for item in self.view_model.filtered_resources()], ["text-1"])

        self.view_model.set_query("title:雨夜")
        self.assertEqual([item.resource_id for item in self.view_model.filtered_resources()], ["text-2"])

    def test_search_suggestions_include_tags(self) -> None:
        suggestions = self.view_model.search_suggestions_for_query("tag:奇")
        tag_suggestions = [item for item in suggestions if item["group"] == "Tags"]
        self.assertEqual(tag_suggestions[0]["label"], "奇幻")
        self.assertEqual(tag_suggestions[0]["query_value"], "tag:奇幻")


if __name__ == "__main__":
    unittest.main()
