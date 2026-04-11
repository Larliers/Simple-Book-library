from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from bookhub.i18n import language_manager, tr
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
        language_manager.set_language("en")
        self.setWindowTitle(tr("app.window_title", "Simple Book Library - UI Outline"))
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
        self.plugins_page = PluginsPage()
        self._register_page("tools", self.plugins_page)
        self._register_page("trash", PlaceholderPage("Trash", "Trash page skeleton."))
        self.settings_page = SettingsPage()
        self.settings_page.language_changed.connect(self._on_language_changed)
        self._register_page("settings", self.settings_page)

        self.setStyleSheet(APP_STYLE)
        self.retranslate_ui()
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

    def _on_language_changed(self, language_code: str) -> None:
        language_manager.set_language(language_code)
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.setWindowTitle(tr("app.window_title", "Simple Book Library - UI Outline"))
        self.sidebar.retranslate_ui()
        self.topbar.retranslate_ui()
        self.library_page.retranslate_ui()
        self.plugins_page.retranslate_ui()
        self.settings_page.retranslate_ui()
