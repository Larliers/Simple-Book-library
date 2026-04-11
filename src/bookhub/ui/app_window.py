from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from bookhub.ui.dialogs.import_dialog import ImportDialog
from bookhub.ui.pages.library_page import LibraryPage
from bookhub.ui.pages.placeholder_page import PlaceholderPage
from bookhub.ui.pages.plugins_page import PluginsPage
from bookhub.ui.pages.settings_page import SettingsPage
from bookhub.ui.resources.styles import APP_STYLE
from bookhub.ui.viewmodels.library_viewmodel import LibraryViewModel
from bookhub.ui.widgets.sidebar import SidebarWidget
from bookhub.ui.widgets.topbar import TopBarWidget


class AppWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Simple Book Library - UI Outline")
        self.resize(1400, 860)

        self._library_vm = LibraryViewModel()
        self._pages: dict[str, int] = {}

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = SidebarWidget()
        self.sidebar.setFixedWidth(240)
        self.sidebar.page_requested.connect(self._show_page)
        root.addWidget(self.sidebar)

        main_panel = QWidget()
        panel_layout = QVBoxLayout(main_panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        self.topbar = TopBarWidget()
        self.topbar.query_changed.connect(self._on_query_changed)
        self.topbar.import_requested.connect(self._show_import_dialog)
        panel_layout.addWidget(self.topbar)

        self.page_stack = QStackedWidget()
        panel_layout.addWidget(self.page_stack, 1)
        root.addWidget(main_panel, 1)

        self.library_page = LibraryPage(self._library_vm)
        self._register_page("library", self.library_page)
        self._register_page("collections", PlaceholderPage("Collections", "Collections page skeleton."))
        self._register_page("reading_now", PlaceholderPage("Reading Now", "Reading queue page skeleton."))
        self._register_page("favorites", PlaceholderPage("Favorites", "Favorites page skeleton."))
        self._register_page("tools", PluginsPage())
        self._register_page("trash", PlaceholderPage("Trash", "Trash page skeleton."))
        self._register_page("settings", SettingsPage())

        self.setStyleSheet(APP_STYLE)
        self._show_page("library")

    def _register_page(self, page_name: str, widget: QWidget) -> None:
        index = self.page_stack.addWidget(widget)
        self._pages[page_name] = index

    def _show_page(self, page_name: str) -> None:
        index = self._pages.get(page_name)
        if index is None:
            return
        self.page_stack.setCurrentIndex(index)
        self.sidebar.set_active(page_name)

    def _on_query_changed(self, query: str) -> None:
        current_page = self.page_stack.currentWidget()
        if current_page is self.library_page:
            self.library_page.set_query(query)

    def _show_import_dialog(self) -> None:
        dialog = ImportDialog(self)
        dialog.exec()

