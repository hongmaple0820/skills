"""
Skills Platform v2.0 - CLI Interface
命令行工具入口
"""
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.json import JSON
from rich.tree import Tree

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.models import Skill, SkillLevel, SkillCategory, Workflow
from src.storage.base import StorageManager
from src.workflows.engine import WorkflowEngine
from src.workflows.parser import load_workflow
from src.nodes.builtin import create_builtin_nodes


console = Console()
storage = StorageManager()


@click.group()
@click.version_option(version='2.0.0')
def cli():
    """Skills Platform v2.0 - 个人工作流操作系统"""
    pass


# ========== 技能管理命令 ==========

@cli.group()
def skill():
    """技能管理"""
    pass


@skill.command('add')
@click.option('--name', '-n', required=True, help='技能名称')
@click.option('--description', '-d', default='', help='技能描述')
@click.option('--level', '-l', type=click.Choice(['1', '2', '3', '4', '5']), default='1', help='技能等级 (1-5)')
@click.option('--category', '-c', type=click.Choice(['technical', 'soft_skill', 'domain_knowledge', 'tool', 'language', 'other']), default='technical', help='技能分类')
@click.option('--tag', '-t', multiple=True, help='标签 (可多次使用)')
def add_skill(name, description, level, category, tag):
    """添加新技能"""
    skill_obj = Skill(
        name=name,
        description=description or None,
        level=SkillLevel(int(level)),
        category=SkillCategory(category),
        tags=list(tag)
    )
    
    storage.skill_storage().save(skill_obj)
    console.print(f"[green]✓[/green] 技能已添加：[bold]{name}[/bold] (ID: {skill_obj.id})")


@skill.command('list')
@click.option('--category', '-c', help='按分类筛选')
@click.option('--level', '-l', type=click.Choice(['1', '2', '3', '4', '5']), help='按等级筛选')
def list_skills(category, level):
    """列出所有技能"""
    skills = storage.skill_storage().get_all()
    
    # 筛选
    if category:
        skills = [s for s in skills if s.category.value == category]
    if level:
        skills = [s for s in skills if s.level.value == int(level)]
    
    if not skills:
        console.print("[yellow]没有找到技能[/yellow]")
        return
    
    table = Table(title="技能列表")
    table.add_column("ID", style="cyan")
    table.add_column("名称", style="green")
    table.add_column("等级", justify="center")
    table.add_column("分类")
    table.add_column("标签")
    
    level_emoji = {1: "⭐", 2: "⭐⭐", 3: "⭐⭐⭐", 4: "⭐⭐⭐⭐", 5: "⭐⭐⭐⭐⭐"}
    
    for skill in skills:
        table.add_row(
            skill.id,
            skill.name,
            level_emoji.get(skill.level.value, ""),
            skill.category.value,
            ", ".join(skill.tags) if skill.tags else "-"
        )
    
    console.print(table)
    console.print(f"\n共 [bold]{len(skills)}[/bold] 个技能")


@skill.command('stats')
def skill_stats():
    """技能统计"""
    skills = storage.skill_storage().get_all()
    
    if not skills:
        console.print("[yellow]暂无技能数据[/yellow]")
        return
    
    # 按等级统计
    by_level = {}
    for skill in skills:
        level_name = skill.level.name
        by_level[level_name] = by_level.get(level_name, 0) + 1
    
    # 按分类统计
    by_category = {}
    for skill in skills:
        cat_name = skill.category.value
        by_category[cat_name] = by_category.get(cat_name, 0) + 1
    
    tree = Tree("📊 技能统计")
    
    level_branch = tree.add("按等级")
    for level, count in sorted(by_level.items()):
        level_branch.add(f"{level}: {count}")
    
    category_branch = tree.add("按分类")
    for category, count in sorted(by_category.items()):
        category_branch.add(f"{category}: {count}")
    
    console.print(tree)
    console.print(f"\n总计：[bold]{len(skills)}[/bold] 个技能")


@skill.command('delete')
@click.argument('skill_id')
def delete_skill(skill_id):
    """删除技能"""
    if storage.skill_storage().delete(skill_id):
        console.print(f"[green]✓[/green] 技能已删除：{skill_id}")
    else:
        console.print(f"[red]✗[/red] 未找到技能：{skill_id}")


# ========== 工作流管理命令 ==========

@cli.group()
def workflow():
    """工作流管理"""
    pass


@workflow.command('load')
@click.argument('yaml_file', type=click.Path(exists=True))
def load_workflow_cmd(yaml_file):
    """从 YAML 文件加载工作流"""
    try:
        workflow_obj = load_workflow(yaml_file)
        storage.workflow_storage().save(workflow_obj)
        console.print(f"[green]✓[/green] 工作流已加载：[bold]{workflow_obj.name}[/bold] (ID: {workflow_obj.id})")
        console.print(f"   节点数：{len(workflow_obj.nodes)}")
        console.print(f"   入口：{workflow_obj.entry_point}")
    except Exception as e:
        console.print(f"[red]✗[/red] 加载失败：{e}")


@workflow.command('list')
def list_workflows():
    """列出所有工作流"""
    workflows = storage.workflow_storage().get_all()
    
    if not workflows:
        console.print("[yellow]没有工作流，使用 'workflow load' 加载 YAML 文件[/yellow]")
        return
    
    table = Table(title="工作流列表")
    table.add_column("ID", style="cyan")
    table.add_column("名称", style="green")
    table.add_column("版本")
    table.add_column("节点数")
    table.add_column("标签")
    
    for wf in workflows:
        table.add_row(
            wf.id,
            wf.name,
            wf.version,
            str(len(wf.nodes)),
            ", ".join(wf.tags) if wf.tags else "-"
        )
    
    console.print(table)


@workflow.command('run')
@click.argument('workflow_id')
@click.option('--var', '-v', multiple=True, help='变量 (格式：key=value)')
def run_workflow(workflow_id, var):
    """执行工作流"""
    # 解析变量
    variables = {}
    for v in var:
        if '=' in v:
            key, value = v.split('=', 1)
            variables[key] = value
    
    try:
        # 创建工作流引擎并注册内置节点
        engine = WorkflowEngine(storage)
        builtin_nodes = create_builtin_nodes(storage)
        for name, handler in builtin_nodes.items():
            engine.register_custom_handler(name, handler)
        
        console.print(f"[blue]▶[/blue] 开始执行工作流：{workflow_id}")
        
        # 执行
        context = engine.run(workflow_id, variables)
        
        # 显示结果
        if context.status == "completed":
            console.print(f"[green]✓[/green] 执行完成!")
        else:
            console.print(f"[red]✗[/red] 执行失败：{context.error}")
        
        # 显示日志
        console.print("\n[bold]执行日志:[/bold]")
        for log in context.logs[-10:]:  # 显示最近 10 条日志
            level_color = {"info": "blue", "warning": "yellow", "error": "red"}.get(log['level'], "white")
            console.print(f"  [{level_color}]{log['timestamp']}[/] {log['message']}")
        
        # 显示节点结果摘要
        if context.node_results:
            console.print(f"\n[bold]节点执行结果:[/bold] {len(context.node_results)} 个节点")
            
    except Exception as e:
        console.print(f"[red]✗[/red] 执行失败：{e}")


# ========== 日报命令 ==========

@cli.group()
def daily():
    """日报管理"""
    pass


@daily.command('add')
@click.option('--skill', '-s', required=True, help='技能名称')
@click.option('--content', '-c', required=True, help='学习内容')
@click.option('--duration', '-d', type=int, default=0, help='学习时长 (分钟)')
@click.option('--insight', '-i', multiple=True, help='心得 (可多次使用)')
@click.option('--problem', '-p', multiple=True, help='问题 (可多次使用)')
@click.option('--plan', '-P', multiple=True, help='计划 (可多次使用)')
@click.option('--mood', '-m', type=click.Choice(['1', '2', '3', '4', '5']), default='4', help='心情 (1-5)')
def add_daily(skill, content, duration, insight, problem, plan, mood):
    """手动添加日报"""
    from src.core.models import DailyLogEntry
    
    # 查找或创建技能
    skills = storage.skill_storage().query({"name": skill})
    if skills:
        skill_id = skills[0].id
    else:
        new_skill = Skill(name=skill, category="technical")
        storage.skill_storage().save(new_skill)
        skill_id = new_skill.id
    
    # 创建日报
    log = DailyLogEntry(
        skill_id=skill_id,
        skill_name=skill,
        learning_content=content,
        duration_minutes=duration,
        insights=list(insight),
        problems=list(problem),
        plans=list(plan),
        mood=int(mood)
    )
    
    storage.daily_log_storage().save(log)
    console.print(f"[green]✓[/green] 日报已添加 (ID: {log.id})")


@daily.command('today')
def today_report():
    """查看今日日报"""
    from datetime import datetime
    
    today = datetime.now().strftime("%Y-%m-%d")
    logs = storage.daily_log_storage().query({"date": today})
    
    if not logs:
        console.print("[yellow]今天还没有记录，使用 'daily add' 添加一条吧![/yellow]")
        return
    
    console.print(Panel(f"[bold]📅 今日日报 ({today})[/bold]", style="blue"))
    
    for log in logs:
        mood_emoji = {5: "🌟", 4: "😊", 3: "😐", 2: "😔", 1: "😫"}.get(log.mood, "😐")
        
        console.print(f"\n[green]{log.skill_name}[/green] {mood_emoji} ({log.duration_minutes}分钟)")
        console.print(f"  📖 {log.learning_content}")
        
        if log.insights:
            console.print("  💡 心得:")
            for insight in log.insights:
                console.print(f"    • {insight}")
        
        if log.problems:
            console.print("  ❓ 问题:")
            for problem in log.problems:
                console.print(f"    • {problem}")
        
        if log.plans:
            console.print("  📋 计划:")
            for plan in log.plans:
                console.print(f"    • {plan}")
    
    # 统计
    total_minutes = sum(log.duration_minutes for log in logs)
    console.print(Panel(f"总计：{len(logs)} 条记录 • {total_minutes} 分钟", style="green"))


# ========== 主程序 ==========

if __name__ == '__main__':
    cli()
