"""
技能数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum


class SkillLevel(Enum):
    """技能等级枚举"""
    BEGINNER = 1      # 入门
    INTERMEDIATE = 2  # 熟练
    ADVANCED = 3      # 精通
    EXPERT = 4        # 专家
    MASTER = 5        # 大师


class SkillCategory(Enum):
    """技能分类枚举"""
    TECHNICAL = "technical"        # 技术技能
    SOFT_SKILL = "soft_skill"      # 软技能
    LANGUAGE = "language"          # 语言
    MANAGEMENT = "management"      # 管理
    DESIGN = "design"              # 设计
    OTHER = "other"                # 其他


@dataclass
class Skill:
    """技能数据模型"""
    name: str
    category: SkillCategory = SkillCategory.OTHER
    level: SkillLevel = SkillLevel.BEGINNER
    description: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    parent_skill: Optional[str] = None  # 父技能 ID
    related_skills: List[str] = field(default_factory=list)  # 相关技能 ID 列表
    total_hours: float = 0.0  # 累计学习时长
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'name': self.name,
            'category': self.category.value,
            'level': self.level.value,
            'description': self.description,
            'tags': self.tags,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'parent_skill': self.parent_skill,
            'related_skills': self.related_skills,
            'total_hours': self.total_hours
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Skill':
        """从字典创建实例"""
        return cls(
            name=data['name'],
            category=SkillCategory(data.get('category', 'other')),
            level=SkillLevel(data.get('level', 1)),
            description=data.get('description', ''),
            tags=data.get('tags', []),
            created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else datetime.now(),
            updated_at=datetime.fromisoformat(data['updated_at']) if 'updated_at' in data else datetime.now(),
            parent_skill=data.get('parent_skill'),
            related_skills=data.get('related_skills', []),
            total_hours=data.get('total_hours', 0.0)
        )
    
    def update_level(self, new_level: SkillLevel):
        """更新技能等级"""
        self.level = new_level
        self.updated_at = datetime.now()
    
    def add_hours(self, hours: float):
        """增加学习时长"""
        self.total_hours += hours
        self.updated_at = datetime.now()
