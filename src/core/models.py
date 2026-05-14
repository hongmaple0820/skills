"""
Skills Platform v2.0 - Core Models
原子化技能模型、工作流定义、执行上下文
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
from enum import Enum
import uuid


class SkillLevel(int, Enum):
    """技能等级 1-5"""
    NOVICE = 1
    BEGINNER = 2
    INTERMEDIATE = 3
    ADVANCED = 4
    EXPERT = 5


class SkillCategory(str, Enum):
    """技能分类"""
    TECHNICAL = "technical"
    SOFT_SKILL = "soft_skill"
    DOMAIN_KNOWLEDGE = "domain_knowledge"
    TOOL = "tool"
    LANGUAGE = "language"
    OTHER = "other"


class SkillAction(BaseModel):
    """技能绑定的可执行动作"""
    action_type: str = Field(..., description="动作类型：cli_function, api_call, workflow_trigger")
    target: str = Field(..., description="目标：函数名、API 端点、工作流 ID")
    params: Dict[str, Any] = Field(default_factory=dict, description="动作参数")
    description: Optional[str] = None


class Skill(BaseModel):
    """原子化技能单元"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    level: SkillLevel = Field(default=SkillLevel.NOVICE)
    category: SkillCategory = Field(default=SkillCategory.OTHER)
    tags: List[str] = Field(default_factory=list)
    actions: List[SkillAction] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def promote(self):
        """提升技能等级"""
        if self.level < SkillLevel.EXPERT:
            self.level = SkillLevel(self.level.value + 1)
            self.updated_at = datetime.now()
            return True
        return False

    def demote(self):
        """降低技能等级"""
        if self.level > SkillLevel.NOVICE:
            self.level = SkillLevel(self.level.value - 1)
            self.updated_at = datetime.now()
            return True
        return False


class WorkflowNodeType(str, Enum):
    """节点类型"""
    SKILL_ACTION = "skill_action"
    DECISION = "decision"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    SUB_WORKFLOW = "sub_workflow"
    CUSTOM = "custom"


class WorkflowNode(BaseModel):
    """工作流节点"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    node_type: WorkflowNodeType
    skill_id: Optional[str] = None  # 关联的技能 ID
    action: Optional[SkillAction] = None
    condition: Optional[str] = None  # Jinja2 模板表达式
    inputs: Dict[str, Any] = Field(default_factory=dict)  # 输入映射 {{ nodes.xxx.output }} - 支持任意类型
    outputs: Dict[str, str] = Field(default_factory=dict)  # 输出映射
    children: List[str] = Field(default_factory=list)  # 子节点 ID 列表（用于 parallel/sequential）
    retry_count: int = 0
    timeout: Optional[int] = None  # 超时秒数
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowTrigger(BaseModel):
    """工作流触发器"""
    type: Literal["manual", "scheduled", "event"]
    cron: Optional[str] = None  # 定时任务表达式
    event: Optional[str] = None  # 事件名称


class Workflow(BaseModel):
    """工作流定义"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    description: Optional[str] = None
    version: str = "1.0.0"
    nodes: Dict[str, WorkflowNode] = Field(default_factory=dict)
    entry_point: str  # 入口节点 ID
    triggers: List[WorkflowTrigger] = Field(default_factory=list)
    variables: Dict[str, Any] = Field(default_factory=dict)  # 全局变量
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    tags: List[str] = Field(default_factory=list)


class ExecutionContext(BaseModel):
    """执行上下文"""
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    workflow_id: str
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    status: Literal["pending", "running", "completed", "failed", "cancelled"] = "pending"
    node_results: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    variables: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    logs: List[Dict[str, Any]] = Field(default_factory=list)

    def add_log(self, node_id: str, message: str, level: str = "info"):
        self.logs.append({
            "timestamp": datetime.now().isoformat(),
            "node_id": node_id,
            "message": message,
            "level": level
        })

    def set_node_result(self, node_id: str, result: Dict[str, Any]):
        self.node_results[node_id] = {
            "output": result,
            "completed_at": datetime.now().isoformat(),
            "status": "success"
        }

    def set_node_error(self, node_id: str, error: str):
        self.node_results[node_id] = {
            "error": error,
            "failed_at": datetime.now().isoformat(),
            "status": "failed"
        }


class DailyLogEntry(BaseModel):
    """日报条目"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    skill_id: Optional[str] = None
    skill_name: str
    learning_content: str
    duration_minutes: int = 0
    insights: List[str] = Field(default_factory=list)
    problems: List[str] = Field(default_factory=list, description="v1 迁移时请用 convert_v1_problems()")
    plans: List[str] = Field(default_factory=list)
    mood: Optional[int] = Field(None, ge=1, le=5)  # 1-5
    workflow_execution_id: Optional[str] = None  # 关联的工作流执行 ID
    created_at: datetime = Field(default_factory=datetime.now)


class MoodEmoji(str, Enum):
    """心情表情"""
    EXCELLENT = "🌟"
    GOOD = "😊"
    NEUTRAL = "😐"
    BAD = "😔"
    TERRIBLE = "😫"

    @classmethod
    def from_int(cls, value: int) -> str:
        mapping = {5: cls.EXCELLENT, 4: cls.GOOD, 3: cls.NEUTRAL, 2: cls.BAD, 1: cls.TERRIBLE}
        return mapping.get(value, cls.NEUTRAL).value


# ─── v1 ↔ v2 迁移映射 ─────────────────────────────
# v1 SkillLevel: BEGINNER=1, INTERMEDIATE=2, ADVANCED=3, EXPERT=4, MASTER=5
# v2 SkillLevel: NOVICE=1, BEGINNER=2, INTERMEDIATE=3, ADVANCED=4, EXPERT=5
# 语义映射（按名称对齐，不按数字裸转）：
#   v1 BEGINNER(1)    → v2 BEGINNER(2)     | v2 NOVICE(1)     → v1 BEGINNER(1)
#   v1 INTERMEDIATE(2) → v2 INTERMEDIATE(3) | v2 BEGINNER(2)   → v1 BEGINNER(1)
#   v1 ADVANCED(3)    → v2 ADVANCED(4)     | v2 INTERMEDIATE(3)→ v1 INTERMEDIATE(2)
#   v1 EXPERT(4)      → v2 EXPERT(5)       | v2 ADVANCED(4)   → v1 ADVANCED(3)
#   v1 MASTER(5)      → v2 EXPERT(5)       | v2 EXPERT(5)     → v1 EXPERT(4)
V1_TO_V2_LEVEL = {1: 2, 2: 3, 3: 4, 4: 5, 5: 5}
V2_TO_V1_LEVEL = {1: 1, 2: 1, 3: 2, 4: 3, 5: 4}

# v1 SkillCategory: TECHNICAL, SOFT_SKILL, LANGUAGE, MANAGEMENT, DESIGN, OTHER
# v2 SkillCategory: TECHNICAL, SOFT_SKILL, DOMAIN_KNOWLEDGE, TOOL, LANGUAGE, OTHER
V1_TO_V2_CATEGORY = {
    "technical": "technical",
    "soft_skill": "soft_skill",
    "language": "language",
    "other": "other",
    # v1-only → v2 无对应，映射到 OTHER 并存 metadata
    "management": "other",
    "design": "other",
}


def convert_v1_problems(v1_problems: list) -> list:
    """将 v1 的 [{problem, solution}] 转为 v2 的 [str]"""
    if not v1_problems:
        return []
    # v2 已是 List[str]
    if all(isinstance(p, str) for p in v1_problems):
        return v1_problems
    # v1 是 List[dict]
    result = []
    for p in v1_problems:
        if isinstance(p, dict):
            prob = p.get("problem", "")
            sol = p.get("solution", "")
            if prob and sol:
                result.append(f"问题: {prob} | 解决: {sol}")
            elif prob:
                result.append(f"问题: {prob}")
            else:
                result.append(sol or str(p))
        else:
            result.append(str(p))
    return result
