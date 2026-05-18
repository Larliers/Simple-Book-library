from __future__ import annotations

from bookhub.library.text_rules.rule_models import ImportRule, RuleContext, RuleResult
from bookhub.library.text_rules.source_resolver import resolve_source
from bookhub.library.text_rules.step_handlers import StepError, apply_step


def apply_rule(rule: ImportRule, context: RuleContext) -> RuleResult:
    if not rule.source:
        return RuleResult(success=False, value="", failed_step=None, error_message="source is required")

    try:
        value = resolve_source(rule.source, context)
    except Exception as exc:  # noqa: BLE001
        return RuleResult(success=False, value="", failed_step="source", error_message=str(exc))

    for step in rule.steps:
        step_name = str(step.type or "")
        try:
            value = apply_step(str(value), step)
        except StepError as exc:
            return RuleResult(success=False, value="", failed_step=step_name, error_message=str(exc))
        except Exception as exc:  # noqa: BLE001
            return RuleResult(success=False, value="", failed_step=step_name, error_message=str(exc))

    return RuleResult(success=True, value=str(value), failed_step=None, error_message=None)


def apply_rule_chain(rules: list[ImportRule], context: RuleContext) -> RuleResult:
    if not rules:
        return RuleResult(success=False, value="", failed_step=None, error_message="no rules")

    last_failure: RuleResult | None = None
    for rule in rules:
        result = apply_rule(rule, context)
        if result.success and str(result.value).strip():
            return RuleResult(success=True, value=str(result.value), failed_step=None, error_message=None)
        last_failure = result

    if last_failure is not None:
        return RuleResult(
            success=False,
            value="",
            failed_step=last_failure.failed_step,
            error_message=last_failure.error_message,
        )
    return RuleResult(success=False, value="", failed_step=None, error_message="all rules failed")
