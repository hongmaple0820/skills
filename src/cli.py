"""
Skills 命令行工具
"""
import argparse
import sys
from datetime import date, datetime
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from src.core.skill_manager import SkillManager
    from src.core.daily_report import DailyReportManager
else:
    from .core.skill_manager import SkillManager
    from .core.daily_report import DailyReportManager


def cmd_add_skill(args):
    """添加技能命令"""
    manager = SkillManager()
    try:
        skill = manager.add_skill(
            name=args.name,
            category=args.category,
            level=args.level,
            description=args.description or "",
            tags=args.tags.split(',') if args.tags else []
        )
        print(f"✅ 技能 '{skill.name}' 添加成功!")
        print(f"   分类：{skill.category.value}")
        print(f"   等级：{'⭐' * skill.level.value}")
    except ValueError as e:
        print(f"❌ 错误：{e}")
        sys.exit(1)


def cmd_list_skills(args):
    """列出技能命令"""
    manager = SkillManager()
    skills = manager.list_skills(category=args.category, level=args.level)
    
    if not skills:
        print("暂无技能记录")
        return
    
    print(f"\n📚 技能清单 (共 {len(skills)} 个)\n")
    
    for skill in skills:
        level_stars = '⭐' * skill.level.value
        print(f"• {skill.name} ({skill.category.value})")
        print(f"  等级：{level_stars}")
        if skill.description:
            print(f"  描述：{skill.description}")
        if skill.total_hours > 0:
            print(f"  累计：{skill.total_hours:.1f}h")
        print()


def cmd_show_stats(args):
    """显示统计信息"""
    manager = SkillManager()
    stats = manager.get_statistics()
    
    print("\n📊 技能统计\n")
    print(f"总技能数：{stats['total']}")
    print(f"总学习时长：{stats['total_hours']:.1f}h")
    
    if stats['by_category']:
        print("\n按分类:")
        for cat, count in stats['by_category'].items():
            print(f"  - {cat}: {count}个")
    
    if stats['by_level']:
        print("\n按等级:")
        level_names = {'1': '入门', '2': '熟练', '3': '精通', '4': '专家', '5': '大师'}
        for lvl, count in sorted(stats['by_level'].items()):
            print(f"  - {level_names.get(lvl, lvl)}: {count}个")
    print()


def cmd_export_skills(args):
    """导出技能清单"""
    manager = SkillManager()
    output = args.output or "data/reports/skills_list.md"
    md = manager.export_to_markdown(output)
    print(f"✅ 技能清单已导出到：{output}")


def cmd_add_learning(args):
    """添加学习记录命令"""
    report_mgr = DailyReportManager()
    log = report_mgr.add_learning(
        skill_name=args.skill,
        duration=args.duration,
        content=args.content,
        notes=args.notes or ""
    )
    print(f"✅ 学习记录已添加!")
    print(f"   技能：{args.skill}")
    print(f"   时长：{args.duration}h")
    print(f"   今日总计：{log.total_hours:.1f}h")


def cmd_add_insight(args):
    """添加心得命令"""
    report_mgr = DailyReportManager()
    log = report_mgr.add_insight(args.insight)
    print(f"✅ 心得已添加! (今日共 {len(log.insights)} 条)")


def cmd_add_problem(args):
    """添加问题记录命令"""
    report_mgr = DailyReportManager()
    log = report_mgr.add_problem(args.problem, args.solution or "")
    print(f"✅ 问题已记录!")


def cmd_add_plan(args):
    """添加计划命令"""
    report_mgr = DailyReportManager()
    log = report_mgr.add_plan(args.plan)
    print(f"✅ 计划已添加! (明日共 {len(log.plans)} 项)")


def cmd_set_mood(args):
    """设置心情命令"""
    report_mgr = DailyReportManager()
    log = report_mgr.set_mood(args.mood)
    mood_emoji = ['😞', '😕', '😐', '🙂', '😄']
    print(f"✅ 今日心情：{mood_emoji[args.mood-1]}")


def cmd_show_today(args):
    """显示今日日报"""
    report_mgr = DailyReportManager()
    log = report_mgr.get_today_report()
    
    if not log or (not log.learning_entries and not log.insights):
        print("今日暂无记录，开始记录你的学习吧！\n")
        print("💡 使用示例:")
        print("  python -m skills.cli add-learning Python 2.0 '学习装饰器'")
        print("  python -m skills.cli add-insight '理解了装饰器的原理'")
        return
    
    print(log.to_markdown())


def cmd_show_stats_period(args):
    """显示周期统计"""
    report_mgr = DailyReportManager()
    
    start = date.fromisoformat(args.start) if args.start else None
    end = date.fromisoformat(args.end) if args.end else None
    
    stats = report_mgr.get_statistics(start, end)
    
    period = f"{start} ~ {end}" if start and end else "全部时间"
    print(f"\n📊 周期报告 ({period})\n")
    print(f"总天数：{stats['total_days']}")
    print(f"总学习时长：{stats['total_hours']:.1f}h")
    print(f"日均学习：{stats['avg_hours_per_day']:.1f}h")
    print(f"平均心情：{'⭐' * round(stats['avg_mood'])}")
    
    if stats['most_practiced_skills']:
        print("\n🎯 重点练习技能:")
        for skill, hours in stats['most_practiced_skills']:
            print(f"  - {skill}: {hours:.1f}h")
    print()


def cmd_export_report(args):
    """导出日报"""
    report_mgr = DailyReportManager()
    
    if args.period:
        dates = args.period.split(':')
        start = date.fromisoformat(dates[0])
        end = date.fromisoformat(dates[1]) if len(dates) > 1 else start
        output = args.output or f"data/reports/report_{start}_to_{end}.md"
        md = report_mgr.export_period_report(start, end, output)
    else:
        report_date = date.fromisoformat(args.date) if args.date else date.today()
        output = args.output or f"data/reports/report_{report_date}.md"
        md = report_mgr.export_report(report_date, output)
    
    print(f"✅ 报告已导出到：{output}")


def main():
    parser = argparse.ArgumentParser(
        prog='skills',
        description='📚 Skills - 个人技能管理与日报系统'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # add-skill 命令
    p_skill = subparsers.add_parser('add-skill', help='添加新技能')
    p_skill.add_argument('name', help='技能名称')
    p_skill.add_argument('-c', '--category', default='technical', 
                         choices=['technical', 'soft_skill', 'language', 'management', 'design', 'other'],
                         help='技能分类 (默认：technical)')
    p_skill.add_argument('-l', '--level', type=int, default=1, choices=[1,2,3,4,5],
                         help='技能等级 1-5 (默认：1)')
    p_skill.add_argument('-d', '--description', help='技能描述')
    p_skill.add_argument('-t', '--tags', help='标签，逗号分隔')
    p_skill.set_defaults(func=cmd_add_skill)
    
    # list-skills 命令
    p_list = subparsers.add_parser('list-skills', help='列出技能')
    p_list.add_argument('-c', '--category', help='按分类筛选')
    p_list.add_argument('-l', '--level', type=int, choices=[1,2,3,4,5], help='按等级筛选')
    p_list.set_defaults(func=cmd_list_skills)
    
    # stats 命令
    p_stats = subparsers.add_parser('stats', help='显示技能统计')
    p_stats.set_defaults(func=cmd_show_stats)
    
    # export-skills 命令
    p_exp = subparsers.add_parser('export-skills', help='导出技能清单')
    p_exp.add_argument('-o', '--output', help='输出文件路径')
    p_exp.set_defaults(func=cmd_export_skills)
    
    # add-learning 命令
    p_learn = subparsers.add_parser('add-learning', help='添加学习记录')
    p_learn.add_argument('skill', help='技能名称')
    p_learn.add_argument('duration', type=float, help='学习时长（小时）')
    p_learn.add_argument('content', help='学习内容摘要')
    p_learn.add_argument('-n', '--notes', help='备注')
    p_learn.set_defaults(func=cmd_add_learning)
    
    # add-insight 命令
    p_insight = subparsers.add_parser('add-insight', help='添加心得')
    p_insight.add_argument('insight', help='心得内容')
    p_insight.set_defaults(func=cmd_add_insight)
    
    # add-problem 命令
    p_prob = subparsers.add_parser('add-problem', help='添加问题记录')
    p_prob.add_argument('problem', help='问题描述')
    p_prob.add_argument('-s', '--solution', help='解决方案')
    p_prob.set_defaults(func=cmd_add_problem)
    
    # add-plan 命令
    p_plan = subparsers.add_parser('add-plan', help='添加计划')
    p_plan.add_argument('plan', help='计划内容')
    p_plan.set_defaults(func=cmd_add_plan)
    
    # set-mood 命令
    p_mood = subparsers.add_parser('set-mood', help='设置今日心情')
    p_mood.add_argument('mood', type=int, choices=[1,2,3,4,5], help='心情评分 1-5')
    p_mood.set_defaults(func=cmd_set_mood)
    
    # today 命令
    p_today = subparsers.add_parser('today', help='显示今日日报')
    p_today.set_defaults(func=cmd_show_today)
    
    # period-stats 命令
    p_period = subparsers.add_parser('period-stats', help='显示周期统计')
    p_period.add_argument('--start', help='开始日期 YYYY-MM-DD')
    p_period.add_argument('--end', help='结束日期 YYYY-MM-DD')
    p_period.set_defaults(func=cmd_show_stats_period)
    
    # export-report 命令
    p_exprt = subparsers.add_parser('export-report', help='导出日报')
    p_exprt.add_argument('-d', '--date', help='日期 YYYY-MM-DD (默认：今天)')
    p_exprt.add_argument('-p', '--period', help='周期 YYYY-MM-DD:YYYY-MM-DD')
    p_exprt.add_argument('-o', '--output', help='输出文件路径')
    p_exprt.set_defaults(func=cmd_export_report)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    args.func(args)


if __name__ == '__main__':
    main()
