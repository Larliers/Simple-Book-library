from __future__ import annotations

import copy
import json
import uuid
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from bookhub.i18n import tr
from bookhub.library.models import DEFAULT_TEXT_PREVIEW_CHARS
from bookhub.library.text_rules import ImportRule, RuleStep, dump_rules_to_json, load_rules_from_json
from bookhub.library.text_rules.rule_preview import (
    build_preview_context,
    find_first_txt_file,
    preview_rule_chain,
    read_txt_preview_sample,
)
from bookhub.library.text_rules.structure_parser import (
    build_structure_report,
    format_structure_signature,
    structure_signature,
)
from bookhub.ui.dialogs.text_rule_help_dialog import TextRuleHelpDialog
from bookhub.ui.dialogs.text_rule_regex_dialog import TextRuleRegexDialog


class TextRuleDialog(QDialog):
    FIELDS = ("title", "author", "series", "tag")
    SOURCE_CODES = ("filename", "stem", "full_path", "parent_folder", "txt_first_line", "txt_head_text")
    PREVIEW_RESULT_HEIGHT_MIN = 96
    PREVIEW_RESULT_HEIGHT_MAX = 420
    PREVIEW_RESULT_HEIGHT_DEFAULT = 180
    STEP_TYPE_CODES = (
        "trim",
        "normalize_spaces",
        "remove_all_spaces",
        "normalize_punctuation",
        "remove_extension",
        "take_bracket_content",
        "take_after_text",
        "take_before_text",
        "take_before_last_text",
        "take_after_last_text",
        "take_between_texts",
        "take_line",
        "take_first_lines",
        "remove_last_lines",
        "remove_first_lines",
        "take_line_range",
        "take_before_marker",
        "take_after_marker",
        "split_and_take",
        "split_multi_and_take",
        "split_and_join_range",
        "remove_prefix",
        "remove_suffix",
        "remove_text",
        "remove_regex",
        "remove_bracket_content",
        "remove_brackets_keep_content",
        "take_last_bracket_content",
        "take_all_bracket_contents",
        "remove_nth_bracket",
        "keep_only_bracket_type",
        "replace_text",
        "regex_extract",
        "loop_lines",
    )
    STEP_CATEGORIES = (
        ("clean", ("trim", "normalize_spaces", "remove_all_spaces", "normalize_punctuation")),
        (
            "delete",
            (
                "remove_prefix",
                "remove_suffix",
                "remove_text",
                "remove_regex",
                "remove_bracket_content",
                "remove_brackets_keep_content",
                "replace_text",
            ),
        ),
        (
            "extract",
            (
                "take_after_text",
                "take_before_text",
                "take_before_last_text",
                "take_after_last_text",
                "take_between_texts",
                "take_before_marker",
                "take_after_marker",
            ),
        ),
        ("line", ("take_line", "take_first_lines", "take_line_range", "remove_first_lines", "remove_last_lines", "loop_lines")),
        (
            "bracket",
            (
                "take_bracket_content",
                "take_last_bracket_content",
                "take_all_bracket_contents",
                "remove_nth_bracket",
                "keep_only_bracket_type",
            ),
        ),
        ("split", ("split_and_take", "split_multi_and_take", "split_and_join_range")),
        ("filename", ("remove_extension",)),
        ("regex", ("regex_extract",)),
    )
    NO_PARAM_STEP_TYPES = {"trim", "remove_extension", "normalize_spaces", "remove_all_spaces", "normalize_punctuation"}

    def __init__(
        self,
        root_path: str,
        rules_json: str,
        parent=None,
        preview_chars: int = DEFAULT_TEXT_PREVIEW_CHARS,
        preview_result_height: int = PREVIEW_RESULT_HEIGHT_DEFAULT,
        preview_result_height_changed: Callable[[int], None] | None = None,
        dialog_size: tuple[int, int] | list[int] | None = None,
        dialog_size_changed: Callable[[int, int], None] | None = None,
        rule_presets: list[dict[str, Any]] | None = None,
        rule_presets_changed: Callable[[list[dict[str, Any]]], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._root_path = root_path
        self._preview_chars = max(100, int(preview_chars or DEFAULT_TEXT_PREVIEW_CHARS))
        self._preview_result_height = self._normalize_preview_result_height(preview_result_height)
        self._preview_result_height_changed = preview_result_height_changed
        self._dialog_size = self._normalize_dialog_size(dialog_size)
        self._dialog_size_changed = dialog_size_changed
        self._rule_presets = self._normalize_rule_presets(rule_presets or [])
        self._rule_presets_changed = rule_presets_changed
        self._current_field_code = "title"
        self._rules_by_field: dict[str, list[ImportRule]] = {field: [] for field in self.FIELDS}
        self._field_buttons: dict[str, QPushButton] = {}
        self._rendering_steps = False
        self._suppress_source_update = False
        self._visible_step_param_keys: dict[int, tuple[str, ...]] = {}
        self._load_rules(rules_json)

        self.setWindowTitle(tr("text.rules.title", "Text Rules"))
        self.resize(*self._dialog_size)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        header = QHBoxLayout()
        title_block = QVBoxLayout()
        title = QLabel(tr("text.rules.title", "Text Rules"))
        title.setObjectName("PageSubtitle")
        title_block.addWidget(title)
        root_label = QLabel(tr("text.rules.root", "Path: {path}").format(path=root_path))
        root_label.setObjectName("PageSubtitle")
        root_label.setWordWrap(True)
        title_block.addWidget(root_label)
        header.addLayout(title_block, 1)
        self.regex_help_btn = QPushButton(tr("text.rules.regex.button", "Common Regex"))
        self.regex_help_btn.setObjectName("GhostButton")
        self.regex_help_btn.clicked.connect(self._open_regex_dialog)
        header.addWidget(self.regex_help_btn, 0, Qt.AlignTop)
        self.help_btn = QPushButton(tr("text.rules.help.button", "Usage Guide"))
        self.help_btn.setObjectName("GhostButton")
        self.help_btn.clicked.connect(self._open_help_dialog)
        header.addWidget(self.help_btn, 0, Qt.AlignTop)
        root.addLayout(header)

        content = QHBoxLayout()
        content.setSpacing(12)
        root.addLayout(content, 1)

        self._build_left_column(content)
        self._build_editor_column(content)
        self._build_preview_column(content)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        save_btn = QPushButton(tr("text.rules.save", "Save"))
        save_btn.setObjectName("PrimaryButton")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton(tr("text.rules.cancel", "Cancel"))
        cancel_btn.setObjectName("GhostButton")
        cancel_btn.clicked.connect(self.reject)
        bottom.addWidget(save_btn)
        bottom.addWidget(cancel_btn)
        root.addLayout(bottom)

        self._load_auto_preview_sample()
        self._refresh_rule_list(selected_row=0)
        self._refresh_structure_diagnostics()
        self._set_multi_preview_placeholder()

    def _build_left_column(self, parent_layout: QHBoxLayout) -> None:
        left = QFrame()
        left.setObjectName("PageSection")
        left.setMinimumWidth(230)
        left.setMaximumWidth(270)
        layout = QVBoxLayout(left)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        layout.addWidget(QLabel(tr("text.rules.field", "Field")))
        field_group = QButtonGroup(self)
        field_group.setExclusive(True)
        for code in self.FIELDS:
            button = QPushButton(self._field_label(code))
            button.setObjectName("TextRuleFieldTab")
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, field=code: self._set_current_field(field))
            field_group.addButton(button)
            self._field_buttons[code] = button
            layout.addWidget(button)
        self._field_buttons[self._current_field_code].setChecked(True)

        layout.addSpacing(8)
        rule_label = QLabel(tr("text.rules.rule_chain", "Rule Chain"))
        rule_label.setObjectName("PageSubtitle")
        layout.addWidget(rule_label)
        self.rule_list = QListWidget()
        self.rule_list.currentRowChanged.connect(self._load_selected_rule)
        layout.addWidget(self.rule_list, 1)

        rule_actions = QHBoxLayout()
        self.add_rule_btn = QPushButton(tr("text.rules.add_rule", "Add Rule"))
        self.add_rule_btn.clicked.connect(self._add_rule)
        self.delete_rule_btn = QPushButton(tr("text.rules.delete_rule", "Delete Rule"))
        self.delete_rule_btn.setObjectName("DangerButton")
        self.delete_rule_btn.clicked.connect(self._delete_rule)
        rule_actions.addWidget(self.add_rule_btn)
        rule_actions.addWidget(self.delete_rule_btn)
        layout.addLayout(rule_actions)

        parent_layout.addWidget(left, 0)

    def _build_editor_column(self, parent_layout: QHBoxLayout) -> None:
        editor = QFrame()
        editor.setObjectName("PageSection")
        editor.setMinimumWidth(520)
        layout = QVBoxLayout(editor)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        source_form = QFormLayout()
        self.source_combo = QComboBox()
        for code in self.SOURCE_CODES:
            self.source_combo.addItem(self._source_label(code), code)
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        source_form.addRow(tr("text.rules.source", "Source"), self.source_combo)
        layout.addLayout(source_form)

        steps_header = QHBoxLayout()
        steps_label = QLabel(tr("text.rules.steps", "Steps"))
        steps_label.setObjectName("PageSubtitle")
        steps_header.addWidget(steps_label)
        steps_header.addStretch(1)
        self.import_preset_top_btn = QPushButton(tr("text.rules.preset.import", "Import Preset"))
        self.import_preset_top_btn.setObjectName("GhostButton")
        self.import_preset_top_btn.clicked.connect(self._import_selected_preset)
        steps_header.addWidget(self.import_preset_top_btn)
        self.save_preset_btn = QPushButton(tr("text.rules.preset.save", "Save Preset"))
        self.save_preset_btn.setObjectName("GhostButton")
        self.save_preset_btn.clicked.connect(self._save_selected_rule_as_preset)
        steps_header.addWidget(self.save_preset_btn)
        self.add_step_btn = QPushButton(tr("text.rules.add_step", "Add Step"))
        self.add_step_btn.setObjectName("GhostButton")
        self.add_step_btn.clicked.connect(self._add_step)
        steps_header.addWidget(self.add_step_btn)
        layout.addLayout(steps_header)

        self.steps_scroll = QScrollArea()
        self.steps_scroll.setObjectName("TextRuleStepsScroll")
        self.steps_scroll.setWidgetResizable(True)
        self.steps_scroll.setFrameShape(QFrame.NoFrame)
        self.steps_container = QWidget()
        self.steps_container.setObjectName("TextRuleStepsContainer")
        self.steps_layout = QVBoxLayout(self.steps_container)
        self.steps_layout.setContentsMargins(0, 0, 0, 0)
        self.steps_layout.setSpacing(8)
        self.steps_scroll.setWidget(self.steps_container)
        layout.addWidget(self.steps_scroll, 1)

        template_box = QFrame()
        template_box.setObjectName("SubtlePanel")
        template_layout = QVBoxLayout(template_box)
        template_layout.setContentsMargins(8, 8, 8, 8)
        template_layout.setSpacing(8)
        builtin_row = QHBoxLayout()
        builtin_row.setSpacing(8)
        builtin_row.addWidget(QLabel(tr("text.rules.templates.title", "Template Rules")))
        self.template_title_btn = QPushButton(tr("text.rules.template.title_line", "Title from first line"))
        self.template_title_btn.clicked.connect(self._insert_template_title_rule)
        builtin_row.addWidget(self.template_title_btn)
        self.template_author_btn = QPushButton(tr("text.rules.template.author_bracket", "Author from bracket"))
        self.template_author_btn.clicked.connect(self._insert_template_author_rule)
        builtin_row.addWidget(self.template_author_btn)
        self.template_fallback_btn = QPushButton(tr("text.rules.template.fallback_stem", "Fallback from stem"))
        self.template_fallback_btn.clicked.connect(self._insert_template_fallback_rule)
        builtin_row.addWidget(self.template_fallback_btn)
        builtin_row.addStretch(1)
        template_layout.addLayout(builtin_row)

        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        preset_row.addWidget(QLabel(tr("text.rules.presets.title", "My Presets")))
        self.preset_combo = QComboBox()
        self.preset_combo.setObjectName("TextRulePresetCombo")
        preset_row.addWidget(self.preset_combo, 1)
        self.import_preset_btn = QPushButton(tr("text.rules.preset.import_current", "Import to current rule"))
        self.import_preset_btn.setObjectName("GhostButton")
        self.import_preset_btn.clicked.connect(self._import_selected_preset)
        preset_row.addWidget(self.import_preset_btn)
        self.delete_preset_btn = QPushButton(tr("text.rules.preset.delete", "Delete Preset"))
        self.delete_preset_btn.setObjectName("DangerButton")
        self.delete_preset_btn.clicked.connect(self._delete_selected_preset)
        preset_row.addWidget(self.delete_preset_btn)
        template_layout.addLayout(preset_row)
        self._refresh_preset_combo()
        layout.addWidget(template_box)

        parent_layout.addWidget(editor, 2)

    def _build_preview_column(self, parent_layout: QHBoxLayout) -> None:
        preview_box = QFrame()
        preview_box.setObjectName("PageSection")
        preview_box.setMinimumWidth(360)
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.setContentsMargins(10, 10, 10, 10)
        preview_layout.setSpacing(8)

        preview_header = QHBoxLayout()
        preview_title = QLabel(tr("text.rules.preview.title", "Preview"))
        preview_title.setObjectName("PageSubtitle")
        preview_header.addWidget(preview_title)
        preview_header.addStretch(1)
        self.preview_auto_btn = QPushButton(tr("text.rules.preview.auto_sample", "Auto sample"))
        self.preview_auto_btn.setObjectName("GhostButton")
        self.preview_auto_btn.clicked.connect(self._load_auto_preview_sample)
        preview_header.addWidget(self.preview_auto_btn)
        self.preview_refresh_btn = QPushButton(tr("text.rules.preview.refresh", "Refresh preview"))
        self.preview_refresh_btn.setObjectName("GhostButton")
        self.preview_refresh_btn.clicked.connect(self._refresh_preview)
        preview_header.addWidget(self.preview_refresh_btn)
        preview_layout.addLayout(preview_header)

        self.preview_splitter = QSplitter(Qt.Vertical)
        self.preview_splitter.setObjectName("TextRulePreviewSplitter")
        self.preview_splitter.setChildrenCollapsible(False)
        self.preview_splitter.setHandleWidth(8)
        self.preview_splitter.splitterMoved.connect(self._on_preview_splitter_moved)

        sample_panel = QWidget()
        sample_layout = QVBoxLayout(sample_panel)
        sample_layout.setContentsMargins(0, 0, 0, 0)
        sample_layout.setSpacing(8)
        preview_form = QFormLayout()
        self.preview_path_edit = QLineEdit()
        self.preview_path_edit.setPlaceholderText(tr("text.rules.preview.path_placeholder", "TXT file path"))
        self.preview_path_edit.textChanged.connect(self._refresh_preview)
        preview_form.addRow(tr("text.rules.preview.path", "Sample file"), self.preview_path_edit)

        self.preview_first_line_edit = QLineEdit()
        self.preview_first_line_edit.setPlaceholderText(
            tr("text.rules.preview.first_line_placeholder", "TXT first line")
        )
        self.preview_first_line_edit.textChanged.connect(self._refresh_preview)
        preview_form.addRow(tr("text.rules.preview.first_line", "First line"), self.preview_first_line_edit)

        self.preview_head_text_edit = QTextEdit()
        self.preview_head_text_edit.setAcceptRichText(False)
        self.preview_head_text_edit.setFixedHeight(120)
        self.preview_head_text_edit.setPlaceholderText(
            tr("text.rules.preview.head_text_placeholder", "TXT head text")
        )
        self.preview_head_text_edit.textChanged.connect(self._refresh_preview)
        preview_form.addRow(tr("text.rules.preview.head_text", "Head text"), self.preview_head_text_edit)
        sample_layout.addLayout(preview_form)

        self.preview_result_box = QFrame()
        self.preview_result_box.setObjectName("TextRulePreviewResult")
        self.preview_result_box.setMinimumHeight(self.PREVIEW_RESULT_HEIGHT_MIN)
        self.preview_result_box.setMaximumHeight(self.PREVIEW_RESULT_HEIGHT_MAX)
        result_layout = QVBoxLayout(self.preview_result_box)
        result_layout.setContentsMargins(10, 8, 10, 8)
        result_layout.setSpacing(4)
        self.preview_result_title = QLabel()
        self.preview_result_title.setObjectName("PageSubtitle")
        self.preview_result_label = QTextEdit()
        self.preview_result_label.setObjectName("TextRulePreviewText")
        self.preview_result_label.setAcceptRichText(False)
        self.preview_result_label.setReadOnly(True)
        self.preview_result_label.setLineWrapMode(QTextEdit.WidgetWidth)
        self.preview_result_label.setFrameShape(QFrame.NoFrame)
        self.preview_result_label.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.preview_result_label.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.preview_result_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        result_layout.addWidget(self.preview_result_title)
        result_layout.addWidget(self.preview_result_label, 1)
        self.preview_splitter.addWidget(sample_panel)
        self.preview_splitter.addWidget(self.preview_result_box)
        self.preview_splitter.setStretchFactor(0, 1)
        self.preview_splitter.setStretchFactor(1, 0)
        self._apply_preview_result_height(self._preview_result_height)
        preview_layout.addWidget(self.preview_splitter, 1)

        diagnostic_box = QFrame()
        diagnostic_box.setObjectName("SubtlePanel")
        diagnostic_layout = QVBoxLayout(diagnostic_box)
        diagnostic_layout.setContentsMargins(8, 8, 8, 8)
        diagnostic_layout.setSpacing(6)
        diagnostic_header = QHBoxLayout()
        diagnostic_title = QLabel(tr("text.rules.structure.title", "Format diagnostics"))
        diagnostic_title.setObjectName("PageSubtitle")
        diagnostic_header.addWidget(diagnostic_title)
        diagnostic_header.addStretch(1)
        self.structure_refresh_btn = QPushButton(tr("text.rules.structure.refresh", "Refresh"))
        self.structure_refresh_btn.setObjectName("GhostButton")
        self.structure_refresh_btn.clicked.connect(self._refresh_structure_diagnostics)
        diagnostic_header.addWidget(self.structure_refresh_btn)
        diagnostic_layout.addLayout(diagnostic_header)

        self.structure_result_label = QTextEdit()
        self.structure_result_label.setObjectName("TextRulePreviewText")
        self.structure_result_label.setAcceptRichText(False)
        self.structure_result_label.setReadOnly(True)
        self.structure_result_label.setFrameShape(QFrame.NoFrame)
        self.structure_result_label.setFixedHeight(96)
        self.structure_result_label.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.structure_result_label.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        diagnostic_layout.addWidget(self.structure_result_label)
        preview_layout.addWidget(diagnostic_box, 0)

        multi_box = QFrame()
        multi_box.setObjectName("SubtlePanel")
        multi_layout = QVBoxLayout(multi_box)
        multi_layout.setContentsMargins(8, 8, 8, 8)
        multi_layout.setSpacing(6)
        multi_header = QHBoxLayout()
        multi_title = QLabel(tr("text.rules.multi_preview.title", "Multi-sample preview"))
        multi_title.setObjectName("PageSubtitle")
        multi_header.addWidget(multi_title)
        multi_header.addStretch(1)
        self.multi_preview_btn = QPushButton(tr("text.rules.multi_preview.run", "Run"))
        self.multi_preview_btn.setObjectName("GhostButton")
        self.multi_preview_btn.clicked.connect(self._run_multi_sample_preview)
        multi_header.addWidget(self.multi_preview_btn)
        multi_layout.addLayout(multi_header)

        self.multi_preview_list = QListWidget()
        self.multi_preview_list.setObjectName("TextRuleMultiPreviewList")
        self.multi_preview_list.setFixedHeight(150)
        self.multi_preview_list.itemClicked.connect(self._load_multi_preview_item)
        multi_layout.addWidget(self.multi_preview_list)
        preview_layout.addWidget(multi_box, 0)

        parent_layout.addWidget(preview_box, 1)

    def _load_rules(self, rules_json: str) -> None:
        try:
            decoded = json.loads(rules_json) if str(rules_json or "").strip() else {}
        except json.JSONDecodeError:
            decoded = {}
        parsed = load_rules_from_json(decoded)
        for field_name in self.FIELDS:
            self._rules_by_field[field_name] = list(parsed.get(field_name, []))

    def rules_json(self) -> str:
        payload = dump_rules_to_json(self._rules_by_field)
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _current_field(self) -> str:
        return self._current_field_code

    def _current_rules(self) -> list[ImportRule]:
        return self._rules_by_field[self._current_field()]

    def _set_current_field(self, field: str) -> None:
        if field not in self.FIELDS or field == self._current_field_code:
            return
        self._current_field_code = field
        button = self._field_buttons.get(field)
        if button is not None:
            button.setChecked(True)
        self._refresh_rule_list(selected_row=0)

    def _refresh_rule_list(self, selected_row: int | None = None) -> None:
        previous_row = self.rule_list.currentRow()
        target_row = previous_row if selected_row is None else selected_row
        self.rule_list.blockSignals(True)
        self.rule_list.clear()
        for idx, rule in enumerate(self._current_rules(), start=1):
            self.rule_list.addItem(QListWidgetItem(self._format_rule_item(idx, rule)))
        if self.rule_list.count() > 0:
            target_row = max(0, min(target_row, self.rule_list.count() - 1))
            self.rule_list.setCurrentRow(target_row)
        self.rule_list.blockSignals(False)
        self._load_selected_rule()
        self._refresh_preview()

    def _format_rule_item(self, index: int, rule: ImportRule) -> str:
        return tr("text.rules.rule_item", "{index}. Source: {source} · Steps: {count}").format(
            index=index,
            source=self._source_label(rule.source),
            count=len(rule.steps),
        )

    def _load_selected_rule(self) -> None:
        idx = self.rule_list.currentRow()
        rules = self._current_rules()
        has_rule = 0 <= idx < len(rules)
        self.add_step_btn.setEnabled(has_rule)
        self.delete_rule_btn.setEnabled(has_rule)
        if not has_rule:
            self._set_source_combo("filename")
            self._render_steps([])
            self._refresh_preview()
            return
        rule = rules[idx]
        self._set_source_combo(rule.source)
        self._render_steps(rule.steps)
        self._refresh_preview()

    def _set_source_combo(self, source: str) -> None:
        self._suppress_source_update = True
        source_idx = self.source_combo.findData(source)
        self.source_combo.setCurrentIndex(source_idx if source_idx >= 0 else 0)
        self._suppress_source_update = False

    def _on_source_changed(self) -> None:
        if self._suppress_source_update:
            return
        rule_idx = self.rule_list.currentRow()
        rules = self._current_rules()
        if rule_idx < 0 or rule_idx >= len(rules):
            return
        rules[rule_idx].source = str(self.source_combo.currentData() or "filename")
        item = self.rule_list.item(rule_idx)
        if item is not None:
            item.setText(self._format_rule_item(rule_idx + 1, rules[rule_idx]))
        self._refresh_preview()

    def _render_steps(self, steps: list[RuleStep]) -> None:
        self._rendering_steps = True
        self._visible_step_param_keys = {}
        while self.steps_layout.count():
            item = self.steps_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not steps:
            empty = QLabel(tr("text.rules.steps.empty", "No steps yet."))
            empty.setObjectName("PageSubtitle")
            empty.setAlignment(Qt.AlignCenter)
            self.steps_layout.addWidget(empty)
            self.steps_layout.addStretch(1)
            self._rendering_steps = False
            return

        for index, step in enumerate(steps):
            self.steps_layout.addWidget(self._build_step_card(index, step))
        self.steps_layout.addStretch(1)
        self._rendering_steps = False

    def _build_step_card(self, step_index: int, step: RuleStep) -> QFrame:
        card = QFrame()
        card.setObjectName("TextRuleStepCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel(
            tr("text.rules.step_card.title", "{index}. {step}").format(
                index=step_index + 1,
                step=self._step_type_label(step.type),
            )
        )
        title.setObjectName("PageSubtitle")
        header.addWidget(title)
        header.addStretch(1)

        up_btn = QPushButton(tr("text.rules.step_up", "Step Up"))
        up_btn.setObjectName("GhostButton")
        up_btn.setEnabled(step_index > 0)
        up_btn.clicked.connect(lambda _=False, idx=step_index: self._move_step(idx, -1))
        header.addWidget(up_btn)
        down_btn = QPushButton(tr("text.rules.step_down", "Step Down"))
        down_btn.setObjectName("GhostButton")
        down_btn.setEnabled(step_index < len(self._selected_steps()) - 1)
        down_btn.clicked.connect(lambda _=False, idx=step_index: self._move_step(idx, 1))
        header.addWidget(down_btn)
        delete_btn = QPushButton(tr("text.rules.delete_step", "Delete Step"))
        delete_btn.setObjectName("DangerButton")
        delete_btn.clicked.connect(lambda _=False, idx=step_index: self._delete_step(idx))
        header.addWidget(delete_btn)
        layout.addLayout(header)

        form = QFormLayout()
        category_combo = QComboBox()
        category_combo.setObjectName("TextRuleStepCategoryCombo")
        for code, text in self._step_category_options():
            category_combo.addItem(text, code)
        category = self._category_for_step_type(step.type)
        category_idx = category_combo.findData(category)
        category_combo.setCurrentIndex(category_idx if category_idx >= 0 else 0)
        category_combo.currentIndexChanged.connect(
            lambda _=0, idx=step_index, combo=category_combo: self._on_step_category_changed(idx, combo)
        )
        form.addRow(tr("text.rules.param.category", "Category"), category_combo)

        type_combo = QComboBox()
        type_combo.setObjectName("TextRuleStepTypeCombo")
        for code in self._step_codes_for_category(category):
            type_combo.addItem(self._step_type_label(code), code)
        type_idx = type_combo.findData(step.type)
        type_combo.setCurrentIndex(type_idx if type_idx >= 0 else 0)
        type_combo.currentIndexChanged.connect(
            lambda _=0, idx=step_index, combo=type_combo: self._on_step_type_changed(idx, combo)
        )
        form.addRow(tr("text.rules.param.type", "Type"), type_combo)

        param_keys = self._param_keys_for_step_type(step.type)
        self._visible_step_param_keys[step_index] = param_keys
        if not param_keys:
            no_params = QLabel(tr("text.rules.step.no_params", "(No parameters)"))
            no_params.setObjectName("PageSubtitle")
            form.addRow("", no_params)
        for key in param_keys:
            self._add_param_widget(form, step_index, step, key)
        layout.addLayout(form)
        return card

    def _add_param_widget(self, form: QFormLayout, step_index: int, step: RuleStep, key: str) -> None:
        label = self._param_label_for_step(step.type, key)
        if step.type in {"take_line_range", "split_and_join_range"} and key in {"start", "end"}:
            widget = QSpinBox()
            widget.setRange(1, 999)
            widget.setValue(self._safe_int(step.params.get(key), 1))
            widget.valueChanged.connect(lambda value, idx=step_index, param=key: self._set_step_param(idx, param, value))
            form.addRow(label, widget)
            return

        if key == "separators":
            widget = QTextEdit()
            widget.setAcceptRichText(False)
            widget.setFixedHeight(64)
            widget.setPlainText(str(step.params.get(key) or ""))
            widget.textChanged.connect(
                lambda idx=step_index, param=key, edit=widget: self._set_step_param(idx, param, edit.toPlainText())
            )
            form.addRow(label, widget)
            return

        if key == "bracket":
            widget = QComboBox()
            widget.addItems(["[]", "［］", "【】", "()", "（）", "<>", "＜＞", "《》", "「」", "『』"])
            value = str(step.params.get("bracket") or "[]")
            value_idx = widget.findText(value)
            widget.setCurrentIndex(value_idx if value_idx >= 0 else 0)
            widget.currentTextChanged.connect(lambda text, idx=step_index: self._set_step_param(idx, "bracket", text))
            form.addRow(label, widget)
            return

        if key == "bracket_scope":
            widget = QComboBox()
            for code, text in self._bracket_scope_options():
                widget.addItem(text, code)
            value_idx = widget.findData(str(step.params.get("bracket_scope") or "outer"))
            widget.setCurrentIndex(value_idx if value_idx >= 0 else 0)
            widget.currentIndexChanged.connect(
                lambda _=0, idx=step_index, combo=widget: self._set_combo_step_param(idx, "bracket_scope", combo)
            )
            form.addRow(label, widget)
            return

        if key == "bracket_type":
            widget = QComboBox()
            for code, text in self._bracket_type_options():
                widget.addItem(text, code)
            value_idx = widget.findData(str(step.params.get("bracket_type") or "all"))
            widget.setCurrentIndex(value_idx if value_idx >= 0 else 0)
            widget.currentIndexChanged.connect(
                lambda _=0, idx=step_index, combo=widget: self._set_combo_step_param(idx, "bracket_type", combo)
            )
            form.addRow(label, widget)
            return

        if key == "scope":
            widget = QComboBox()
            for code, text in self._scope_options():
                widget.addItem(text, code)
            value_idx = widget.findData(str(step.params.get("scope") or "all"))
            widget.setCurrentIndex(value_idx if value_idx >= 0 else 0)
            widget.currentIndexChanged.connect(
                lambda _=0, idx=step_index, combo=widget: self._set_combo_step_param(idx, "scope", combo, rerender=True)
            )
            form.addRow(label, widget)
            return

        if key == "unit":
            widget = QComboBox()
            for code, text in self._unit_options():
                widget.addItem(text, code)
            value_idx = widget.findData(str(step.params.get("unit") or "line"))
            widget.setCurrentIndex(value_idx if value_idx >= 0 else 0)
            widget.currentIndexChanged.connect(
                lambda _=0, idx=step_index, combo=widget: self._set_combo_step_param(idx, "unit", combo)
            )
            form.addRow(label, widget)
            return

        if key == "join":
            widget = QComboBox()
            for code, text in self._join_options():
                widget.addItem(text, code)
            value_idx = widget.findData(str(step.params.get("join") or "newline"))
            widget.setCurrentIndex(value_idx if value_idx >= 0 else 0)
            widget.currentIndexChanged.connect(
                lambda _=0, idx=step_index, combo=widget: self._set_combo_step_param(idx, "join", combo, rerender=True)
            )
            form.addRow(label, widget)
            return

        if key == "skip_failed":
            widget = QComboBox()
            for value, text in self._skip_failed_options():
                widget.addItem(text, value)
            value_idx = widget.findData(self._safe_bool(step.params.get("skip_failed"), True))
            widget.setCurrentIndex(value_idx if value_idx >= 0 else 0)
            widget.currentIndexChanged.connect(
                lambda _=0, idx=step_index, combo=widget: self._set_combo_step_param(idx, "skip_failed", combo)
            )
            form.addRow(label, widget)
            return

        if key == "case_sensitive":
            widget = QComboBox()
            for value, text in self._case_sensitive_options():
                widget.addItem(text, value)
            value_idx = widget.findData(self._safe_bool(step.params.get("case_sensitive"), True))
            widget.setCurrentIndex(value_idx if value_idx >= 0 else 0)
            widget.currentIndexChanged.connect(
                lambda _=0, idx=step_index, combo=widget: self._set_combo_step_param(idx, "case_sensitive", combo)
            )
            form.addRow(label, widget)
            return

        if key in {"index", "group", "count"}:
            widget = QSpinBox()
            widget.setRange(0 if key == "group" else 1, 999)
            widget.setValue(self._safe_int(step.params.get(key), 1))
            if key == "count" and step.type in {"take_before_marker", "take_after_marker"} and str(step.params.get("scope") or "all") == "all":
                widget.setEnabled(False)
            widget.valueChanged.connect(lambda value, idx=step_index, param=key: self._set_step_param(idx, param, value))
            form.addRow(label, widget)
            return

        widget = QLineEdit()
        widget.setText(str(step.params.get(key) or ""))
        if key == "custom_separator" and str(step.params.get("join") or "newline") != "custom":
            widget.setEnabled(False)
        widget.textChanged.connect(lambda text, idx=step_index, param=key: self._set_step_param(idx, param, text))
        form.addRow(label, widget)

    def _selected_steps(self) -> list[RuleStep]:
        rule_idx = self.rule_list.currentRow()
        rules = self._current_rules()
        if rule_idx < 0 or rule_idx >= len(rules):
            return []
        return rules[rule_idx].steps

    def _on_step_category_changed(self, step_index: int, combo: QComboBox) -> None:
        if self._rendering_steps:
            return
        steps = self._selected_steps()
        if step_index < 0 or step_index >= len(steps):
            return
        codes = self._step_codes_for_category(str(combo.currentData() or "clean"))
        new_type = codes[0] if codes else "trim"
        steps[step_index] = RuleStep(type=new_type, params=self._default_params_for_step_type(new_type, {}))
        self._render_steps(steps)
        self._refresh_rule_list_label()
        self._refresh_preview()

    def _on_step_type_changed(self, step_index: int, combo: QComboBox) -> None:
        if self._rendering_steps:
            return
        steps = self._selected_steps()
        if step_index < 0 or step_index >= len(steps):
            return
        new_type = str(combo.currentData() or "trim")
        steps[step_index] = RuleStep(type=new_type, params=self._default_params_for_step_type(new_type, steps[step_index].params))
        self._render_steps(steps)
        self._refresh_rule_list_label()
        self._refresh_preview()

    def _set_step_param(self, step_index: int, key: str, value: object) -> None:
        if self._rendering_steps:
            return
        steps = self._selected_steps()
        if step_index < 0 or step_index >= len(steps):
            return
        steps[step_index].params[key] = value
        self._refresh_preview()

    def _set_combo_step_param(self, step_index: int, key: str, combo: QComboBox, *, rerender: bool = False) -> None:
        if self._rendering_steps:
            return
        steps = self._selected_steps()
        if step_index < 0 or step_index >= len(steps):
            return
        data = combo.currentData()
        steps[step_index].params[key] = data if data is not None else ""
        if rerender:
            self._render_steps(steps)
        self._refresh_preview()

    def _add_step(self) -> None:
        steps = self._selected_steps()
        if not steps and self.rule_list.currentRow() < 0:
            QMessageBox.warning(
                self,
                tr("text.rules.need_rule", "No rule selected"),
                tr("text.rules.need_rule_msg", "Please add/select a rule first."),
            )
            return
        steps.append(RuleStep(type="trim", params={}))
        self._render_steps(steps)
        self._refresh_rule_list_label()
        self._refresh_preview()

    def _delete_step(self, step_index: int) -> None:
        steps = self._selected_steps()
        if step_index < 0 or step_index >= len(steps):
            return
        del steps[step_index]
        self._render_steps(steps)
        self._refresh_rule_list_label()
        self._refresh_preview()

    def _move_step(self, step_index: int, offset: int) -> None:
        steps = self._selected_steps()
        target = step_index + offset
        if step_index < 0 or step_index >= len(steps) or target < 0 or target >= len(steps):
            return
        steps[step_index], steps[target] = steps[target], steps[step_index]
        self._render_steps(steps)
        self._refresh_preview()

    def _refresh_rule_list_label(self) -> None:
        rule_idx = self.rule_list.currentRow()
        rules = self._current_rules()
        if rule_idx < 0 or rule_idx >= len(rules):
            return
        item = self.rule_list.item(rule_idx)
        if item is not None:
            item.setText(self._format_rule_item(rule_idx + 1, rules[rule_idx]))

    def _build_rule_from_form(self) -> ImportRule:
        source = str(self.source_combo.currentData() or "filename")
        return ImportRule(field=self._current_field(), source=source, steps=[])

    def _add_rule(self) -> None:
        rules = self._current_rules()
        rule = self._build_rule_from_form()
        rules.append(rule)
        self._refresh_rule_list(selected_row=len(rules) - 1)

    def _delete_rule(self) -> None:
        idx = self.rule_list.currentRow()
        rules = self._current_rules()
        if idx < 0 or idx >= len(rules):
            return
        del rules[idx]
        self._refresh_rule_list(selected_row=min(idx, len(rules) - 1))

    def _selected_rule(self) -> ImportRule | None:
        idx = self.rule_list.currentRow()
        rules = self._current_rules()
        if idx < 0 or idx >= len(rules):
            return None
        return rules[idx]

    def _save_selected_rule_as_preset(self) -> None:
        rule = self._selected_rule()
        if rule is None:
            QMessageBox.warning(
                self,
                tr("text.rules.preset.need_rule", "No rule selected"),
                tr("text.rules.preset.need_rule_msg", "Please add/select a rule first."),
            )
            return

        name, ok = QInputDialog.getText(
            self,
            tr("text.rules.preset.save", "Save Preset"),
            tr("text.rules.preset.name_prompt", "Preset name:"),
        )
        name = str(name or "").strip()
        if not ok or not name:
            return

        rule_label = tr("text.rules.preset.kind.rule", "Full rule")
        steps_label = tr("text.rules.preset.kind.steps", "Steps only")
        kind_text, ok = QInputDialog.getItem(
            self,
            tr("text.rules.preset.kind_title", "Preset Type"),
            tr("text.rules.preset.kind_prompt", "Save as:"),
            [rule_label, steps_label],
            0,
            False,
        )
        if not ok:
            return
        kind = "steps" if kind_text == steps_label else "rule"
        self._add_rule_preset(name, kind, rule)

    def _add_rule_preset(self, name: str, kind: str, rule: ImportRule) -> dict[str, Any]:
        steps = [step.to_dict() for step in rule.steps]
        preset: dict[str, Any] = {
            "id": uuid.uuid4().hex,
            "kind": "steps" if kind == "steps" else "rule",
            "name": str(name or "Preset").strip() or "Preset",
            "steps": copy.deepcopy(steps),
        }
        if preset["kind"] == "rule":
            preset["source"] = str(rule.source or "filename")
        self._set_rule_presets([*self._rule_presets, preset])
        return preset

    def _import_selected_preset(self) -> None:
        preset = self._selected_preset()
        if preset is None:
            QMessageBox.warning(
                self,
                tr("text.rules.preset.none", "No preset"),
                tr("text.rules.preset.none_msg", "No preset is selected."),
            )
            return

        steps = self._steps_from_preset(preset)
        if str(preset.get("kind") or "") == "rule":
            rules = self._current_rules()
            rules.append(
                ImportRule(
                    field=self._current_field(),
                    source=str(preset.get("source") or "filename"),
                    steps=steps,
                )
            )
            self._refresh_rule_list(selected_row=len(rules) - 1)
            return

        rule = self._selected_rule()
        if rule is None:
            QMessageBox.warning(
                self,
                tr("text.rules.preset.need_rule", "No rule selected"),
                tr("text.rules.preset.need_rule_msg", "Please add/select a rule first."),
            )
            return
        rule.steps.extend(steps)
        self._render_steps(rule.steps)
        self._refresh_rule_list_label()
        self._refresh_preview()

    def _delete_selected_preset(self) -> None:
        preset = self._selected_preset()
        if preset is None:
            return
        result = QMessageBox.question(
            self,
            tr("text.rules.preset.delete", "Delete Preset"),
            tr("text.rules.preset.delete_confirm", "Delete preset {name}?").format(
                name=str(preset.get("name") or "")
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if result == QMessageBox.Yes:
            self._remove_rule_preset_by_id(str(preset.get("id") or ""))

    def _remove_rule_preset_by_id(self, preset_id: str) -> None:
        self._set_rule_presets([item for item in self._rule_presets if str(item.get("id") or "") != preset_id])

    def _selected_preset(self) -> dict[str, Any] | None:
        if not hasattr(self, "preset_combo"):
            return None
        preset_id = str(self.preset_combo.currentData() or "")
        for preset in self._rule_presets:
            if str(preset.get("id") or "") == preset_id:
                return copy.deepcopy(preset)
        return None

    def _steps_from_preset(self, preset: dict[str, Any]) -> list[RuleStep]:
        steps: list[RuleStep] = []
        for item in preset.get("steps") or []:
            if isinstance(item, dict):
                steps.append(RuleStep.from_dict(copy.deepcopy(item)))
        return steps

    def _set_rule_presets(self, presets: list[dict[str, Any]]) -> None:
        self._rule_presets = self._normalize_rule_presets(presets)
        self._refresh_preset_combo()
        if self._rule_presets_changed is not None:
            self._rule_presets_changed(copy.deepcopy(self._rule_presets))

    def _refresh_preset_combo(self) -> None:
        if not hasattr(self, "preset_combo"):
            return
        current_id = str(self.preset_combo.currentData() or "")
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        for preset in self._rule_presets:
            self.preset_combo.addItem(self._format_preset_label(preset), str(preset.get("id") or ""))
        if current_id:
            index = self.preset_combo.findData(current_id)
            if index >= 0:
                self.preset_combo.setCurrentIndex(index)
        self.preset_combo.blockSignals(False)
        has_presets = self.preset_combo.count() > 0
        self.preset_combo.setEnabled(has_presets)
        self.import_preset_btn.setEnabled(has_presets)
        self.import_preset_top_btn.setEnabled(has_presets)
        self.delete_preset_btn.setEnabled(has_presets)

    def _open_help_dialog(self) -> None:
        dialog = TextRuleHelpDialog(self)
        dialog.exec()

    def _open_regex_dialog(self) -> None:
        dialog = TextRuleRegexDialog(self)
        dialog.exec()

    def _insert_template_title_rule(self) -> None:
        self._current_rules().append(
            ImportRule(
                field=self._current_field(),
                source="txt_first_line",
                steps=[
                    RuleStep(type="take_after_text", params={"value": "T"}),
                    RuleStep(type="trim", params={}),
                ],
            )
        )
        self._refresh_rule_list(selected_row=self.rule_list.count())

    def _insert_template_author_rule(self) -> None:
        self._current_rules().append(
            ImportRule(
                field=self._current_field(),
                source="filename",
                steps=[
                    RuleStep(type="take_bracket_content", params={"bracket": "【】", "index": 1}),
                    RuleStep(type="trim", params={}),
                ],
            )
        )
        self._refresh_rule_list(selected_row=self.rule_list.count())

    def _insert_template_fallback_rule(self) -> None:
        self._current_rules().append(
            ImportRule(
                field=self._current_field(),
                source="stem",
                steps=[RuleStep(type="trim", params={})],
            )
        )
        self._refresh_rule_list(selected_row=self.rule_list.count())

    def _load_auto_preview_sample(self) -> None:
        sample_path = find_first_txt_file(self._root_path)
        if not sample_path:
            self._refresh_preview()
            return
        sample = read_txt_preview_sample(sample_path, self._preview_chars)
        if sample is None:
            self._refresh_preview()
            return

        self.preview_path_edit.blockSignals(True)
        self.preview_first_line_edit.blockSignals(True)
        self.preview_head_text_edit.blockSignals(True)
        self.preview_path_edit.setText(sample.file_path)
        self.preview_first_line_edit.setText(sample.txt_first_line)
        self.preview_head_text_edit.setPlainText(sample.txt_head_text)
        self.preview_path_edit.blockSignals(False)
        self.preview_first_line_edit.blockSignals(False)
        self.preview_head_text_edit.blockSignals(False)
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        if not hasattr(self, "preview_result_label"):
            return

        file_path = self.preview_path_edit.text().strip()
        first_line = self.preview_first_line_edit.text()
        head_text = self.preview_head_text_edit.toPlainText()
        if not file_path and not first_line and not head_text:
            self._set_preview_result(
                "empty",
                tr("text.rules.preview.status.empty", "No sample"),
                tr("text.rules.preview.no_sample", "No TXT sample found."),
            )
            return

        rules = self._current_rules()
        if not rules:
            self._set_preview_result(
                "empty",
                tr("text.rules.preview.status.empty", "No rules"),
                tr("text.rules.preview.no_rules", "No rules for current field."),
            )
            return

        context = build_preview_context(file_path, first_line, head_text)
        result = preview_rule_chain(rules, context)
        if result.success:
            warning = str(result.warning_message or "").strip()
            message = tr("text.rules.preview.success", "{field}: {value}").format(
                field=self._field_label(self._current_field()),
                value=result.value,
            )
            if warning:
                message = tr("text.rules.preview.warning", "{value}\n\nReminder: {warning}").format(
                    value=message,
                    warning=warning,
                )
            self._set_preview_result(
                "warning" if warning else "success",
                tr("text.rules.preview.status.warning", "Matched with warning")
                if warning
                else tr("text.rules.preview.status.success", "Matched"),
                message,
            )
            return

        failed_step = result.failed_step or tr("text.rules.preview.unknown_step", "unknown")
        error_message = result.error_message or tr("text.rules.preview.unknown_error", "Unknown error")
        self._set_preview_result(
            "failed",
            tr("text.rules.preview.status.failed", "Failed"),
            tr("text.rules.preview.failed", "Failed at {step}: {error}").format(
                step=failed_step,
                error=error_message,
            ),
        )

    def _set_preview_result(self, state: str, title: str, message: str) -> None:
        self.preview_result_box.setProperty("state", state)
        self.preview_result_title.setText(title)
        self.preview_result_label.setPlainText(message)
        self.preview_result_box.style().unpolish(self.preview_result_box)
        self.preview_result_box.style().polish(self.preview_result_box)

    def _refresh_structure_diagnostics(self) -> None:
        if not hasattr(self, "structure_result_label"):
            return
        samples = self._sample_txt_rows(limit=80)
        if not samples:
            self.structure_result_label.setPlainText(
                tr("text.rules.structure.no_samples", "No TXT samples for format diagnostics.")
            )
            return
        filenames = [sample["filename"] for sample in samples]
        report = build_structure_report(filenames)
        dominant = report.dominant_group
        if dominant is None:
            self.structure_result_label.setPlainText(
                tr("text.rules.structure.no_samples", "No TXT samples for format diagnostics.")
            )
            return

        lines = [
            tr("text.rules.structure.sample_count", "Samples: {count}").format(count=report.total),
            tr("text.rules.structure.main_format", "Main format: {format}").format(
                format=format_structure_signature(dominant.signature)
            ),
            tr("text.rules.structure.consistency", "Consistency: {score:.0f}% ({count}/{total})").format(
                score=report.consistency_score,
                count=dominant.count,
                total=report.total,
            ),
        ]
        if len(report.groups) > 1:
            lines.append(tr("text.rules.structure.groups", "Groups: {count}").format(count=len(report.groups)))
        for group_index, group in enumerate(report.groups[:5], start=1):
            signature = group.signature
            group_samples = [
                sample["relative_path"]
                for sample in samples
                if structure_signature(sample["filename"]) == signature
            ][:3]
            lines.append(
                tr("text.rules.structure.group_item", "Group {index}: {count} samples, {format}").format(
                    index=group_index,
                    count=group.count,
                    format=format_structure_signature(signature),
                )
            )
            lines.extend(f"  {value}" for value in group_samples)
        if report.outlier_samples:
            lines.append(tr("text.rules.structure.outliers", "Outliers:"))
            dominant_signature = dominant.signature
            outlier_paths = [
                sample["relative_path"]
                for sample in samples
                if structure_signature(sample["filename"]) != dominant_signature
            ][:5]
            lines.extend(f"  {value}" for value in outlier_paths)
        else:
            lines.append(tr("text.rules.structure.no_outliers", "Outliers: none"))
        self.structure_result_label.setPlainText("\n".join(lines))

    def _sample_txt_rows(self, *, limit: int) -> list[dict[str, str]]:
        root = Path(self._root_path)
        if not root.exists():
            return []
        values: list[dict[str, str]] = []
        try:
            iterator = root.rglob("*.txt") if root.is_dir() else [root]
            for file_path in iterator:
                if len(values) >= limit:
                    break
                if file_path.is_file():
                    try:
                        relative_path = str(file_path.relative_to(root)) if root.is_dir() else file_path.name
                    except ValueError:
                        relative_path = file_path.name
                    values.append(
                        {
                            "path": str(file_path),
                            "relative_path": relative_path,
                            "filename": file_path.name,
                        }
                    )
        except OSError:
            return []
        return sorted(values, key=lambda item: item["relative_path"].lower())

    def _set_multi_preview_placeholder(self) -> None:
        if not hasattr(self, "multi_preview_list"):
            return
        self.multi_preview_list.clear()
        self.multi_preview_list.addItem(tr("text.rules.multi_preview.placeholder", "Run multi-sample preview to validate current rules."))

    def _run_multi_sample_preview(self) -> None:
        if not hasattr(self, "multi_preview_list"):
            return
        self.multi_preview_list.clear()
        rows = self._sample_txt_rows(limit=20)
        if not rows:
            self.multi_preview_list.addItem(tr("text.rules.multi_preview.no_samples", "No TXT samples."))
            return
        rules = self._current_rules()
        if not rules:
            self.multi_preview_list.addItem(tr("text.rules.preview.no_rules", "No rules for current field."))
            return
        for row in rows:
            sample = read_txt_preview_sample(row["path"], self._preview_chars)
            if sample is None:
                text = tr("text.rules.multi_preview.unreadable", "FAIL {path}: unreadable").format(
                    path=row["relative_path"]
                )
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, row["path"])
                self.multi_preview_list.addItem(item)
                continue
            context = build_preview_context(sample.file_path, sample.txt_first_line, sample.txt_head_text)
            result = preview_rule_chain(rules, context)
            if result.success:
                value = str(result.value or "").replace("\n", " / ")
                text = tr("text.rules.multi_preview.success", "OK {path}: {value}").format(
                    path=row["relative_path"],
                    value=value[:120],
                )
            else:
                failed_step = result.failed_step or tr("text.rules.preview.unknown_step", "unknown")
                error = result.error_message or tr("text.rules.preview.unknown_error", "Unknown error")
                text = tr("text.rules.multi_preview.failed", "FAIL {path}: {step} - {error}").format(
                    path=row["relative_path"],
                    step=failed_step,
                    error=str(error)[:80],
                )
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, row["path"])
            self.multi_preview_list.addItem(item)

    def _load_multi_preview_item(self, item: QListWidgetItem) -> None:
        file_path = str(item.data(Qt.UserRole) or "")
        if not file_path:
            return
        sample = read_txt_preview_sample(file_path, self._preview_chars)
        if sample is None:
            return
        self.preview_path_edit.blockSignals(True)
        self.preview_first_line_edit.blockSignals(True)
        self.preview_head_text_edit.blockSignals(True)
        self.preview_path_edit.setText(sample.file_path)
        self.preview_first_line_edit.setText(sample.txt_first_line)
        self.preview_head_text_edit.setPlainText(sample.txt_head_text)
        self.preview_path_edit.blockSignals(False)
        self.preview_first_line_edit.blockSignals(False)
        self.preview_head_text_edit.blockSignals(False)
        self._refresh_preview()

    def _apply_preview_result_height(self, height: int) -> None:
        height = self._normalize_preview_result_height(height)
        self._preview_result_height = height
        sample_height = max(180, 560 - height)
        self.preview_splitter.setSizes([sample_height, height])

    def _on_preview_splitter_moved(self, _pos: int, _index: int) -> None:
        sizes = self.preview_splitter.sizes()
        if len(sizes) < 2:
            return
        self._preview_result_height = self._normalize_preview_result_height(sizes[1])

    def _save_preview_result_height(self) -> None:
        if self._preview_result_height_changed is not None:
            self._preview_result_height_changed(self._preview_result_height)

    def _save_dialog_size(self) -> None:
        if self._dialog_size_changed is not None:
            size = self.size()
            width, height = self._normalize_dialog_size((size.width(), size.height()))
            self._dialog_size_changed(width, height)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._save_preview_result_height()
        self._save_dialog_size()
        super().closeEvent(event)

    def accept(self) -> None:
        self._save_preview_result_height()
        self._save_dialog_size()
        super().accept()

    def reject(self) -> None:
        self._save_preview_result_height()
        self._save_dialog_size()
        super().reject()

    def _param_keys_for_step_type(self, step_type: str) -> tuple[str, ...]:
        if step_type in self.NO_PARAM_STEP_TYPES:
            return ()
        if step_type in {"take_after_text", "take_before_text", "take_before_last_text", "take_after_last_text", "remove_prefix", "remove_suffix"}:
            return ("value",)
        if step_type == "take_between_texts":
            return ("start", "end")
        if step_type == "take_line":
            return ("index",)
        if step_type == "take_first_lines":
            return ("count",)
        if step_type == "remove_last_lines":
            return ("count",)
        if step_type == "remove_first_lines":
            return ("count",)
        if step_type == "take_line_range":
            return ("start", "end")
        if step_type in {"take_before_marker", "take_after_marker"}:
            return ("value", "scope", "unit", "count")
        if step_type == "split_and_take":
            return ("separator", "index")
        if step_type == "split_multi_and_take":
            return ("separators", "index")
        if step_type == "split_and_join_range":
            return ("separator", "start", "end", "joiner")
        if step_type == "take_bracket_content":
            return ("bracket", "bracket_scope", "index")
        if step_type == "remove_text":
            return ("text", "case_sensitive")
        if step_type == "remove_regex":
            return ("pattern",)
        if step_type in {"remove_bracket_content", "remove_brackets_keep_content"}:
            return ("bracket_type", "bracket_scope")
        if step_type == "take_last_bracket_content":
            return ("bracket_type", "bracket_scope")
        if step_type == "take_all_bracket_contents":
            return ("bracket_type", "bracket_scope", "join", "custom_separator")
        if step_type == "remove_nth_bracket":
            return ("bracket_type", "bracket_scope", "index")
        if step_type == "keep_only_bracket_type":
            return ("bracket_type", "bracket_scope", "join", "custom_separator")
        if step_type == "replace_text":
            return ("old", "new")
        if step_type == "regex_extract":
            return ("pattern", "group")
        if step_type == "loop_lines":
            return ("pattern", "group", "join", "custom_separator", "skip_failed")
        return ()

    def _default_params_for_step_type(self, step_type: str, old_params: dict[str, Any] | None = None) -> dict[str, object]:
        old_params = old_params or {}
        if step_type in self.NO_PARAM_STEP_TYPES:
            return {}
        if step_type in {"take_after_text", "take_before_text", "take_before_last_text", "take_after_last_text", "remove_prefix", "remove_suffix"}:
            return {"value": str(old_params.get("value") or "")}
        if step_type == "take_between_texts":
            return {
                "start": str(old_params.get("start") or ""),
                "end": str(old_params.get("end") or ""),
            }
        if step_type == "take_line":
            return {"index": self._safe_int(old_params.get("index"), 1)}
        if step_type == "take_first_lines":
            return {"count": self._safe_int(old_params.get("count"), 1)}
        if step_type == "remove_last_lines":
            return {"count": self._safe_int(old_params.get("count"), 1)}
        if step_type == "remove_first_lines":
            return {"count": self._safe_int(old_params.get("count"), 1)}
        if step_type == "take_line_range":
            return {
                "start": self._safe_int(old_params.get("start"), 1),
                "end": self._safe_int(old_params.get("end"), 1),
            }
        if step_type in {"take_before_marker", "take_after_marker"}:
            return {
                "value": str(old_params.get("value") or ""),
                "scope": str(old_params.get("scope") or "all"),
                "unit": str(old_params.get("unit") or "line"),
                "count": self._safe_int(old_params.get("count"), 1),
            }
        if step_type == "split_and_take":
            return {
                "separator": str(old_params.get("separator") or ""),
                "index": self._safe_int(old_params.get("index"), 1),
            }
        if step_type == "split_multi_and_take":
            return {
                "separators": str(old_params.get("separators") or "-\n_\n／\n/"),
                "index": self._safe_int(old_params.get("index"), 1),
            }
        if step_type == "split_and_join_range":
            separator = str(old_params.get("separator") or "")
            return {
                "separator": separator,
                "start": self._safe_int(old_params.get("start"), 1),
                "end": self._safe_int(old_params.get("end"), 1),
                "joiner": str(old_params.get("joiner") if old_params.get("joiner") is not None else separator),
            }
        if step_type == "take_bracket_content":
            return {
                "bracket": str(old_params.get("bracket") or "[]"),
                "bracket_scope": str(old_params.get("bracket_scope") or "outer"),
                "index": self._safe_int(old_params.get("index"), 1),
            }
        if step_type == "remove_text":
            return {
                "text": str(old_params.get("text") or old_params.get("value") or ""),
                "case_sensitive": self._safe_bool(old_params.get("case_sensitive"), True),
            }
        if step_type == "remove_regex":
            return {"pattern": str(old_params.get("pattern") or "")}
        if step_type in {"remove_bracket_content", "remove_brackets_keep_content"}:
            return {
                "bracket_type": str(old_params.get("bracket_type") or "all"),
                "bracket_scope": str(old_params.get("bracket_scope") or "outer"),
            }
        if step_type == "take_last_bracket_content":
            return {
                "bracket_type": str(old_params.get("bracket_type") or "all"),
                "bracket_scope": str(old_params.get("bracket_scope") or "outer"),
            }
        if step_type == "take_all_bracket_contents":
            return {
                "bracket_type": str(old_params.get("bracket_type") or "all"),
                "bracket_scope": str(old_params.get("bracket_scope") or "outer"),
                "join": str(old_params.get("join") or "newline"),
                "custom_separator": str(old_params.get("custom_separator") or ""),
            }
        if step_type == "remove_nth_bracket":
            return {
                "bracket_type": str(old_params.get("bracket_type") or "all"),
                "bracket_scope": str(old_params.get("bracket_scope") or "outer"),
                "index": self._safe_int(old_params.get("index"), 1),
            }
        if step_type == "keep_only_bracket_type":
            return {
                "bracket_type": str(old_params.get("bracket_type") or "all"),
                "bracket_scope": str(old_params.get("bracket_scope") or "outer"),
                "join": str(old_params.get("join") or "newline"),
                "custom_separator": str(old_params.get("custom_separator") or ""),
            }
        if step_type == "replace_text":
            return {
                "old": str(old_params.get("old") or ""),
                "new": str(old_params.get("new") or ""),
            }
        if step_type == "regex_extract":
            return {
                "pattern": str(old_params.get("pattern") or ""),
                "group": self._safe_int(old_params.get("group"), 1),
            }
        if step_type == "loop_lines":
            return {
                "pattern": str(old_params.get("pattern") or r"#\[(.+?)\]"),
                "group": self._safe_int(old_params.get("group"), 1),
                "join": str(old_params.get("join") or "newline"),
                "custom_separator": str(old_params.get("custom_separator") or ""),
                "skip_failed": self._safe_bool(old_params.get("skip_failed"), True),
            }
        return {}

    @staticmethod
    def _safe_int(value: object, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_bool(value: object, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "y", "on"}:
                return True
            if normalized in {"0", "false", "no", "n", "off"}:
                return False
        if value is None:
            return default
        return bool(value)

    @classmethod
    def _normalize_preview_result_height(cls, value: object) -> int:
        try:
            height = int(value)
        except (TypeError, ValueError):
            height = cls.PREVIEW_RESULT_HEIGHT_DEFAULT
        return min(cls.PREVIEW_RESULT_HEIGHT_MAX, max(cls.PREVIEW_RESULT_HEIGHT_MIN, height))

    @staticmethod
    def _normalize_dialog_size(value: object) -> tuple[int, int]:
        try:
            width = int(value[0])  # type: ignore[index]
            height = int(value[1])  # type: ignore[index]
        except (TypeError, ValueError, IndexError):
            width, height = 1320, 820
        return (min(1920, max(1100, width)), min(1200, max(700, height)))

    @staticmethod
    def _normalize_rule_presets(value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        presets: list[dict[str, Any]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            preset_id = str(item.get("id") or "").strip()
            kind = str(item.get("kind") or "").strip()
            if not preset_id or kind not in {"rule", "steps"}:
                continue
            steps = []
            for step in item.get("steps") or []:
                if isinstance(step, dict) and str(step.get("type") or "").strip():
                    payload = {str(key): data for key, data in step.items()}
                    payload["type"] = str(payload.get("type") or "").strip()
                    steps.append(payload)
            preset: dict[str, Any] = {
                "id": preset_id,
                "kind": kind,
                "name": str(item.get("name") or "Preset").strip() or "Preset",
                "steps": steps,
            }
            if kind == "rule":
                preset["source"] = str(item.get("source") or "filename").strip() or "filename"
            presets.append(preset)
        return presets

    @staticmethod
    def _field_label(code: str) -> str:
        mapping = {
            "title": tr("text.rules.field.title", "Title"),
            "author": tr("text.rules.field.author", "Author"),
            "series": tr("text.rules.field.series", "Series"),
            "tag": tr("text.rules.field.tag", "Tag"),
        }
        return mapping.get(code, code)

    @staticmethod
    def _source_label(code: str) -> str:
        mapping = {
            "filename": tr("text.rules.source.filename", "File name"),
            "stem": tr("text.rules.source.stem", "Stem (without extension)"),
            "full_path": tr("text.rules.source.full_path", "Full path"),
            "parent_folder": tr("text.rules.source.parent_folder", "Parent folder"),
            "txt_first_line": tr("text.rules.source.txt_first_line", "TXT first line"),
            "txt_head_text": tr("text.rules.source.txt_head_text", "TXT head text"),
        }
        return mapping.get(code, code)

    @staticmethod
    def _preset_kind_label(kind: str) -> str:
        if kind == "steps":
            return tr("text.rules.preset.kind.steps", "Steps only")
        return tr("text.rules.preset.kind.rule", "Full rule")

    @staticmethod
    def _format_preset_label(preset: dict[str, Any]) -> str:
        return tr("text.rules.preset.item", "{name} ({kind})").format(
            name=str(preset.get("name") or "Preset"),
            kind=TextRuleDialog._preset_kind_label(str(preset.get("kind") or "rule")),
        )

    @classmethod
    def _step_codes_for_category(cls, category: str) -> tuple[str, ...]:
        for code, steps in cls.STEP_CATEGORIES:
            if code == category:
                return steps
        return cls.STEP_CATEGORIES[0][1]

    @classmethod
    def _category_for_step_type(cls, step_type: str) -> str:
        for category, steps in cls.STEP_CATEGORIES:
            if step_type in steps:
                return category
        return cls.STEP_CATEGORIES[0][0]

    @staticmethod
    def _step_category_options() -> tuple[tuple[str, str], ...]:
        return (
            ("clean", tr("text.rules.category.clean", "Text cleanup")),
            ("delete", tr("text.rules.category.delete", "Text delete")),
            ("extract", tr("text.rules.category.extract", "Text extract")),
            ("line", tr("text.rules.category.line", "Line processing")),
            ("bracket", tr("text.rules.category.bracket", "Bracket processing")),
            ("split", tr("text.rules.category.split", "Split processing")),
            ("filename", tr("text.rules.category.filename", "File name")),
            ("regex", tr("text.rules.category.regex", "Advanced regex")),
        )

    @staticmethod
    def _step_type_label(code: str) -> str:
        mapping = {
            "trim": tr("text.rules.step.trim", "Trim"),
            "normalize_spaces": tr("text.rules.step.normalize_spaces", "Normalize spaces"),
            "remove_all_spaces": tr("text.rules.step.remove_all_spaces", "Remove all spaces"),
            "normalize_punctuation": tr("text.rules.step.normalize_punctuation", "Normalize punctuation"),
            "remove_extension": tr("text.rules.step.remove_extension", "Remove extension"),
            "take_bracket_content": tr("text.rules.step.take_bracket_content", "Take bracket content"),
            "take_after_text": tr("text.rules.step.take_after_text", "Take after text"),
            "take_before_text": tr("text.rules.step.take_before_text", "Take before text"),
            "take_before_last_text": tr("text.rules.step.take_before_last_text", "Take before last text"),
            "take_after_last_text": tr("text.rules.step.take_after_last_text", "Take after last text"),
            "take_between_texts": tr("text.rules.step.take_between_texts", "Take between texts"),
            "take_line": tr("text.rules.step.take_line", "Take line N"),
            "take_first_lines": tr("text.rules.step.take_first_lines", "Take first N lines"),
            "remove_last_lines": tr("text.rules.step.remove_last_lines", "Remove last N lines"),
            "remove_first_lines": tr("text.rules.step.remove_first_lines", "Remove first N lines"),
            "take_line_range": tr("text.rules.step.take_line_range", "Take line N-M"),
            "take_before_marker": tr("text.rules.step.take_before_marker", "Take before marker"),
            "take_after_marker": tr("text.rules.step.take_after_marker", "Take after marker"),
            "split_and_take": tr("text.rules.step.split_and_take", "Split and take"),
            "split_multi_and_take": tr("text.rules.step.split_multi_and_take", "Split by multiple separators and take"),
            "split_and_join_range": tr("text.rules.step.split_and_join_range", "Split and join range"),
            "remove_prefix": tr("text.rules.step.remove_prefix", "Remove prefix"),
            "remove_suffix": tr("text.rules.step.remove_suffix", "Remove suffix"),
            "remove_text": tr("text.rules.step.remove_text", "Remove text"),
            "remove_regex": tr("text.rules.step.remove_regex", "Remove regex"),
            "remove_bracket_content": tr("text.rules.step.remove_bracket_content", "Remove bracket content"),
            "remove_brackets_keep_content": tr("text.rules.step.remove_brackets_keep_content", "Remove brackets keep content"),
            "take_last_bracket_content": tr("text.rules.step.take_last_bracket_content", "Take last bracket content"),
            "take_all_bracket_contents": tr("text.rules.step.take_all_bracket_contents", "Take all bracket contents"),
            "remove_nth_bracket": tr("text.rules.step.remove_nth_bracket", "Remove Nth bracket block"),
            "keep_only_bracket_type": tr("text.rules.step.keep_only_bracket_type", "Keep only bracket type"),
            "replace_text": tr("text.rules.step.replace_text", "Replace text"),
            "regex_extract": tr("text.rules.step.regex_extract", "Regex extract"),
            "loop_lines": tr("text.rules.step.loop_lines", "Loop lines extract"),
        }
        return mapping.get(code, code)

    @staticmethod
    def _param_label(code: str) -> str:
        mapping = {
            "category": tr("text.rules.param.category", "Category"),
            "text": tr("text.rules.param.text", "Text"),
            "value": tr("text.rules.param.value", "Value"),
            "start": tr("text.rules.param.start", "Start"),
            "end": tr("text.rules.param.end", "End"),
            "separator": tr("text.rules.param.separator", "Separator"),
            "separators": tr("text.rules.param.separators", "Separators"),
            "joiner": tr("text.rules.param.joiner", "Joiner"),
            "bracket": tr("text.rules.param.bracket", "Bracket"),
            "bracket_type": tr("text.rules.param.bracket_type", "Bracket type"),
            "bracket_scope": tr("text.rules.param.bracket_scope", "Nested scope"),
            "index": tr("text.rules.param.index", "Index"),
            "count": tr("text.rules.param.count", "Count"),
            "scope": tr("text.rules.param.scope", "Range"),
            "unit": tr("text.rules.param.unit", "Unit"),
            "group": tr("text.rules.param.group", "Group"),
            "old": tr("text.rules.param.old", "Old"),
            "new": tr("text.rules.param.new", "New"),
            "pattern": tr("text.rules.param.pattern", "Pattern"),
            "join": tr("text.rules.param.join", "Join"),
            "custom_separator": tr("text.rules.param.custom_separator", "Custom separator"),
            "skip_failed": tr("text.rules.param.skip_failed", "Skip unmatched lines"),
            "case_sensitive": tr("text.rules.param.case_sensitive", "Case sensitive"),
        }
        return mapping.get(code, code)

    @staticmethod
    def _param_label_for_step(step_type: str, code: str) -> str:
        if step_type == "take_line_range" and code == "start":
            return tr("text.rules.param.start_line", "Start line")
        if step_type == "take_line_range" and code == "end":
            return tr("text.rules.param.end_line", "End line")
        if step_type == "split_and_join_range" and code == "start":
            return tr("text.rules.param.start_part", "Start part")
        if step_type == "split_and_join_range" and code == "end":
            return tr("text.rules.param.end_part", "End part")
        return TextRuleDialog._param_label(code)

    @staticmethod
    def _scope_options() -> tuple[tuple[str, str], ...]:
        return (
            ("all", tr("text.rules.option.scope.all", "All")),
            ("count", tr("text.rules.option.scope.count", "Count")),
        )

    @staticmethod
    def _bracket_scope_options() -> tuple[tuple[str, str], ...]:
        return (
            ("outer", tr("text.rules.option.bracket_scope.outer", "Outer blocks")),
            ("all", tr("text.rules.option.bracket_scope.all", "All blocks")),
            ("inner", tr("text.rules.option.bracket_scope.inner", "Inner blocks")),
        )

    @staticmethod
    def _unit_options() -> tuple[tuple[str, str], ...]:
        return (
            ("line", tr("text.rules.option.unit.line", "Lines")),
            ("char", tr("text.rules.option.unit.char", "Characters")),
        )

    @staticmethod
    def _join_options() -> tuple[tuple[str, str], ...]:
        return (
            ("newline", tr("text.rules.option.join.newline", "New line")),
            ("comma", tr("text.rules.option.join.comma", "Comma")),
            ("semicolon", tr("text.rules.option.join.semicolon", "Semicolon")),
            ("custom", tr("text.rules.option.join.custom", "Custom")),
        )

    @staticmethod
    def _skip_failed_options() -> tuple[tuple[bool, str], ...]:
        return (
            (True, tr("text.rules.option.skip_failed.true", "Skip unmatched lines")),
            (False, tr("text.rules.option.skip_failed.false", "Fail on unmatched line")),
        )

    @staticmethod
    def _case_sensitive_options() -> tuple[tuple[bool, str], ...]:
        return (
            (True, tr("text.rules.option.case_sensitive.true", "Case sensitive")),
            (False, tr("text.rules.option.case_sensitive.false", "Ignore case")),
        )

    @staticmethod
    def _bracket_type_options() -> tuple[tuple[str, str], ...]:
        return (
            ("all", tr("text.rules.option.bracket_type.all", "All brackets")),
            ("square", tr("text.rules.option.bracket_type.square", "Square brackets")),
            ("round", tr("text.rules.option.bracket_type.round", "Round brackets")),
            ("chinese_square", tr("text.rules.option.bracket_type.chinese_square", "Chinese square brackets")),
            ("corner", tr("text.rules.option.bracket_type.corner", "Corner brackets")),
            ("book_title", tr("text.rules.option.bracket_type.book_title", "Book title brackets")),
            ("angle", tr("text.rules.option.bracket_type.angle", "Angle brackets")),
        )
