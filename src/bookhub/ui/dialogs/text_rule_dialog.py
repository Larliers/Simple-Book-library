from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from bookhub.i18n import tr
from bookhub.library.text_rules import ImportRule, RuleStep, dump_rules_to_json, load_rules_from_json
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

    def __init__(self, root_path: str, rules_json: str, parent=None) -> None:
        super().__init__(parent)
        self._root_path = root_path
        self._rules_by_field: dict[str, list[ImportRule]] = {field: [] for field in self.FIELDS}
        self._load_rules(rules_json)

        self.setWindowTitle(tr("text.rules.title", "Text Rules"))
        self.resize(1100, 700)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        root_label = QLabel(tr("text.rules.root", "Path: {path}").format(path=root_path))
        root_label.setObjectName("PageSubtitle")
        root.addWidget(root_label)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel(tr("text.rules.field", "Field")))
        self.field_combo = QComboBox()
        for code in self.FIELDS:
            self.field_combo.addItem(self._field_label(code), code)
        self.field_combo.currentIndexChanged.connect(self._refresh_rule_list)
        top_row.addWidget(self.field_combo)
        self.help_btn = QPushButton(tr("text.rules.help.button", "Usage Guide"))
        self.help_btn.setObjectName("GhostButton")
        self.help_btn.clicked.connect(self._open_help_dialog)
        top_row.addWidget(self.help_btn)
        top_row.addStretch(1)
        root.addLayout(top_row)

        guide_box = QFrame()
        guide_box.setObjectName("PageSection")
        guide_layout = QVBoxLayout(guide_box)
        guide_layout.setContentsMargins(10, 10, 10, 10)
        guide_layout.setSpacing(6)
        guide_title = QLabel(tr("text.rules.guide.title", "Quick Guide"))
        guide_title.setObjectName("PageSubtitle")
        guide_layout.addWidget(guide_title)
        guide_content = QLabel(
            "\n".join(
                [
                    tr("text.rules.guide.step1", "1. Pick field and source for the target value."),
                    tr("text.rules.guide.step2", "2. Add rule, then add steps from top to bottom."),
                    tr("text.rules.guide.step3", "3. Save rules and rescan Text Novel folders."),
                ]
            )
        )
        guide_content.setWordWrap(True)
        guide_layout.addWidget(guide_content)

        template_row = QHBoxLayout()
        template_row.addWidget(QLabel(tr("text.rules.templates.title", "Template Rules")))
        self.template_title_btn = QPushButton(tr("text.rules.template.title_line", "Title from first line"))
        self.template_title_btn.clicked.connect(self._insert_template_title_rule)
        template_row.addWidget(self.template_title_btn)
        self.template_author_btn = QPushButton(tr("text.rules.template.author_bracket", "Author from bracket"))
        self.template_author_btn.clicked.connect(self._insert_template_author_rule)
        template_row.addWidget(self.template_author_btn)
        self.template_fallback_btn = QPushButton(tr("text.rules.template.fallback_stem", "Fallback from stem"))
        self.template_fallback_btn.clicked.connect(self._insert_template_fallback_rule)
        template_row.addWidget(self.template_fallback_btn)
        template_row.addStretch(1)
        guide_layout.addLayout(template_row)
        root.addWidget(guide_box)

        content = QHBoxLayout()
        content.setSpacing(12)
        root.addLayout(content, 1)

        rule_col = QVBoxLayout()
        content.addLayout(rule_col, 1)
        rule_col.addWidget(QLabel(tr("text.rules.rule_chain", "Rule Chain")))
        self.rule_list = QListWidget()
        self.rule_list.currentRowChanged.connect(self._load_selected_rule)
        rule_col.addWidget(self.rule_list, 1)

        rule_actions = QHBoxLayout()
        self.add_rule_btn = QPushButton(tr("text.rules.add_rule", "Add Rule"))
        self.add_rule_btn.clicked.connect(self._add_rule)
        self.update_rule_btn = QPushButton(tr("text.rules.update_rule", "Update Rule"))
        self.update_rule_btn.clicked.connect(self._update_rule)
        self.delete_rule_btn = QPushButton(tr("text.rules.delete_rule", "Delete Rule"))
        self.delete_rule_btn.clicked.connect(self._delete_rule)
        rule_actions.addWidget(self.add_rule_btn)
        rule_actions.addWidget(self.update_rule_btn)
        rule_actions.addWidget(self.delete_rule_btn)
        rule_col.addLayout(rule_actions)

        editor_col = QVBoxLayout()
        content.addLayout(editor_col, 2)

        rule_form = QFormLayout()
        self.source_combo = QComboBox()
        for code in self.SOURCE_CODES:
            self.source_combo.addItem(self._source_label(code), code)
        rule_form.addRow(tr("text.rules.source", "Source"), self.source_combo)
        editor_col.addLayout(rule_form)

        editor_col.addWidget(QLabel(tr("text.rules.steps", "Steps")))
        self.step_list = QListWidget()
        self.step_list.currentRowChanged.connect(self._load_selected_step)
        editor_col.addWidget(self.step_list, 1)

        step_form_wrap = QWidget()
        step_form = QGridLayout(step_form_wrap)
        step_form.setContentsMargins(0, 0, 0, 0)
        step_form.setHorizontalSpacing(8)
        step_form.setVerticalSpacing(6)

        self.step_type_combo = QComboBox()
        for code in self.STEP_TYPE_CODES:
            self.step_type_combo.addItem(self._step_type_label(code), code)

        self.bracket_combo = QComboBox()
        self.bracket_combo.addItems(["[]", "【】", "()", "（）", "<>", "《》"])

        self.value_combo = QComboBox()
        self.value_combo.setEditable(True)
        self.start_combo = QComboBox()
        self.start_combo.setEditable(True)
        self.end_combo = QComboBox()
        self.end_combo.setEditable(True)
        self.sep_combo = QComboBox()
        self.sep_combo.setEditable(True)
        self.old_combo = QComboBox()
        self.old_combo.setEditable(True)
        self.new_combo = QComboBox()
        self.new_combo.setEditable(True)
        self.pattern_combo = QComboBox()
        self.pattern_combo.setEditable(True)

        self.index_spin = QSpinBox()
        self.index_spin.setRange(1, 999)
        self.index_spin.setValue(1)
        self.group_spin = QSpinBox()
        self.group_spin.setRange(0, 999)
        self.group_spin.setValue(1)

        row = 0
        step_form.addWidget(QLabel(tr("text.rules.param.type", "Type")), row, 0)
        step_form.addWidget(self.step_type_combo, row, 1)
        step_form.addWidget(QLabel(tr("text.rules.param.value", "Value")), row, 2)
        step_form.addWidget(self.value_combo, row, 3)
        row += 1
        step_form.addWidget(QLabel(tr("text.rules.param.start", "Start")), row, 0)
        step_form.addWidget(self.start_combo, row, 1)
        step_form.addWidget(QLabel(tr("text.rules.param.end", "End")), row, 2)
        step_form.addWidget(self.end_combo, row, 3)
        row += 1
        step_form.addWidget(QLabel(tr("text.rules.param.separator", "Separator")), row, 0)
        step_form.addWidget(self.sep_combo, row, 1)
        step_form.addWidget(QLabel(tr("text.rules.param.bracket", "Bracket")), row, 2)
        step_form.addWidget(self.bracket_combo, row, 3)
        row += 1
        step_form.addWidget(QLabel(tr("text.rules.param.index", "Index")), row, 0)
        step_form.addWidget(self.index_spin, row, 1)
        step_form.addWidget(QLabel(tr("text.rules.param.group", "Group")), row, 2)
        step_form.addWidget(self.group_spin, row, 3)
        row += 1
        step_form.addWidget(QLabel(tr("text.rules.param.old", "Old")), row, 0)
        step_form.addWidget(self.old_combo, row, 1)
        step_form.addWidget(QLabel(tr("text.rules.param.new", "New")), row, 2)
        step_form.addWidget(self.new_combo, row, 3)
        row += 1
        step_form.addWidget(QLabel(tr("text.rules.param.pattern", "Pattern")), row, 0)
        step_form.addWidget(self.pattern_combo, row, 1, 1, 3)

        editor_col.addWidget(step_form_wrap)

        step_actions = QHBoxLayout()
        self.add_step_btn = QPushButton(tr("text.rules.add_step", "Add Step"))
        self.add_step_btn.clicked.connect(self._add_step)
        self.update_step_btn = QPushButton(tr("text.rules.update_step", "Update Step"))
        self.update_step_btn.clicked.connect(self._update_step)
        self.delete_step_btn = QPushButton(tr("text.rules.delete_step", "Delete Step"))
        self.delete_step_btn.clicked.connect(self._delete_step)
        self.move_step_up_btn = QPushButton(tr("text.rules.step_up", "Step Up"))
        self.move_step_up_btn.clicked.connect(lambda: self._move_step(-1))
        self.move_step_down_btn = QPushButton(tr("text.rules.step_down", "Step Down"))
        self.move_step_down_btn.clicked.connect(lambda: self._move_step(1))
        step_actions.addWidget(self.add_step_btn)
        step_actions.addWidget(self.update_step_btn)
        step_actions.addWidget(self.delete_step_btn)
        step_actions.addWidget(self.move_step_up_btn)
        step_actions.addWidget(self.move_step_down_btn)
        editor_col.addLayout(step_actions)

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

        self._refresh_rule_list()

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
        return str(self.field_combo.currentData() or "title")

    def _current_rules(self) -> list[ImportRule]:
        return self._rules_by_field[self._current_field()]

    def _refresh_rule_list(self) -> None:
        self.rule_list.clear()
        for idx, rule in enumerate(self._current_rules(), start=1):
            label = tr("text.rules.rule_item", "{index}. Source: {source} · Steps: {count}").format(
                index=idx,
                source=self._source_label(rule.source),
                count=len(rule.steps),
            )
            self.rule_list.addItem(QListWidgetItem(label))
        if self.rule_list.count() > 0:
            self.rule_list.setCurrentRow(0)
        else:
            self.step_list.clear()

    def _load_selected_rule(self) -> None:
        idx = self.rule_list.currentRow()
        rules = self._current_rules()
        if idx < 0 or idx >= len(rules):
            return
        rule = rules[idx]
        source_idx = self.source_combo.findData(rule.source)
        if source_idx >= 0:
            self.source_combo.setCurrentIndex(source_idx)
        self._render_steps(rule.steps)

    def _render_steps(self, steps: list[RuleStep]) -> None:
        self.step_list.clear()
        for idx, step in enumerate(steps, start=1):
            self.step_list.addItem(
                QListWidgetItem(
                    tr("text.rules.step_item", "{index}. {step}").format(index=idx, step=self._format_step_label(step))
                )
            )
        if self.step_list.count() > 0:
            self.step_list.setCurrentRow(0)

    def _format_step_label(self, step: RuleStep) -> str:
        step_name = self._step_type_label(step.type)
        if not step.params:
            return step_name
        details = ", ".join(f"{self._param_label(k)}={v}" for k, v in step.params.items())
        return f"{step_name} ({details})"

    def _load_selected_step(self) -> None:
        rule_idx = self.rule_list.currentRow()
        step_idx = self.step_list.currentRow()
        rules = self._current_rules()
        if rule_idx < 0 or rule_idx >= len(rules):
            return
        steps = rules[rule_idx].steps
        if step_idx < 0 or step_idx >= len(steps):
            return
        step = steps[step_idx]
        type_idx = self.step_type_combo.findData(step.type)
        if type_idx >= 0:
            self.step_type_combo.setCurrentIndex(type_idx)

        self.value_combo.setCurrentText(str(step.params.get("value") or ""))
        self.start_combo.setCurrentText(str(step.params.get("start") or ""))
        self.end_combo.setCurrentText(str(step.params.get("end") or ""))
        self.sep_combo.setCurrentText(str(step.params.get("separator") or ""))
        self.old_combo.setCurrentText(str(step.params.get("old") or ""))
        self.new_combo.setCurrentText(str(step.params.get("new") or ""))
        self.pattern_combo.setCurrentText(str(step.params.get("pattern") or ""))

        bracket = str(step.params.get("bracket") or "[]")
        bracket_idx = self.bracket_combo.findText(bracket)
        if bracket_idx >= 0:
            self.bracket_combo.setCurrentIndex(bracket_idx)
        self.index_spin.setValue(int(step.params.get("index") or 1))
        self.group_spin.setValue(int(step.params.get("group") or 1))

    def _collect_step_params(self, step_type: str) -> dict[str, object]:
        if step_type in {"trim", "remove_extension"}:
            return {}
        if step_type in {"take_after_text", "take_before_text", "remove_prefix", "remove_suffix"}:
            return {"value": self.value_combo.currentText()}
        if step_type == "take_between_texts":
            return {"start": self.start_combo.currentText(), "end": self.end_combo.currentText()}
        if step_type == "split_and_take":
            return {"separator": self.sep_combo.currentText(), "index": self.index_spin.value()}
        if step_type == "take_bracket_content":
            return {"bracket": self.bracket_combo.currentText(), "index": self.index_spin.value()}
        if step_type == "replace_text":
            return {"old": self.old_combo.currentText(), "new": self.new_combo.currentText()}
        if step_type == "regex_extract":
            return {"pattern": self.pattern_combo.currentText(), "group": self.group_spin.value()}
        return {}

    def _build_step_from_form(self) -> RuleStep:
        step_type = str(self.step_type_combo.currentData() or "trim")
        params = self._collect_step_params(step_type)
        return RuleStep(type=step_type, params=params)

    def _add_step(self) -> None:
        idx = self.rule_list.currentRow()
        rules = self._current_rules()
        if idx < 0 or idx >= len(rules):
            QMessageBox.warning(
                self,
                tr("text.rules.need_rule", "No rule selected"),
                tr("text.rules.need_rule_msg", "Please add/select a rule first."),
            )
            return
        step = self._build_step_from_form()
        rules[idx].steps.append(step)
        self._render_steps(rules[idx].steps)
        self._refresh_rule_list()
        self.rule_list.setCurrentRow(idx)

    def _update_step(self) -> None:
        rule_idx = self.rule_list.currentRow()
        step_idx = self.step_list.currentRow()
        rules = self._current_rules()
        if rule_idx < 0 or rule_idx >= len(rules):
            return
        if step_idx < 0 or step_idx >= len(rules[rule_idx].steps):
            return
        rules[rule_idx].steps[step_idx] = self._build_step_from_form()
        self._render_steps(rules[rule_idx].steps)
        self.step_list.setCurrentRow(step_idx)
        self._refresh_rule_list()
        self.rule_list.setCurrentRow(rule_idx)

    def _delete_step(self) -> None:
        rule_idx = self.rule_list.currentRow()
        step_idx = self.step_list.currentRow()
        rules = self._current_rules()
        if rule_idx < 0 or rule_idx >= len(rules):
            return
        if step_idx < 0 or step_idx >= len(rules[rule_idx].steps):
            return
        del rules[rule_idx].steps[step_idx]
        self._render_steps(rules[rule_idx].steps)
        self._refresh_rule_list()
        self.rule_list.setCurrentRow(rule_idx)

    def _move_step(self, offset: int) -> None:
        rule_idx = self.rule_list.currentRow()
        step_idx = self.step_list.currentRow()
        rules = self._current_rules()
        if rule_idx < 0 or rule_idx >= len(rules):
            return
        steps = rules[rule_idx].steps
        if step_idx < 0 or step_idx >= len(steps):
            return
        target = step_idx + offset
        if target < 0 or target >= len(steps):
            return
        steps[step_idx], steps[target] = steps[target], steps[step_idx]
        self._render_steps(steps)
        self.step_list.setCurrentRow(target)
        self._refresh_rule_list()
        self.rule_list.setCurrentRow(rule_idx)

    def _build_rule_from_form(self) -> ImportRule:
        source = str(self.source_combo.currentData() or "filename")
        return ImportRule(field=self._current_field(), source=source, steps=[])

    def _add_rule(self) -> None:
        rules = self._current_rules()
        rule = self._build_rule_from_form()
        rules.append(rule)
        self._refresh_rule_list()
        self.rule_list.setCurrentRow(len(rules) - 1)

    def _update_rule(self) -> None:
        idx = self.rule_list.currentRow()
        rules = self._current_rules()
        if idx < 0 or idx >= len(rules):
            return
        rules[idx].source = str(self.source_combo.currentData() or "filename")
        self._refresh_rule_list()
        self.rule_list.setCurrentRow(idx)

    def _delete_rule(self) -> None:
        idx = self.rule_list.currentRow()
        rules = self._current_rules()
        if idx < 0 or idx >= len(rules):
            return
        del rules[idx]
        self._refresh_rule_list()

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
        self._refresh_rule_list()
        self.rule_list.setCurrentRow(self.rule_list.count() - 1)

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
        self._refresh_rule_list()
        self.rule_list.setCurrentRow(self.rule_list.count() - 1)

    def _insert_template_fallback_rule(self) -> None:
        self._current_rules().append(
            ImportRule(
                field=self._current_field(),
                source="stem",
                steps=[RuleStep(type="trim", params={})],
            )
        )
        self._refresh_rule_list()
        self.rule_list.setCurrentRow(self.rule_list.count() - 1)

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
