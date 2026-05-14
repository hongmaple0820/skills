"""单元测试：核心模型"""
import ast
import json
import os
import pytest
from datetime import datetime
from pathlib import Path
from pydantic import ValidationError
from src.core.models import (
    Skill, SkillLevel, SkillCategory, SkillAction,
    Workflow, WorkflowNode, WorkflowNodeType, ExecutionContext,
    DailyLogEntry, V1_TO_V2_LEVEL, V1_TO_V2_CATEGORY, convert_v1_problems
)
from src.storage.base import StorageManager
from src.workflows.engine import WorkflowEngine


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


def test_v1_to_v2_level_mapping():
    """验证 v1→v2 SkillLevel 语义映射正确"""
    # 映射策略：按名称语义匹配，同名映射到同名；v2 无对应名称则降级到最接近的上级等级
    # v1 BEGINNER(1) → v2 BEGINNER(2), v1 INTERMEDIATE(2) → v2 INTERMEDIATE(3), 等等
    assert V1_TO_V2_LEVEL[1] == SkillLevel.BEGINNER.value    # v1 BEGINNER → v2 BEGINNER（同名映射）
    assert V1_TO_V2_LEVEL[2] == SkillLevel.INTERMEDIATE.value  # v1 INTERMEDIATE → v2 INTERMEDIATE（同名映射）
    assert V1_TO_V2_LEVEL[3] == SkillLevel.ADVANCED.value     # v1 ADVANCED → v2 ADVANCED（同名映射）
    assert V1_TO_V2_LEVEL[4] == SkillLevel.EXPERT.value       # v1 EXPERT → v2 EXPERT（同名映射）
    assert V1_TO_V2_LEVEL[5] == SkillLevel.EXPERT.value       # v1 MASTER → v2 EXPERT（v2 无 MASTER，降级到 EXPERT）


def test_v1_to_v2_category_mapping():
    """验证 v1→v2 SkillCategory 映射"""
    assert V1_TO_V2_CATEGORY["technical"] == "technical"
    assert V1_TO_V2_CATEGORY["soft_skill"] == "soft_skill"
    assert V1_TO_V2_CATEGORY["language"] == "language"
    assert V1_TO_V2_CATEGORY["other"] == "other"
    # v1-only 分类 → OTHER
    assert V1_TO_V2_CATEGORY["management"] == "other"
    assert V1_TO_V2_CATEGORY["design"] == "other"


def test_convert_v1_problems_dicts():
    """验证 v1 [{problem, solution}] → v2 [str]"""
    v1 = [
        {"problem": "安装失败", "solution": "升级 pip"},
        {"problem": "内存不足", "solution": "增加 swap"},
    ]
    result = convert_v1_problems(v1)
    assert len(result) == 2
    assert "安装失败" in result[0]
    assert "升级 pip" in result[0]
    assert "内存不足" in result[1]


def test_convert_v1_problems_str_list():
    """验证 v2 [str] 原样返回"""
    v2 = ["问题: 安装失败 | 解决: 升级 pip"]
    assert convert_v1_problems(v2) == v2


def test_convert_v1_problems_empty():
    """验证空列表"""
    assert convert_v1_problems([]) == []


def test_import_constraint_v1_models():
    """门禁：src/core、src/workflows、src/nodes 禁止 import src.models"""
    forbidden_dirs = ["src/core", "src/workflows", "src/nodes"]
    violations = []
    for d in forbidden_dirs:
        for root, dirs, files in os.walk(d):
            for f in files:
                if not f.endswith(".py"):
                    continue
                path = os.path.join(root, f)
                with open(path, "r", encoding="utf-8") as fh:
                    content = fh.read()
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if node.module and node.module.startswith("src.models"):
                            violations.append(f"{path}: from {node.module} import ...")
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name.startswith("src.models"):
                                violations.append(f"{path}: import {alias.name}")
    assert not violations, f"发现 v1 import 违规:\n" + "\n".join(violations)


def test_data_schema_affinity():
    """门禁：存档数据文件必须与 v2 模型模式一致，不允许 v1-only 字段泄露"""
    data_dir = Path("data")
    if not data_dir.exists():
        pytest.skip("data/ 目录不存在，跳过")

    # v1-only 字段名，迁移后应被封装在 metadata.legacy_fields 内，
    # 不得出现在 v2 模型顶层
    v1_only_top_level_fields = {"total_hours", "parent_skill", "related_skills"}

    # --- 技能数据校验 ---
    skills_file = data_dir / "skills.json"
    if skills_file.exists():
        with open(skills_file, "r", encoding="utf-8") as f:
            items = json.load(f)
        errors = []
        for item in items:
            # 1) 必须能被 Skill 模型反序列化
            try:
                Skill(**item)
            except ValidationError as e:
                errors.append(f"skills.json: id={item.get('id','?')}: {e}")

            # 2) 不能有 v1-only 顶层字段泄露
            leaked = v1_only_top_level_fields & set(item.keys())
            if leaked:
                errors.append(
                    f"skills.json: id={item.get('id','?')} 包含 v1-only 顶层字段: {leaked}。"
                    f" 这些字段应在 metadata.legacy_fields 中。"
                )

        assert not errors, "数据模式亲和性违规:\n" + "\n".join(errors)

    # --- 日报数据校验 ---
    logs_file = data_dir / "daily_logs.json"
    if logs_file.exists():
        with open(logs_file, "r", encoding="utf-8") as f:
            items = json.load(f)
        errors = []
        for item in items:
            # 必须能被 DailyLogEntry 模型反序列化
            try:
                DailyLogEntry(**item)
            except ValidationError as e:
                errors.append(f"daily_logs.json: id={item.get('id','?')}: {e}")
        assert not errors, "数据模式亲和性违规:\n" + "\n".join(errors)


def test_workflow_template_resolution_expression_and_embedded_text():
    """验证工作流模板能解析表达式和嵌入式文本。"""
    engine = WorkflowEngine(StorageManager())
    context = ExecutionContext(workflow_id="wf", variables={"repo_path": ".", "days": 7})
    context.set_node_result("git_stats_node", {"commits_count": 2, "insertions": 12})

    assert engine.resolve_template("{{ variables.repo_path }}", context) == "."
    assert engine.resolve_template("{{ nodes.git_stats_node.output.commits_count > 0 }}", context) is True
    assert engine.resolve_template(
        "今日完成 {{ nodes.git_stats_node.output.commits_count }} 次提交",
        context,
    ) == "今日完成 2 次提交"


def test_workflow_input_resolution_is_recursive():
    """验证列表和字典中的模板也会被递归解析。"""
    engine = WorkflowEngine(StorageManager())
    context = ExecutionContext(workflow_id="wf", variables={"default_mood": 4})
    node = WorkflowNode(
        name="Daily",
        node_type=WorkflowNodeType.CUSTOM,
        inputs={
            "mood": "{{ variables.default_mood }}",
            "insights": ["心情 {{ variables.default_mood }}"],
            "nested": {"mood": "{{ variables.default_mood }}"},
        },
    )

    resolved = engine.resolve_inputs(node, context)

    assert resolved["mood"] == 4
    assert resolved["insights"] == ["心情 4"]
    assert resolved["nested"] == {"mood": 4}


@pytest.mark.asyncio
async def test_workflow_false_condition_skips_node():
    """验证 False 条件不会因为非空字符串而被当成 True。"""
    engine = WorkflowEngine(StorageManager())
    context = ExecutionContext(workflow_id="wf")
    context.set_node_result("git_stats_node", {"commits_count": 0})
    node = WorkflowNode(
        name="Analyze",
        node_type=WorkflowNodeType.CUSTOM,
        condition="{{ nodes.git_stats_node.output.commits_count > 0 }}",
        metadata={"handler": "missing_handler"},
    )

    result = await engine.execute_node(node, context)

    assert result == {"skipped": True, "reason": "condition_not_met"}
