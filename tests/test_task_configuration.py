"""Regression tests for taskset wiring and endpoint contracts."""

from src.locustfile import load_tasks_for_service
from tasksets.rule_management.rules import (
    CreateRuleTaskset,
    GetRuleTaskset,
    ListRulesTaskset,
    UpdateRuleTaskset,
)


def test_rule_management_loads_configured_read_and_write_tasksets() -> None:
    tasks = load_tasks_for_service("rule-management")

    assert set(tasks) == {
        ListRulesTaskset,
        GetRuleTaskset,
        CreateRuleTaskset,
        UpdateRuleTaskset,
    }
    assert tasks[ListRulesTaskset] == 50
    assert tasks[GetRuleTaskset] == 30
    assert tasks[CreateRuleTaskset] == 10
    assert tasks[UpdateRuleTaskset] == 10
