from __future__ import annotations

from math import ceil
from time import monotonic

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QTimer, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from bookhub.i18n import tr


class SlideToast(QFrame):
    closed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._margin = 16
        self._remaining_seconds = 0
        self._deadline_ts = 0.0
        self._is_closing = False

        self.setObjectName("SlideToast")
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow)
        self.setStyleSheet(
            "QFrame#SlideToast {"
            "background: #fff7f7;"
            "border: 1px solid #efc0c0;"
            "border-radius: 10px;"
            "}"
            "QLabel#SlideToastTitle {"
            "color: #8e2c2c;"
            "font-size: 13px;"
            "font-weight: 700;"
            "}"
            "QLabel#SlideToastMessage {"
            "color: #8e2c2c;"
            "font-size: 12px;"
            "}"
            "QLabel#SlideToastCountdown {"
            "color: #ad5555;"
            "font-size: 11px;"
            "}"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)

        self._title_label = QLabel("")
        self._title_label.setObjectName("SlideToastTitle")
        root.addWidget(self._title_label)

        self._message_label = QLabel("")
        self._message_label.setObjectName("SlideToastMessage")
        self._message_label.setWordWrap(True)
        self._message_label.setMaximumWidth(280)
        root.addWidget(self._message_label)

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        self._countdown_label = QLabel("")
        self._countdown_label.setObjectName("SlideToastCountdown")
        footer.addWidget(self._countdown_label, 0, Qt.AlignLeft)
        footer.addStretch(1)
        root.addLayout(footer)

        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(100)
        self._countdown_timer.timeout.connect(self._on_countdown_tick)

        self._slide_in_animation = QPropertyAnimation(self, b"pos", self)
        self._slide_in_animation.setDuration(220)
        self._slide_in_animation.setEasingCurve(QEasingCurve.OutCubic)

        self._slide_out_animation = QPropertyAnimation(self, b"pos", self)
        self._slide_out_animation.setDuration(220)
        self._slide_out_animation.setEasingCurve(QEasingCurve.InCubic)
        self._slide_out_animation.finished.connect(self._finalize_close)

        self.hide()

    def show_toast(self, title: str, message: str, duration_seconds: int = 6) -> None:
        self._title_label.setText(title)
        self._message_label.setText(message)
        self._countdown_timer.stop()
        self._is_closing = False
        self._remaining_seconds = max(1, int(duration_seconds))
        self._deadline_ts = monotonic() + float(self._remaining_seconds)
        self._refresh_countdown_text()
        self.adjustSize()

        start_pos, end_pos, _ = self._calculate_positions()
        if self.isVisible():
            start_pos = self.pos()
        self.move(start_pos)
        self.show()
        self.raise_()

        self._slide_out_animation.stop()
        self._slide_in_animation.stop()
        self._slide_in_animation.setStartValue(start_pos)
        self._slide_in_animation.setEndValue(end_pos)
        self._slide_in_animation.start()

        self._countdown_timer.start()

    def close_with_slide(self) -> None:
        if not self.isVisible() or self._is_closing:
            return
        self._is_closing = True
        self._countdown_timer.stop()
        _, _, out_pos = self._calculate_positions()
        self._slide_in_animation.stop()
        self._slide_out_animation.stop()
        self._slide_out_animation.setStartValue(self.pos())
        self._slide_out_animation.setEndValue(out_pos)
        self._slide_out_animation.start()

    def reposition(self) -> None:
        if not self.isVisible():
            return
        _, end_pos, _ = self._calculate_positions()
        self.move(end_pos)

    def _on_countdown_tick(self) -> None:
        remaining = self._deadline_ts - monotonic()
        display_seconds = max(0, ceil(remaining))
        if display_seconds != self._remaining_seconds:
            self._remaining_seconds = display_seconds
            self._refresh_countdown_text()
        if remaining <= 0:
            self.close_with_slide()
            return

    def _refresh_countdown_text(self) -> None:
        self._countdown_label.setText(
            tr("scan.conflict.toast_countdown", "Auto close in {seconds}s").format(
                seconds=self._remaining_seconds
            )
        )

    def _calculate_positions(self) -> tuple[QPoint, QPoint, QPoint]:
        parent = self.parentWidget()
        if parent is None:
            return QPoint(0, 0), QPoint(0, 0), QPoint(0, 0)

        width = self.width()
        height = self.height()
        x = max(0, parent.width() - width - self._margin)
        end_y = max(0, parent.height() - height - self._margin)
        start_y = parent.height() + height
        out_y = parent.height() + height + self._margin
        return QPoint(x, start_y), QPoint(x, end_y), QPoint(x, out_y)

    def _finalize_close(self) -> None:
        self._countdown_timer.stop()
        self._is_closing = False
        self.hide()
        self.closed.emit()
