"""Quick verification for core v2 models and execution context."""

import sys
from datetime import datetime

sys.path.insert(0, "F:\\project\\skills")

from src.core.models import (  # noqa: E402
    DailyLogEntry,
    ExecutionContext,
    Skill,
    SkillCategory,
    SkillLevel,
    Workflow,
    WorkflowNode,
    WorkflowNodeType,
)


s = Skill(name="Python", level=SkillLevel.INTERMEDIATE, category=SkillCategory.TECHNICAL)
assert s.name == "Python"
assert s.level == SkillLevel.INTERMEDIATE
assert s.category == SkillCategory.TECHNICAL
assert s.id is not None
print(f"[OK] Skill: {s.name} (id={s.id})")

assert s.promote()
assert s.level == SkillLevel.ADVANCED
print(f"[OK] Skill.promote -> {s.level.name}")

log = DailyLogEntry(
    skill_name="Python",
    learning_content="Pydantic",
    duration_minutes=60,
    mood=5,
)
assert log.skill_name == "Python"
assert log.date == datetime.now().strftime("%Y-%m-%d")
print(f"[OK] DailyLogEntry: {log.skill_name} {log.duration_minutes}min")

wf = Workflow(
    name="Test WF",
    entry_point="start",
    nodes={"start": WorkflowNode(name="Start", node_type=WorkflowNodeType.SEQUENTIAL)},
)
assert wf.name == "Test WF"
assert len(wf.nodes) == 1
print(f"[OK] Workflow: {wf.name}")

ctx = ExecutionContext(workflow_id="wf-1")
ctx.add_log("node1", "running", "info")
ctx.set_node_result("node1", {"ok": True})
assert len(ctx.logs) == 1
assert ctx.node_results["node1"]["output"]["ok"] is True
print(f"[OK] ExecutionContext: {ctx.status} logs={len(ctx.logs)}")

print("\n[OK] 全部验证通过")
