"""
Core 模块 — Skills Platform v2.0 工作流引擎核心

模块职责：
  - src.core.models       → Pydantic 数据模型（Skill, Workflow, DailyLogEntry 等）
  - src.core.initialize   → 项目初始化
  - src.core.daily_report → (已废弃) v1 日报管理器，请使用 StorageManager
  - src.core.skill_manager → (已废弃) v1 技能管理器，请使用 StorageManager

v1 Legacy 模块（skill_manager, daily_report）保留仅用于数据迁移参考。
新代码请通过 src.storage.base.StorageManager 操作数据。
"""

