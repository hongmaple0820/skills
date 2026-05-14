"""
技能管理模块 (v1 Legacy)

⚠️ 已废弃：请使用 src.storage.base.StorageManager + src.core.models.Skill 替代。
此模块保留以供旧数据迁移参考，不应用于新代码。
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict

from ..models.skill import Skill, SkillLevel, SkillCategory


class SkillManager:
    """技能管理器"""
    
    def __init__(self, data_dir: str = "data/skills"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.skills_file = self.data_dir / "skills.json"
        self._skills: Dict[str, Skill] = {}
        self._load()
    
    def _load(self):
        """从文件加载技能数据"""
        if self.skills_file.exists():
            with open(self.skills_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for name, skill_data in data.items():
                    self._skills[name] = Skill.from_dict(skill_data)
    
    def _save(self):
        """保存技能数据到文件"""
        data = {name: skill.to_dict() for name, skill in self._skills.items()}
        with open(self.skills_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_skill(self, name: str, category: str = "other", 
                  level: int = 1, description: str = "", 
                  tags: List[str] = None) -> Skill:
        """添加新技能"""
        if name in self._skills:
            raise ValueError(f"技能 '{name}' 已存在")
        
        skill = Skill(
            name=name,
            category=SkillCategory(category),
            level=SkillLevel(level),
            description=description,
            tags=tags or []
        )
        self._skills[name] = skill
        self._save()
        return skill
    
    def get_skill(self, name: str) -> Optional[Skill]:
        """获取技能"""
        return self._skills.get(name)
    
    def update_skill(self, name: str, **kwargs) -> Optional[Skill]:
        """更新技能信息"""
        skill = self._skills.get(name)
        if not skill:
            return None
        
        for key, value in kwargs.items():
            if hasattr(skill, key):
                if key == 'level':
                    value = SkillLevel(value)
                elif key == 'category':
                    value = SkillCategory(value)
                setattr(skill, key, value)
        
        skill.updated_at = datetime.now()
        self._save()
        return skill
    
    def delete_skill(self, name: str) -> bool:
        """删除技能"""
        if name in self._skills:
            del self._skills[name]
            self._save()
            return True
        return False
    
    def list_skills(self, category: str = None, level: int = None) -> List[Skill]:
        """列出技能，支持筛选"""
        skills = list(self._skills.values())
        
        if category:
            skills = [s for s in skills if s.category.value == category]
        
        if level:
            skills = [s for s in skills if s.level.value == level]
        
        return skills
    
    def get_all_categories(self) -> List[str]:
        """获取所有分类"""
        return list(set(s.category.value for s in self._skills.values()))
    
    def get_statistics(self) -> dict:
        """获取技能统计信息"""
        if not self._skills:
            return {
                'total': 0,
                'by_category': {},
                'by_level': {},
                'total_hours': 0
            }
        
        by_category = {}
        by_level = {}
        total_hours = 0
        
        for skill in self._skills.values():
            # 按分类统计
            cat = skill.category.value
            by_category[cat] = by_category.get(cat, 0) + 1
            
            # 按等级统计
            lvl = str(skill.level.value)
            by_level[lvl] = by_level.get(lvl, 0) + 1
            
            # 累计时长
            total_hours += skill.total_hours
        
        return {
            'total': len(self._skills),
            'by_category': by_category,
            'by_level': by_level,
            'total_hours': total_hours
        }
    
    def export_to_markdown(self, output_file: str = None) -> str:
        """导出技能列表为 Markdown"""
        md = "# 📚 技能清单\n\n"
        
        # 按分类分组
        categories = {}
        for skill in self._skills.values():
            cat = skill.category.value
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(skill)
        
        # 输出每个分类
        category_names = {
            'technical': '技术技能',
            'soft_skill': '软技能',
            'language': '语言',
            'management': '管理',
            'design': '设计',
            'other': '其他'
        }
        
        for cat, skills in categories.items():
            md += f"## {category_names.get(cat, cat)}\n\n"
            
            for skill in sorted(skills, key=lambda x: x.level.value, reverse=True):
                level_names = {
                    1: '⭐ 入门',
                    2: '⭐⭐ 熟练',
                    3: '⭐⭐⭐ 精通',
                    4: '⭐⭐⭐⭐ 专家',
                    5: '⭐⭐⭐⭐⭐ 大师'
                }
                md += f"### {skill.name}\n"
                md += f"- 等级：{level_names.get(skill.level.value, '')}\n"
                if skill.description:
                    md += f"- 描述：{skill.description}\n"
                if skill.tags:
                    md += f"- 标签：{', '.join(skill.tags)}\n"
                if skill.total_hours > 0:
                    md += f"- 累计学习：{skill.total_hours:.1f} 小时\n"
                md += "\n"
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(md)
        
        return md
