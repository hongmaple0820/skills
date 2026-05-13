"""单元测试：核心模型"""
import pytest
from datetime import datetime
from src.core.models import (
    Skill, SkillLevel, SkillCategory, SkillAction,
    Workflow, WorkflowNode, WorkflowNodeType, ExecutionContext,
    DailyLogEntry
)


def test_skill_creation():
    """测试技能创建"""
    skill = Skill(name="Python", level=SkillLevel.INTERMEDIATE, category=SkillCategory.TECHNICAL)
    assert skill.name == "Python"
    assert skill.level == SkillLevel.INTERMEDIATE
    assert skill.category == SkillCategory.TECHNICAL
    assert skill.id is not None


def test_skill_promote():
    """测试技能提升"""
    skill = Skill(name="Python", level=SkillLevel.NOVICE)
    assert skill.promote()
    assert skill.level == SkillLevel.BEGINNER
    assert skill.promote()  # 可以继续提升
    assert skill.level == SkillLevel.INTERMEDIATE


def test_workflow_creation():
    """测试工作流创建"""
    workflow = Workflow(
        name="Test Workflow",
        entry_point="start",
        nodes={
            "start": WorkflowNode(name="Start", node_type=WorkflowNodeType.SEQUENTIAL)
        }
    )
    assert workflow.name == "Test Workflow"
    assert len(workflow.nodes) == 1


def test_execution_context():
    """测试执行上下文"""
    context = ExecutionContext(workflow_id="wf-123")
    assert context.status == "pending"
    assert context.execution_id is not None
    
    context.add_log("node1", "Test log", "info")
    assert len(context.logs) == 1
    
    context.set_node_result("node1", {"output": "test"})
    assert "node1" in context.node_results


def test_daily_log_entry():
    """测试日报条目"""
    log = DailyLogEntry(
        skill_name="Python",
        learning_content="Learned Pydantic",
        duration_minutes=60,
        mood=5
    )
    assert log.skill_name == "Python"
    assert log.mood == 5
    assert log.date == datetime.now().strftime("%Y-%m-%d")
