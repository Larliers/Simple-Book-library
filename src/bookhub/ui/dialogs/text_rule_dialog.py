from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
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


class TextRuleDialog(QDialog):
    FIELDS = ("title", "author", "series", "tag")

    def __init__(self, root_path: str, rules_json: str, parent=None) -> None:
        super().__init__(parent)
        self._root_path = root_path
        self._rules_by_field: dict[str, list[ImportRule]] = {field: [] for field in self.FIELDS}
        self._load_rules(rules_json)

        self.setWindowTitle(tr("text.rules.title", "Text Rules"))
        self.resize(980, 620)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        root_label = QLabel(tr("text.rules.root", "Path: {path}").format(path=root_path))
        root_label.setObjectName("PageSubtitle")
        root.addWidget(root_label)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel(tr("text.rules.field", "Field")))
        self.field_combo = QComboBox()
        self.field_combo.addItems(list(self.FIELDS))
        self.field_combo.currentIndexChanged.connect(self._refresh_rule_list)
        top_row.addWidget(self.field_combo)
        top_row.addStretch(1)
        root.addLayout(top_row)

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
        self.source_combo.addItems(
            ["filename", "stem", "full_path", "parent_folder", "txt_first_line", "txt_head_text"]
        )
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
        self.step_type_combo.addItems(
            [
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
            ]
        )
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
        step_form.addWidget(QLabel("type"), row, 0)
        step_form.addWidget(self.step_type_combo, row, 1)
        step_form.addWidget(QLabel("value"), row, 2)
        step_form.addWidget(self.value_combo, row, 3)
        row += 1
        step_form.addWidget(QLabel("start"), row, 0)
        step_form.addWidget(self.start_combo, row, 1)
        step_form.addWidget(QLabel("end"), row, 2)
        step_form.addWidget(self.end_combo, row, 3)
        row += 1
        step_form.addWidget(QLabel("separator"), row, 0)
        step_form.addWidget(self.sep_combo, row, 1)
        step_form.addWidget(QLabel("bracket"), row, 2)
        step_form.addWidget(self.bracket_combo, row, 3)
        row += 1
        step_form.addWidget(QLabel("index"), row, 0)
        step_form.addWidget(self.index_spin, row, 1)
        step_form.addWidget(QLabel("group"), row, 2)
        step_form.addWidget(self.group_spin, row, 3)
        row += 1
        step_form.addWidget(QLabel("old"), row, 0)
        step_form.addWidget(self.old_combo, row, 1)
        step_form.addWidget(QLabel("new"), row, 2)
        step_form.addWidget(self.new_combo, row, 3)
        row += 1
        step_form.addWidget(QLabel("pattern"), row, 0)
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
        return str(self.field_combo.currentText())

    def _current_rules(self) -> list[ImportRule]:
        return self._rules_by_field[self._current_field()]

    def _refresh_rule_list(self) -> None:
        self.rule_list.clear()
        for idx, rule in enumerate(self._current_rules(), start=1):
            label = f"{idx}. source={rule.source} steps={len(rule.steps)}"
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
        source_idx = self.source_combo.findText(rule.source)
        if source_idx >= 0:
            self.source_combo.setCurrentIndex(source_idx)
        self._render_steps(rule.steps)

    def _render_steps(self, steps: list[RuleStep]) -> None:
        self.step_list.clear()
        for idx, step in enumerate(steps, start=1):
            self.step_list.addItem(QListWidgetItem(f"{idx}. {self._step_label(step)}"))
        if self.step_list.count() > 0:
            self.step_list.setCurrentRow(0)

    @staticmethod
    def _step_label(step: RuleStep) -> str:
        params = step.params
        if not params:
            return step.type
        details = ", ".join(f"{k}={v}" for k, v in params.items())
        return f"{step.type} ({details})"

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
        type_idx = self.step_type_combo.findText(step.type)
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
        step_type = self.step_type_combo.currentText()
        params = self._collect_step_params(step_type)
        return RuleStep(type=step_type, params=params)

    def _add_step(self) -> None:
        idx = self.rule_list.currentRow()
        rules = self._current_rules()
        if idx < 0 or idx >= len(rules):
            QMessageBox.warning(self, tr("text.rules.need_rule", "No rule selected"), tr("text.rules.need_rule_msg", "Please add/select a rule first."))
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
        source = self.source_combo.currentText()
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
        rules[idx].source = self.source_combo.currentText()
        self._refresh_rule_list()
        self.rule_list.setCurrentRow(idx)

    def _delete_rule(self) -> None:
        idx = self.rule_list.currentRow()
        rules = self._current_rules()
        if idx < 0 or idx >= len(rules):
            return
        del rules[idx]
        self._refresh_rule_list()
