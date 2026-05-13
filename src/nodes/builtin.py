"""
Skills Platform v2.0 - Built-in Skill Nodes
内置技能节点实现：日报、代码分析、Git 操作等
"""
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

from ..core.models import DailyLogEntry, Skill, SkillLevel
from ..storage.base import StorageManager


class DailyReportNode:
    """日报生成节点"""

    def __init__(self, storage: StorageManager):
        self.storage = storage

    def execute(self, inputs: Dict[str, Any], context) -> Dict[str, Any]:
        """
        执行日报生成
        输入：skill_name, learning_content, duration_minutes, insights, problems, plans, mood
        输出：生成的日报 ID 和统计信息
        """
        skill_name = inputs.get("skill_name", "General")
        learning_content = inputs.get("learning_content", "")
        duration_minutes = inputs.get("duration_minutes", 0)
        insights = inputs.get("insights", [])
        problems = inputs.get("problems", [])
        plans = inputs.get("plans", [])
        mood = inputs.get("mood")

        # 查找或创建技能
        skill_storage = self.storage.skill_storage()
        skills = skill_storage.query({"name": skill_name})
        
        if skills:
            skill = skills[0]
            skill_id = skill.id
        else:
            # 创建新技能
            new_skill = Skill(name=skill_name, category="technical")
            skill_storage.save(new_skill)
            skill_id = new_skill.id

        # 创建日报条目
        # 确保 mood 是整数
        mood_value = int(mood) if mood is not None else None
        
        daily_log = DailyLogEntry(
            skill_id=skill_id,
            skill_name=skill_name,
            learning_content=learning_content,
            duration_minutes=duration_minutes,
            insights=insights if isinstance(insights, list) else [insights],
            problems=problems if isinstance(problems, list) else [problems],
            plans=plans if isinstance(plans, list) else [plans],
            mood=mood_value,
            workflow_execution_id=context.execution_id
        )

        daily_log_storage = self.storage.daily_log_storage()
        daily_log_storage.save(daily_log)

        # 生成统计信息
        today_stats = self._get_today_stats()
        
        return {
            "daily_log_id": daily_log.id,
            "skill_id": skill_id,
            "skill_name": skill_name,
            "date": daily_log.date,
            "duration_minutes": duration_minutes,
            "insights_count": len(daily_log.insights),
            "problems_count": len(daily_log.problems),
            "plans_count": len(daily_log.plans),
            "mood_emoji": self._get_mood_emoji(mood),
            "today_stats": today_stats,
            "success": True
        }

    def _get_today_stats(self) -> Dict[str, Any]:
        """获取今日统计"""
        today = datetime.now().strftime("%Y-%m-%d")
        daily_log_storage = self.storage.daily_log_storage()
        today_logs = daily_log_storage.query({"date": today})
        
        total_minutes = sum(log.duration_minutes for log in today_logs)
        skills_practiced = list(set(log.skill_name for log in today_logs))
        total_insights = sum(len(log.insights) for log in today_logs)
        total_problems = sum(len(log.problems) for log in today_logs)
        
        return {
            "total_learning_minutes": total_minutes,
            "skills_practiced": skills_practiced,
            "total_insights": total_insights,
            "total_problems": total_problems,
            "logs_count": len(today_logs)
        }

    def _get_mood_emoji(self, mood: int) -> str:
        """获取心情表情"""
        if not mood:
            return "😐"
        mapping = {5: "🌟", 4: "😊", 3: "😐", 2: "😔", 1: "😫"}
        return mapping.get(mood, "😐")


class CodeAnalysisNode:
    """代码分析节点（模拟）"""

    def execute(self, inputs: Dict[str, Any], context) -> Dict[str, Any]:
        """
        分析代码文件
        输入：file_path, language
        输出：代码统计、复杂度分析
        """
        file_path = inputs.get("file_path", "")
        language = inputs.get("language", "python")

        # 模拟分析结果
        result = {
            "file_path": file_path,
            "language": language,
            "lines_of_code": 0,
            "comment_lines": 0,
            "blank_lines": 0,
            "functions_count": 0,
            "classes_count": 0,
            "complexity_score": 0,
            "suggestions": [],
            "success": True
        }

        # 实际分析文件
        path = Path(file_path)
        if path.exists():
            try:
                content = path.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                result["lines_of_code"] = len([l for l in lines if l.strip() and not l.strip().startswith('#')])
                result["comment_lines"] = len([l for l in lines if l.strip().startswith('#')])
                result["blank_lines"] = len([l for l in lines if not l.strip()])
                result["functions_count"] = content.count('def ')
                result["classes_count"] = content.count('class ')
                
                # 简单复杂度估算
                result["complexity_score"] = (
                    result["functions_count"] * 2 + 
                    result["classes_count"] * 5 +
                    content.count('if ') + 
                    content.count('for ') + 
                    content.count('while ')
                )
                
                # 生成建议
                if result["complexity_score"] > 20:
                    result["suggestions"].append("考虑重构高复杂度函数")
                if result["comment_lines"] < result["lines_of_code"] * 0.1:
                    result["suggestions"].append("增加代码注释")
                    
            except Exception as e:
                result["success"] = False
                result["error"] = str(e)

        return result


class GitStatsNode:
    """Git 统计节点"""

    def execute(self, inputs: Dict[str, Any], context) -> Dict[str, Any]:
        """
        获取 Git 提交统计
        输入：repo_path, days
        输出：提交次数、文件变更等
        """
        repo_path = inputs.get("repo_path", ".")
        days = inputs.get("days", 7)

        # 模拟 Git 统计
        result = {
            "repo_path": repo_path,
            "period_days": days,
            "commits_count": 0,
            "files_changed": 0,
            "insertions": 0,
            "deletions": 0,
            "success": True
        }

        try:
            import subprocess
            
            # 获取提交数
            cmd_commits = f"cd {repo_path} && git log --since='{days} days ago' --oneline | wc -l"
            commits_result = subprocess.run(cmd_commits, shell=True, capture_output=True, text=True)
            result["commits_count"] = int(commits_result.stdout.strip())
            
            # 获取变更统计
            cmd_stats = f"cd {repo_path} && git log --since='{days} days ago' --numstat --pretty=format:'' | awk '{{add+=$1; del+=$2}} END {{print add, del}}'"
            stats_result = subprocess.run(cmd_stats, shell=True, capture_output=True, text=True)
            if stats_result.stdout.strip():
                parts = stats_result.stdout.strip().split()
                result["insertions"] = int(parts[0]) if parts[0] != '-' else 0
                result["deletions"] = int(parts[1]) if len(parts) > 1 and parts[1] != '-' else 0
                result["files_changed"] = result["commits_count"]  # 简化估算
            
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)

        return result


class SkillProgressNode:
    """技能进度追踪节点"""

    def __init__(self, storage: StorageManager):
        self.storage = storage

    def execute(self, inputs: Dict[str, Any], context) -> Dict[str, Any]:
        """
        更新技能进度
        输入：skill_name, action (promote/demote/set_level), level
        输出：技能当前状态
        """
        skill_name = inputs.get("skill_name")
        action = inputs.get("action", "info")
        new_level = inputs.get("level")

        skill_storage = self.storage.skill_storage()
        
        if skill_name:
            skills = skill_storage.query({"name": skill_name})
            if not skills:
                return {"success": False, "error": f"Skill not found: {skill_name}"}
            
            skill = skills[0]
            
            if action == "promote":
                skill.promote()
                skill_storage.update(skill.id, {"level": skill.level.value})
            elif action == "demote":
                skill.demote()
                skill_storage.update(skill.id, {"level": skill.level.value})
            elif action == "set_level" and new_level:
                from ..core.models import SkillLevel
                skill.level = SkillLevel(new_level)
                skill_storage.update(skill.id, {"level": skill.level.value})

            return {
                "skill_id": skill.id,
                "skill_name": skill.name,
                "level": skill.level.name,
                "level_value": skill.level.value,
                "category": skill.category.value,
                "tags": skill.tags,
                "success": True
            }
        else:
            # 返回所有技能概览
            all_skills = skill_storage.get_all()
            return {
                "total_skills": len(all_skills),
                "skills_by_level": self._group_by_level(all_skills),
                "success": True
            }

    def _group_by_level(self, skills: List[Skill]) -> Dict[str, int]:
        """按等级分组统计"""
        groups = {}
        for skill in skills:
            level_name = skill.level.name
            groups[level_name] = groups.get(level_name, 0) + 1
        return groups


# 节点工厂
def create_builtin_nodes(storage: StorageManager) -> Dict[str, callable]:
    """创建所有内置节点处理器"""
    return {
        "daily_report": DailyReportNode(storage).execute,
        "code_analysis": CodeAnalysisNode().execute,
        "git_stats": GitStatsNode().execute,
        "skill_progress": SkillProgressNode(storage).execute,
    }
