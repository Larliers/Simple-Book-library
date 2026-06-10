from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
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
from bookhub.ui.dialogs.text_rule_help_dialog import TextRuleHelpDialog


class TextRuleDialog(QDialog):
    FIELDS = ("title", "author", "series", "tag")
    SOURCE_CODES = ("filename", "stem", "full_path", "parent_folder", "txt_first_line", "txt_head_text")
    STEP_TYPE_CODES = (
        "trim",
        "remove_extension",
        "take_bracket_content",
        "take_after_text",
        "take_before_text",
        "take_between_texts",
        "split_and_take",
        "remove_prefix",
        "remove_suffix",
        "replace_text",
        "regex_extract",
    )
    NO_PARAM_STEP_TYPES = {"trim", "remove_extension"}

    def __init__(
        self,
        root_path: str,
        rules_json: str,
        parent=None,
        preview_chars: int = DEFAULT_TEXT_PREVIEW_CHARS,
    ) -> None:
        super().__init__(parent)
        self._root_path = root_path
        self._preview_chars = max(100, int(preview_chars or DEFAULT_TEXT_PREVIEW_CHARS))
        self._current_field_code = "title"
        self._rules_by_field: dict[str, list[ImportRule]] = {field: [] for field in self.FIELDS}
        self._field_buttons: dict[str, QPushButton] = {}
        self._rendering_steps = False
        self._suppress_source_update = False
        self._visible_step_param_keys: dict[int, tuple[str, ...]] = {}
        self._load_rules(rules_json)

        self.setWindowTitle(tr("text.rules.title", "Text Rules"))
        self.resize(1320, 820)

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
        template_layout = QHBoxLayout(template_box)
        template_layout.setContentsMargins(8, 8, 8, 8)
        template_layout.setSpacing(8)
        template_layout.addWidget(QLabel(tr("text.rules.templates.title", "Template Rules")))
        self.template_title_btn = QPushButton(tr("text.rules.template.title_line", "Title from first line"))
        self.template_title_btn.clicked.connect(self._insert_template_title_rule)
        template_layout.addWidget(self.template_title_btn)
        self.template_author_btn = QPushButton(tr("text.rules.template.author_bracket", "Author from bracket"))
        self.template_author_btn.clicked.connect(self._insert_template_author_rule)
        template_layout.addWidget(self.template_author_btn)
        self.template_fallback_btn = QPushButton(tr("text.rules.template.fallback_stem", "Fallback from stem"))
        self.template_fallback_btn.clicked.connect(self._insert_template_fallback_rule)
        template_layout.addWidget(self.template_fallback_btn)
        template_layout.addStretch(1)
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
        preview_layout.addLayout(preview_form)

        self.preview_result_box = QFrame()
        self.preview_result_box.setObjectName("TextRulePreviewResult")
        result_layout = QVBoxLayout(self.preview_result_box)
        result_layout.setContentsMargins(10, 8, 10, 8)
        result_layout.setSpacing(4)
        self.preview_result_title = QLabel()
        self.preview_result_title.setObjectName("PageSubtitle")
        self.preview_result_label = QLabel()
        self.preview_result_label.setWordWrap(True)
        self.preview_result_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        result_layout.addWidget(self.preview_result_title)
        result_layout.addWidget(self.preview_result_label)
        preview_layout.addWidget(self.preview_result_box)
        preview_layout.addStretch(1)

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
        type_combo = QComboBox()
        for code in self.STEP_TYPE_CODES:
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
        label = self._param_label(key)
        if key == "bracket":
            widget = QComboBox()
            widget.addItems(["[]", "【】", "()", "（）", "<>", "《》"])
            value = str(step.params.get("bracket") or "[]")
            value_idx = widget.findText(value)
            widget.setCurrentIndex(value_idx if value_idx >= 0 else 0)
            widget.currentTextChanged.connect(lambda text, idx=step_index: self._set_step_param(idx, "bracket", text))
            form.addRow(label, widget)
            return

        if key in {"index", "group"}:
            widget = QSpinBox()
            widget.setRange(0 if key == "group" else 1, 999)
            widget.setValue(self._safe_int(step.params.get(key), 1))
            widget.valueChanged.connect(lambda value, idx=step_index, param=key: self._set_step_param(idx, param, value))
            form.addRow(label, widget)
            return

        widget = QLineEdit()
        widget.setText(str(step.params.get(key) or ""))
        widget.textChanged.connect(lambda text, idx=step_index, param=key: self._set_step_param(idx, param, text))
        form.addRow(label, widget)

    def _selected_steps(self) -> list[RuleStep]:
        rule_idx = self.rule_list.currentRow()
        rules = self._current_rules()
        if rule_idx < 0 or rule_idx >= len(rules):
            return []
        return rules[rule_idx].steps

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

    def _open_help_dialog(self) -> None:
        dialog = TextRuleHelpDialog(self)
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
            self._set_preview_result(
                "success",
                tr("text.rules.preview.status.success", "Matched"),
                tr("text.rules.preview.success", "{field}: {value}").format(
                    field=self._field_label(self._current_field()),
                    value=result.value,
                ),
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
        self.preview_result_label.setText(message)
        self.preview_result_box.style().unpolish(self.preview_result_box)
        self.preview_result_box.style().polish(self.preview_result_box)

    def _param_keys_for_step_type(self, step_type: str) -> tuple[str, ...]:
        if step_type in self.NO_PARAM_STEP_TYPES:
            return ()
        if step_type in {"take_after_text", "take_before_text", "remove_prefix", "remove_suffix"}:
            return ("value",)
        if step_type == "take_between_texts":
            return ("start", "end")
        if step_type == "split_and_take":
            return ("separator", "index")
        if step_type == "take_bracket_content":
            return ("bracket", "index")
        if step_type == "replace_text":
            return ("old", "new")
        if step_type == "regex_extract":
            return ("pattern", "group")
        return ()

    def _default_params_for_step_type(self, step_type: str, old_params: dict[str, Any] | None = None) -> dict[str, object]:
        old_params = old_params or {}
        if step_type in self.NO_PARAM_STEP_TYPES:
            return {}
        if step_type in {"take_after_text", "take_before_text", "remove_prefix", "remove_suffix"}:
            return {"value": str(old_params.get("value") or "")}
        if step_type == "take_between_texts":
            return {
                "start": str(old_params.get("start") or ""),
                "end": str(old_params.get("end") or ""),
            }
        if step_type == "split_and_take":
            return {
                "separator": str(old_params.get("separator") or ""),
                "index": self._safe_int(old_params.get("index"), 1),
            }
        if step_type == "take_bracket_content":
            return {
                "bracket": str(old_params.get("bracket") or "[]"),
                "index": self._safe_int(old_params.get("index"), 1),
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
        return {}

    @staticmethod
    def _safe_int(value: object, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

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
    def _step_type_label(code: str) -> str:
        mapping = {
            "trim": tr("text.rules.step.trim", "Trim"),
            "remove_extension": tr("text.rules.step.remove_extension", "Remove extension"),
            "take_bracket_content": tr("text.rules.step.take_bracket_content", "Take bracket content"),
            "take_after_text": tr("text.rules.step.take_after_text", "Take after text"),
            "take_before_text": tr("text.rules.step.take_before_text", "Take before text"),
            "take_between_texts": tr("text.rules.step.take_between_texts", "Take between texts"),
            "split_and_take": tr("text.rules.step.split_and_take", "Split and take"),
            "remove_prefix": tr("text.rules.step.remove_prefix", "Remove prefix"),
            "remove_suffix": tr("text.rules.step.remove_suffix", "Remove suffix"),
            "replace_text": tr("text.rules.step.replace_text", "Replace text"),
            "regex_extract": tr("text.rules.step.regex_extract", "Regex extract"),
        }
        return mapping.get(code, code)

    @staticmethod
    def _param_label(code: str) -> str:
        mapping = {
            "value": tr("text.rules.param.value", "Value"),
            "start": tr("text.rules.param.start", "Start"),
            "end": tr("text.rules.param.end", "End"),
            "separator": tr("text.rules.param.separator", "Separator"),
            "bracket": tr("text.rules.param.bracket", "Bracket"),
            "index": tr("text.rules.param.index", "Index"),
            "group": tr("text.rules.param.group", "Group"),
            "old": tr("text.rules.param.old", "Old"),
            "new": tr("text.rules.param.new", "New"),
            "pattern": tr("text.rules.param.pattern", "Pattern"),
        }
        return mapping.get(code, code)
