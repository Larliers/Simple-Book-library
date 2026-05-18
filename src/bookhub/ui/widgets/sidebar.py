from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpacerItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from bookhub.i18n import tr
from bookhub.ui.resources.assets import load_icon


class SidebarWidget(QWidget):
    page_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(14, 14, 14, 8)
        header_layout.setSpacing(2)
        self.title = QLabel("Bookshelf")
        self.title.setObjectName("SidebarTitle")
        self.subtitle = QLabel("Local Database")
        self.subtitle.setObjectName("PageSubtitle")
        header_layout.addWidget(self.title)
        header_layout.addWidget(self.subtitle)
        layout.addWidget(header)

        nav = QWidget()
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(10, 4, 10, 8)
        nav_layout.setSpacing(3)

        self._buttons: dict[str, QPushButton] = {}
        button_definitions = [
            ("library", "Library", "library.svg"),
            ("text_novel", "Text Novel", "library.svg"),
            ("collections", "Collections", "collections.svg"),
            ("favorites", "Favorites", "favorites.svg"),
            ("comic", "Comic", "library.svg"),
            ("comic_fav", "Comic Fav", "favorites.svg"),
        ]

        for key, text, icon_name in button_definitions:
            button = QPushButton(text)
            button.setCheckable(True)
            button.setProperty("variant", "sidebar_tab")
            button.setIcon(load_icon(icon_name))
            button.setIconSize(QSize(16, 16))
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _=False, page=key: self._emit_page(page))
            nav_layout.addWidget(button)
            self._buttons[key] = button

        nav_layout.addSpacing(12)
        self.import_button = QPushButton("IMPORT BOOKS")
        self.import_button.setObjectName("PrimarySideButton")
        self.import_button.setCursor(Qt.PointingHandCursor)
        nav_layout.addWidget(self.import_button)
        nav_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))
        layout.addWidget(nav, 1)

        footer = QWidget()
        footer.setObjectName("SidebarFoot")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(10, 10, 10, 10)
        footer_layout.setSpacing(6)
        self.settings_button = QPushButton("Settings")
        self.settings_button.setCheckable(True)
        self.settings_button.setProperty("variant", "sidebar_tab")
        self.settings_button.setIcon(load_icon("settings.svg"))
        self.settings_button.setIconSize(QSize(16, 16))
        self.settings_button.setCursor(Qt.PointingHandCursor)
        self.settings_button.clicked.connect(lambda: self._emit_page("settings"))
        footer_layout.addWidget(self.settings_button)
        layout.addWidget(footer)

        self.retranslate_ui()
        self.set_active("library")
        self._apply_adaptive_scale()

    def retranslate_ui(self) -> None:
        self.title.setText(tr("sidebar.title", "Bookshelf"))
        self.subtitle.setText(tr("sidebar.subtitle", "Local Database"))
        self._buttons["library"].setText(tr("sidebar.library", "Library"))
        self._buttons["text_novel"].setText(tr("sidebar.text_novel", "Text Novel"))
        self._buttons["collections"].setText(tr("sidebar.collections", "Collections"))
        self._buttons["favorites"].setText(tr("sidebar.favorites", "Favorites"))
        self._buttons["comic"].setText(tr("sidebar.comic", "Comic"))
        self._buttons["comic_fav"].setText(tr("sidebar.comic_fav", "Comic Fav"))
        self.import_button.setText(tr("sidebar.import_books", "IMPORT BOOKS"))
        self.settings_button.setText(tr("sidebar.settings", "Settings"))

    def set_active(self, page_name: str) -> None:
        for key, button in self._buttons.items():
            button.setChecked(key == page_name)
        self.settings_button.setChecked(page_name == "settings")

    def _emit_page(self, page_name: str) -> None:
        self.set_active(page_name)
        self.page_requested.emit(page_name)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_adaptive_scale()

    def _apply_adaptive_scale(self) -> None:
        height = max(1, self.height())
        scale = max(1.0, min(1.7, height / 860.0))

        title_size = int(28 * scale)
        subtitle_size = int(12 * min(scale, 1.45))
        nav_size = int(13 * min(scale, 1.55))
        icon_size = int(16 * min(scale, 1.45))

        title_font = QFont(self.title.font())
        title_font.setPixelSize(title_size)
        title_font.setBold(True)
        self.title.setFont(title_font)

        subtitle_font = QFont(self.subtitle.font())
        subtitle_font.setPixelSize(subtitle_size)
        self.subtitle.setFont(subtitle_font)

        for button in self._buttons.values():
            button_font = QFont(button.font())
            button_font.setPixelSize(nav_size)
            button.setFont(button_font)
            button.setIconSize(QSize(icon_size, icon_size))

        import_font = QFont(self.import_button.font())
        import_font.setPixelSize(nav_size)
        self.import_button.setFont(import_font)

        settings_font = QFont(self.settings_button.font())
        settings_font.setPixelSize(nav_size)
        self.settings_button.setFont(settings_font)
        self.settings_button.setIconSize(QSize(icon_size, icon_size))
