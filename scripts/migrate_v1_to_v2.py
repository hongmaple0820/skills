#!/usr/bin/env python3
"""
Skills Platform v1 → v2 数据迁移脚本

将 v1 遗留数据（data/skills/skills.json, data/logs/*.json）
迁移到 v2 格式（data/skills.json, data/daily_logs.json）。

用法：
    python scripts/migrate_v1_to_v2.py          # 执行迁移
    python scripts/migrate_v1_to_v2.py --dry    # 预览（不写文件）
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from uuid import NAMESPACE_URL, uuid5

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.models import Skill, SkillLevel, SkillCategory, DailyLogEntry
from src.core.models import V1_TO_V2_LEVEL, V1_TO_V2_CATEGORY, convert_v1_problems


def load_v1_skills(path: Path) -> Dict[str, dict]:
    """加载 v1 格式的技能数据"""
    if not path.exists():
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_v1_logs(path: Path) -> List[dict]:
    """加载 v1 格式的日志文件列表"""
    if not path.exists():
        return []
    logs = []
    for file in sorted(path.glob("*.json")):
        with open(file, 'r', encoding='utf-8') as f:
            logs.append(json.load(f))
    return logs


def convert_v1_skill(name: str, v1_data: dict) -> dict:
    """将单条 v1 技能数据转换为 v2 Skill 的 dict"""
    cat = v1_data.get("category", "other")
    v2_cat = V1_TO_V2_CATEGORY.get(cat, "other")
    # v1 没有 v2 特有的 category
    v1_level = v1_data.get("level", 1)
    v2_level = V1_TO_V2_LEVEL.get(v1_level, 1)
    
    # 收集 v1-only 字段到 metadata.legacy_fields
    legacy = {}
    if cat in ("management", "design"):
        legacy["v1_category"] = cat
    for field in ("parent_skill", "related_skills", "total_hours"):
        val = v1_data.get(field)
        if val not in (None, 0.0, "", []):
            legacy[field] = val
    
    metadata = {}
    if legacy:
        metadata["legacy_fields"] = legacy
    
    skill_kwargs = dict(
        name=name,
        category=SkillCategory(v2_cat),
        level=SkillLevel(v2_level),
        description=v1_data.get("description", ""),
        tags=v1_data.get("tags", []),
        metadata=metadata,
    )
    if v1_data.get("id"):
        skill_kwargs["id"] = v1_data["id"]
    skill = Skill(**skill_kwargs)
    return skill.model_dump()


def convert_v1_log(v1_data: dict) -> List[dict]:
    """将单条 v1 日报数据转换为 v2 DailyLogEntry 的 dict 列表"""
    # v1 日期字段可以是 datetime 对象或字符串
    date_val = v1_data.get("date", "")
    if isinstance(date_val, str):
        date_str = date_val[:10]
    else:
        # 已序列化为 datetime 字符串
        try:
            date_str = datetime.fromisoformat(date_val).strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            date_str = datetime.now().strftime("%Y-%m-%d")
    
    entries = v1_data.get("learning_entries", [])
    if not entries:
        # 如果没有学习条目，仍然生成一条空记录
        stable_id = str(uuid5(
            NAMESPACE_URL,
            "|".join(["skills-platform-v1-log", date_str, "empty"])
        ))[:8]
        return [DailyLogEntry(
            id=stable_id,
            skill_name="(未指定)",
            learning_content="",
            duration_minutes=0,
            insights=v1_data.get("insights", []),
            problems=convert_v1_problems(v1_data.get("problems", [])),
            plans=v1_data.get("plans", []),
            mood=v1_data.get("mood", 3),
        ).model_dump()]
    
    results = []
    for index, entry in enumerate(entries):
        # v1 duration 是小时，v2 是分钟
        duration_minutes = int(float(entry.get("duration", 0)) * 60)
        stable_id = str(uuid5(
            NAMESPACE_URL,
            "|".join([
                "skills-platform-v1-log",
                date_str,
                str(index),
                entry.get("skill_name", "(未指定)"),
                entry.get("content", entry.get("notes", "")),
            ])
        ))[:8]
        log = DailyLogEntry(
            id=stable_id,
            skill_name=entry.get("skill_name", "(未指定)"),
            learning_content=entry.get("content", entry.get("notes", "")),
            duration_minutes=duration_minutes,
            date=date_str,
            insights=v1_data.get("insights", []),
            problems=convert_v1_problems(v1_data.get("problems", [])),
            plans=v1_data.get("plans", []),
            mood=v1_data.get("mood", 3),
        )
        results.append(log.model_dump())
    return results


def main():
    parser = argparse.ArgumentParser(description="迁移 v1 数据到 v2 格式")
    parser.add_argument("--dry", action="store_true", help="预览模式，不写入文件")
    args = parser.parse_args()
    
    data_dir = PROJECT_ROOT / "data"
    
    # --- 技能迁移 ---
    v1_skills_file = data_dir / "skills" / "skills.json"
    v2_skills_file = data_dir / "skills.json"
    
    print("=" * 60)
    print("技能数据迁移")
    print("=" * 60)
    
    v1_skills = load_v1_skills(v1_skills_file)
    print(f"  v1 数据源: {v1_skills_file} ({len(v1_skills)} 条)")
    
    v2_existing = {}
    if v2_skills_file.exists():
        with open(v2_skills_file, 'r', encoding='utf-8') as f:
            v2_existing = {item.get("name"): item for item in json.load(f)}
        print(f"  v2 目标已有: {len(v2_existing)} 条")
    
    merged = dict(v2_existing)
    new_count = 0
    for name, v1_data in v1_skills.items():
        if name not in merged:
            merged[name] = convert_v1_skill(name, v1_data)
            new_count += 1
    
    print(f"  新增: {new_count} 条, 总条数: {len(merged)}")
    
    if not args.dry and new_count > 0:
        with open(v2_skills_file, 'w', encoding='utf-8') as f:
            json.dump(list(merged.values()), f, ensure_ascii=False, indent=2)
        print(f"  ✅ 已写入 {v2_skills_file}")
    elif args.dry:
        print(f"  [预览模式] 未写入文件")
    else:
        print(f"  ℹ️  无需更新")
    
    # --- 技能 ID 映射 ---
    mapping_file = data_dir / "skill_id_mapping.json"
    skill_id_mapping = {name: merged[name].get("id", "") for name in v1_skills}
    if not args.dry:
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(skill_id_mapping, f, ensure_ascii=False, indent=2)
        print(f"  ✅ 已写入 {mapping_file}")
    else:
        print(f"  [预览模式] 映射文件未写入")
    
    # --- 日志迁移 ---
    v1_logs_dir = data_dir / "logs"
    v2_logs_file = data_dir / "daily_logs.json"
    
    print()
    print("=" * 60)
    print("日报数据迁移")
    print("=" * 60)
    
    v1_logs = load_v1_logs(v1_logs_dir)
    print(f"  v1 数据源: {v1_logs_dir}/ ({len(v1_logs)} 天)")
    
    v2_existing_logs = []
    if v2_logs_file.exists():
        with open(v2_logs_file, 'r', encoding='utf-8') as f:
            v2_existing_logs = json.load(f)
        print(f"  v2 目标已有: {len(v2_existing_logs)} 条")
    
    existing_ids = {item.get("id") for item in v2_existing_logs}
    new_logs = []
    for v1_log_data in v1_logs:
        converted = convert_v1_log(v1_log_data)
        for log_dict in converted:
            if log_dict.get("id") not in existing_ids:
                new_logs.append(log_dict)
    
    all_logs = v2_existing_logs + new_logs
    
    print(f"  新增: {len(new_logs)} 条, 总条数: {len(all_logs)}")
    
    if not args.dry and new_logs:
        with open(v2_logs_file, 'w', encoding='utf-8') as f:
            json.dump(all_logs, f, ensure_ascii=False, indent=2)
        print(f"  ✅ 已写入 {v2_logs_file}")
    elif args.dry:
        print(f"  [预览模式] 未写入文件")
    else:
        print(f"  ℹ️  无需更新")
    
    # --- 总结 ---
    print()
    print("=" * 60)
    print("迁移完成")
    print("=" * 60)
    if args.dry:
        print("运行 without --dry 来实际写入文件")
    else:
        print("✅ 迁移完成。")
        print(f"📋 技能 ID 映射: {mapping_file}")
        print("💡 确认数据正确后，可安全删除旧目录:")
        print(f"   - {v1_skills_file.parent}")
        print(f"   - {v1_logs_dir}")


if __name__ == "__main__":
    main()
