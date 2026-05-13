"""
日报系统模块
"""
import json
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional

from ..models.daily_log import DailyLog


class DailyReportManager:
    """日报管理器"""
    
    def __init__(self, data_dir: str = "data/logs"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._logs: dict[str, DailyLog] = {}
        self._load()
    
    def _get_log_file(self, log_date: date) -> Path:
        """获取指定日期的日志文件路径"""
        filename = log_date.strftime("%Y-%m-%d.json")
        return self.data_dir / filename
    
    def _load(self):
        """加载所有日志"""
        self._logs = {}
        for file in self.data_dir.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    log = DailyLog.from_dict(data)
                    log_date = log.date.date() if isinstance(log.date, datetime) else log.date
                    self._logs[log_date] = log
            except Exception as e:
                print(f"加载日志文件 {file} 失败：{e}")
    
    def _save(self, log: DailyLog):
        """保存日志"""
        log_date = log.date.date() if isinstance(log.date, datetime) else log.date
        file_path = self._get_log_file(log_date)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(log.to_dict(), f, ensure_ascii=False, indent=2)
        self._logs[log_date] = log
    
    def create_report(self, report_date: date = None) -> DailyLog:
        """创建新的日报"""
        if report_date is None:
            report_date = date.today()
        
        if report_date in self._logs:
            return self._logs[report_date]
        
        log = DailyLog(date=datetime.combine(report_date, datetime.min.time()))
        self._save(log)
        return log
    
    def get_report(self, report_date: date) -> Optional[DailyLog]:
        """获取指定日期的日报"""
        return self._logs.get(report_date)
    
    def get_today_report(self) -> Optional[DailyLog]:
        """获取今日日报"""
        return self.get_report(date.today())
    
    def add_learning(self, skill_name: str, duration: float, content: str, 
                     notes: str = "", report_date: date = None):
        """添加学习记录"""
        if report_date is None:
            report_date = date.today()
        
        log = self.get_report(report_date)
        if not log:
            log = self.create_report(report_date)
        
        log.add_learning(skill_name, duration, content, notes)
        self._save(log)
        return log
    
    def add_insight(self, insight: str, report_date: date = None):
        """添加心得"""
        if report_date is None:
            report_date = date.today()
        
        log = self.get_report(report_date)
        if not log:
            log = self.create_report(report_date)
        
        log.add_insight(insight)
        self._save(log)
        return log
    
    def add_problem(self, problem: str, solution: str = "", report_date: date = None):
        """添加问题记录"""
        if report_date is None:
            report_date = date.today()
        
        log = self.get_report(report_date)
        if not log:
            log = self.create_report(report_date)
        
        log.add_problem(problem, solution)
        self._save(log)
        return log
    
    def add_plan(self, plan: str, report_date: date = None):
        """添加计划"""
        if report_date is None:
            report_date = date.today()
        
        log = self.get_report(report_date)
        if not log:
            log = self.create_report(report_date)
        
        log.add_plan(plan)
        self._save(log)
        return log
    
    def set_mood(self, mood: int, report_date: date = None):
        """设置心情评分"""
        if report_date is None:
            report_date = date.today()
        
        if not 1 <= mood <= 5:
            raise ValueError("心情评分必须在 1-5 之间")
        
        log = self.get_report(report_date)
        if not log:
            log = self.create_report(report_date)
        
        log.mood = mood
        self._save(log)
        return log
    
    def list_reports(self, start_date: date = None, end_date: date = None) -> List[DailyLog]:
        """列出日报，支持日期范围筛选"""
        logs = list(self._logs.values())
        
        if start_date:
            logs = [l for l in logs if (l.date.date() if isinstance(l.date, datetime) else l.date) >= start_date]
        
        if end_date:
            logs = [l for l in logs if (l.date.date() if isinstance(l.date, datetime) else l.date) <= end_date]
        
        return sorted(logs, key=lambda x: x.date, reverse=True)
    
    def get_statistics(self, start_date: date = None, end_date: date = None) -> dict:
        """获取统计信息"""
        logs = self.list_reports(start_date, end_date)
        
        if not logs:
            return {
                'total_days': 0,
                'total_hours': 0,
                'avg_hours_per_day': 0,
                'most_practiced_skills': [],
                'avg_mood': 0
            }
        
        total_hours = sum(log.total_hours for log in logs)
        skill_counts = {}
        mood_sum = 0
        
        for log in logs:
            mood_sum += log.mood
            for entry in log.learning_entries:
                skill_counts[entry.skill_name] = skill_counts.get(entry.skill_name, 0) + entry.duration
        
        # 找出练习最多的技能
        sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
        most_practiced = sorted_skills[:5]  # Top 5
        
        return {
            'total_days': len(logs),
            'total_hours': total_hours,
            'avg_hours_per_day': total_hours / len(logs) if logs else 0,
            'most_practiced_skills': most_practiced,
            'avg_mood': mood_sum / len(logs) if logs else 0
        }
    
    def export_report(self, report_date: date = None, output_file: str = None) -> str:
        """导出日报为 Markdown"""
        if report_date is None:
            report_date = date.today()
        
        log = self.get_report(report_date)
        if not log:
            return "该日期没有日报记录"
        
        md = log.to_markdown()
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(md)
        
        return md
    
    def export_period_report(self, start_date: date, end_date: date, 
                            output_file: str = None) -> str:
        """导出时间段汇总报告"""
        logs = self.list_reports(start_date, end_date)
        
        if not logs:
            return "该时间段没有日报记录"
        
        md = f"# 📊 周期报告 ({start_date} ~ {end_date})\n\n"
        
        # 汇总统计
        stats = self.get_statistics(start_date, end_date)
        md += "## 📈 总体统计\n\n"
        md += f"- 总天数：{stats['total_days']} 天\n"
        md += f"- 总学习时长：{stats['total_hours']:.1f} 小时\n"
        md += f"- 日均学习：{stats['avg_hours_per_day']:.1f} 小时\n"
        md += f"- 平均心情：{'⭐' * round(stats['avg_mood'])}\n\n"
        
        md += "### 🎯 重点练习技能\n\n"
        for skill, hours in stats['most_practiced_skills']:
            md += f"- {skill}: {hours:.1f} 小时\n"
        md += "\n"
        
        # 每日详情
        md += "## 📅 每日详情\n\n"
        for log in sorted(logs, key=lambda x: x.date):
            date_str = log.date.strftime('%Y-%m-%d')
            md += f"### {date_str}\n"
            md += f"- 学习时长：{log.total_hours:.1f}h | "
            md += f"技能：{log.skills_count}个 | "
            md += f"心情：{'⭐' * log.mood}\n"
            
            if log.learning_entries:
                entries = ", ".join([e.skill_name for e in log.learning_entries])
                md += f"- 内容：{entries}\n"
            
            if log.insights:
                md += f"- 收获：{log.insights[0]}\n" if log.insights else ""
            
            md += "\n"
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(md)
        
        return md
