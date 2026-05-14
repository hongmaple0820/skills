# Skills Platform 数据模型架构

## 概述

Skills Platform 存在两套数据模型体系，服务于不同的生命周期阶段。

| 体系 | 位置 | 模型框架 | 用途 | 状态 |
|------|------|---------|------|------|
| v1 (Legacy) | `src/models/` | Python dataclass | CLI 直接输入/输出 | ⚠️ 已废弃 |
| v2 (Current) | `src/core/models.py` | Pydantic | 工作流引擎 + StorageManager | ✅ 当前标准 |

## v1 模型（Legacy）

### 文件位置

- `src/models/skill.py` — `Skill`, `SkillLevel`, `SkillCategory`
- `src/models/daily_log.py` — `DailyLog`, `LearningEntry`

### 设计意图

v1 是为独立 CLI 命令设计的简单数据对象。每个模型自带 `to_dict()` / `from_dict()` 直接序列化，无类型校验。

### 字段映射（v1 → v2 对照）

| v1 `Skill` 字段 | v2 `Skill` 字段 | 备注 |
|----------------|----------------|------|
| `name` | `name` | 直接映射 |
| `category` | `category` | **枚举值不同**：v1 含 `management`/`design`（→`metadata.legacy_fields`），v2 含 `domain_knowledge`/`tool`；v1 特有值转换时映射为 `OTHER` |
| `level` | `level` | **枚举值不同**：v1: `BEGINNER=1, INTERMEDIATE=2, ADVANCED=3, EXPERT=4, MASTER=5`；v2: `NOVICE=1, BEGINNER=2, INTERMEDIATE=3, ADVANCED=4, EXPERT=5` |
| `description` | `description` | 直接映射 |
| `tags` | `tags` | 直接映射 |
| `created_at` | `created_at` | 直接映射 |
| `updated_at` | `updated_at` | 直接映射 |
| `parent_skill` | `metadata.legacy_fields` | v1 特有字段，存入 `metadata.legacy_fields["parent_skill"]` |
| `related_skills` | `metadata.legacy_fields` | v1 特有字段，存入 `metadata.legacy_fields["related_skills"]` |
| `total_hours` | `metadata.legacy_fields` | v1 特有字段，存入 `metadata.legacy_fields["total_hours"]` |
| — | `id` | v2 用 `uuid4` 前 8 位作为短 ID（Pydantic 自动生成） |
| — | `actions` | v2 特有的工作流动作定义 |
| — | `metadata` | v2 扩展字典；v1 特有字段经转换后存入 `metadata.legacy_fields` |

| v1 `DailyLog` / `LearningEntry` | v2 `DailyLogEntry` | 备注 |
|-------------------------------|-------------------|------|
| `date` (datetime) | `date` (str, format: YYYY-MM-DD) | v2 存字符串 |
| `learning_entries[].skill_name` | `skill_name` | 直接映射 |
| `learning_entries[].duration` | `duration_minutes` | **单位不同**：v1 是"小时"，v2 是"分钟" |
| `learning_entries[].content` | `learning_content` | 命名差异 |
| `insights` | `insights` | 直接映射 |
| `problems` | `problems` | **格式不同**：v1 是 `List[{problem, solution}]`，v2 是 `List[str]` |
| `plans` | `plans` | 直接映射 |
| `mood` | `mood` | 直接映射 |
| — | `skill_id` | v2 关联技能 UUID |
| — | `workflow_execution_id` | v2 用于跟踪工作流来源 |
| — | `id` | v2 用 `uuid4` 前 8 位作为短 ID；迁移脚本对 v1 日报生成稳定短 ID |

## v2 模型（Current）

### 文件位置

- `src/core/models.py` — 所有 Pydantic 模型

### 设计意图

v2 为工作流引擎 + StorageManager 服务。用 Pydantic 做校验，用短 ID 做持久化主键。

### 存储后端

- `StorageManager` 负责全量 CRUD，统一入口
- `JSONStorage` / `SQLiteStorage` 两种实现
- 数据文件：`data/skills.json`、`data/daily_logs.json`、`data/workflows.json`

## 常用转换代码

### v1 Skill → v2 Skill

```python
from src.core.models import Skill as V2Skill, SkillLevel, SkillCategory
from src.models.skill import Skill as V1Skill

# 映射表应在 src.core.models 中定义（迁移门禁 #1）
V1_TO_V2_LEVEL = {
    1: SkillLevel.BEGINNER,     # v1 BEGINNER(1) → v2 BEGINNER(2)
    2: SkillLevel.INTERMEDIATE, # v1 INTERMEDIATE(2) → v2 INTERMEDIATE(3)
    3: SkillLevel.ADVANCED,     # v1 ADVANCED(3) → v2 ADVANCED(4)
    4: SkillLevel.EXPERT,       # v1 EXPERT(4) → v2 EXPERT(5)
    5: SkillLevel.EXPERT,       # v1 MASTER(5) → v2 EXPERT(5)
}
V1_TO_V2_CATEGORY = {
    "technical": SkillCategory.TECHNICAL,
    "soft_skill": SkillCategory.SOFT_SKILL,
    "language": SkillCategory.LANGUAGE,
    "management": SkillCategory.OTHER,   # v1 特有 → OTHER + legacy_fields
    "design": SkillCategory.OTHER,       # v1 特有 → OTHER + legacy_fields
}

def v1_skill_to_v2(v1: V1Skill) -> V2Skill:
    """将 v1 Skill 转换为 v2 Skill，保留 v1 特有字段到 metadata.legacy_fields"""
    legacy = {}
    if v1.parent_skill:
        legacy["parent_skill"] = v1.parent_skill
    if v1.related_skills:
        legacy["related_skills"] = v1.related_skills
    if v1.total_hours is not None:
        legacy["total_hours"] = v1.total_hours
    if v1.category.value in ("management", "design"):
        legacy["original_category"] = v1.category.value

    category = V1_TO_V2_CATEGORY.get(v1.category.value, SkillCategory.OTHER)
    level = V1_TO_V2_LEVEL.get(v1.level.value, SkillLevel.NOVICE)

    return V2Skill(
        name=v1.name,
        category=category,
        level=level,
        description=v1.description,
        tags=v1.tags,
        created_at=v1.created_at,
        updated_at=v1.updated_at,
        # id 由 Pydantic 自动生成，无需传参
        metadata={"legacy_fields": legacy} if legacy else {},
    )
```

### v2 Skill → v1 Skill（如需迁移反向）

```python
# 反向映射表
V2_TO_V1_LEVEL = {
    SkillLevel.NOVICE: 1,       # v2 NOVICE(1) → v1 BEGINNER(1)
    SkillLevel.BEGINNER: 1,     # v2 BEGINNER(2) → v1 BEGINNER(1)
    SkillLevel.INTERMEDIATE: 2, # v2 INTERMEDIATE(3) → v1 INTERMEDIATE(2)
    SkillLevel.ADVANCED: 3,     # v2 ADVANCED(4) → v1 ADVANCED(3)
    SkillLevel.EXPERT: 4,       # v2 EXPERT(5) → v1 EXPERT(4)
}

def v2_skill_to_v1(v2: V2Skill) -> V1Skill:
    """将 v2 Skill 转换回 v1 Skill，从 metadata.legacy_fields 恢复 v1 特有字段"""
    legacy = (v2.metadata or {}).get("legacy_fields") or {}

    from src.models.skill import SkillLevel as V1Level, SkillCategory as V1Category

    return V1Skill(
        name=v2.name,
        category=V1Category(legacy.get("original_category", v2.category.value)),
        level=V1Level(V2_TO_V1_LEVEL.get(v2.level, 1)),
        description=v2.description or "",
        tags=v2.tags or [],
        parent_skill=legacy.get("parent_skill"),
        related_skills=legacy.get("related_skills", []),
        total_hours=legacy.get("total_hours"),
        created_at=v2.created_at,
        updated_at=v2.updated_at,
    )
```

## 核心原则

1. **新代码一律使用 v2（Pydantic）模型**，走 `StorageManager`
2. **不要直接 import v1 dataclass** 到 `src/core/`、`src/workflows/`、`src/nodes/` 中
3. 需要操作旧数据时，显式调用转换函数
4. 迁移实现以 `scripts/migrate_v1_to_v2.py` 和 `tests/unit/test_models.py` 中的门禁测试为准
