"""
日报数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class LearningEntry:
    """学习记录条目"""
    skill_name: str
    duration: float  # 学习时长（小时）
    content: str     # 学习内容摘要
    notes: str = ""  # 备注
    
    def to_dict(self) -> dict:
        return {
            'skill_name': self.skill_name,
            'duration': self.duration,
            'content': self.content,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'LearningEntry':
        return cls(
            skill_name=data['skill_name'],
            duration=data['duration'],
            content=data['content'],
            notes=data.get('notes', '')
        )


@dataclass
class DailyLog:
    """日报数据模型"""
    date: datetime
    learning_entries: List[LearningEntry] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)  # 收获与心得
    problems: List[dict] = field(default_factory=list)  # 遇到的问题 [{problem, solution}]
    plans: List[str] = field(default_factory=list)  # 明日计划
    mood: int = 3  # 心情评分 1-5
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def total_hours(self) -> float:
        """计算总学习时长"""
        return sum(entry.duration for entry in self.learning_entries)
    
    @property
    def skills_count(self) -> int:
        """统计涉及技能数量"""
        return len(set(entry.skill_name for entry in self.learning_entries))
    
    def add_learning(self, skill_name: str, duration: float, content: str, notes: str = ""):
        """添加学习记录"""
        entry = LearningEntry(
            skill_name=skill_name,
            duration=duration,
            content=content,
            notes=notes
        )
        self.learning_entries.append(entry)
        self.updated_at = datetime.now()
    
    def add_insight(self, insight: str):
        """添加心得"""
        self.insights.append(insight)
        self.updated_at = datetime.now()
    
    def add_problem(self, problem: str, solution: str = ""):
        """添加问题记录"""
        self.problems.append({'problem': problem, 'solution': solution})
        self.updated_at = datetime.now()
    
    def add_plan(self, plan: str):
        """添加计划"""
        self.plans.append(plan)
        self.updated_at = datetime.now()
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'date': self.date.isoformat(),
            'learning_entries': [e.to_dict() for e in self.learning_entries],
            'insights': self.insights,
            'problems': self.problems,
            'plans': self.plans,
            'mood': self.mood,
            'total_hours': self.total_hours,
            'skills_count': self.skills_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DailyLog':
        """从字典创建实例"""
        log = cls(
            date=datetime.fromisoformat(data['date']),
            insights=data.get('insights', []),
            problems=data.get('problems', []),
            plans=data.get('plans', []),
            mood=data.get('mood', 3),
            created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else datetime.now(),
            updated_at=datetime.fromisoformat(data['updated_at']) if 'updated_at' in data else datetime.now()
        )
        log.learning_entries = [
            LearningEntry.from_dict(e) for e in data.get('learning_entries', [])
        ]
        return log
    
    def to_markdown(self) -> str:
        """生成 Markdown 格式的日报"""
        date_str = self.date.strftime('%Y-%m-%d')
        md = f"# 日报 - {date_str}\n\n"
        
        # 今日学习
        md += "## 📚 今日学习\n"
        if self.learning_entries:
            for entry in self.learning_entries:
                md += f"- **{entry.skill_name}** | {entry.duration}h | {entry.content}\n"
                if entry.notes:
                    md += f"  - _{entry.notes}_\n"
        else:
            md += "- 无记录\n"
        md += "\n"
        
        # 收获与心得
        md += "## 💡 收获与心得\n"
        if self.insights:
            for insight in self.insights:
                md += f"- {insight}\n"
        else:
            md += "- 无\n"
        md += "\n"
        
        # 遇到的问题
        md += "## 🐛 遇到的问题\n"
        if self.problems:
            for p in self.problems:
                md += f"- **问题**: {p['problem']}\n"
                if p.get('solution'):
                    md += f"  - **解决**: {p['solution']}\n"
        else:
            md += "- 无\n"
        md += "\n"
        
        # 明日计划
        md += "## 📝 明日计划\n"
        if self.plans:
            for plan in self.plans:
                md += f"- [ ] {plan}\n"
        else:
            md += "- 无\n"
        md += "\n"
        
        # 今日统计
        md += "## 📊 今日统计\n"
        md += f"- 总学习时长：{self.total_hours:.1f} 小时\n"
        md += f"- 涉及技能：{self.skills_count} 个\n"
        md += f"- 心情指数：{'⭐' * self.mood}\n"
        
        return md
