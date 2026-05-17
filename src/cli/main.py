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
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.models import Skill, SkillLevel, SkillCategory, Workflow
from src.reports.daily_renderer import render_daily_report, render_theme_preview_gallery
from src.reports.wechat_renderer import render_wechat_article
from src.reports import list_themes, list_wechat_themes
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


@daily.command('render')
@click.option('--date', 'report_date', default=None, help='日报日期 YYYY-MM-DD，默认取最新一天')
@click.option('--theme', default='maple-ai', help='渲染主题')
@click.option('--title', default='AI 科技日报', help='日报标题')
@click.option('--description', default='聚焦 AI 技术推进、工作流执行与次日动作的高密度日报卡片。', help='日报简短描述')
@click.option('--author', default='Skills Workflow', help='作者')
@click.option('--source-name', default='Skills Platform', help='来源名称')
@click.option('--source-statement', default='数据来自 Skills Platform 当日工作流与日报记录，仅用于信息归档与工作复盘。', help='来源声明')
@click.option('--user-note', default='', help='用户备注')
@click.option('--output-dir', default='data/reports', help='输出目录')
def render_daily(report_date, theme, title, description, author, source_name, source_statement, user_note, output_dir):
    """渲染日报展示文件：图片海报 + 交互嵌入 + 文章页"""
    logs = storage.daily_log_storage().get_all()
    if not logs:
        console.print("[red]✗[/red] 没有日报数据可渲染")
        return

    target_date = report_date or max(log.date for log in logs)
    selected_logs = [log for log in logs if log.date == target_date]
    if not selected_logs:
        console.print(f"[red]✗[/red] 未找到 {target_date} 的日报数据")
        return

    rendered = render_daily_report(
        selected_logs,
        date=target_date,
        theme=theme,
        title=title,
        description=description,
        author=author,
        source_name=source_name,
        source_statement=source_statement,
        user_note=user_note,
        output_dir=output_dir,
    )

    table = Table(title="日报渲染结果")
    table.add_column("形式", style="cyan")
    table.add_column("文件", style="green")
    table.add_row("图片版海报 PNG", str(rendered.poster_png_path))
    table.add_row("图片版海报 SVG", str(rendered.poster_svg_path))
    table.add_row("截图底板 HTML", str(rendered.poster_html_path))
    table.add_row("交互版组件", str(rendered.widget_path))
    table.add_row("文章嵌入页", str(rendered.article_path))
    console.print(table)
    console.print("[blue]说明[/blue] 公众号正文优先使用 PNG 图片版；如需截图，可直接打开截图底板 HTML 或文章嵌入页。")


@daily.group()
def theme():
    """日报主题"""
    pass


@theme.command('list')
@click.option('--date', 'report_date', default=None, help='日报日期 YYYY-MM-DD，默认取最新一天')
@click.option('--title', default='AI 科技日报', help='预览标题')
@click.option('--description', default='用于预览所有日报主题的统一示例内容。', help='预览描述')
@click.option('--author', default='Skills Workflow', help='作者')
@click.option('--source-name', default='Skills Platform', help='来源名称')
@click.option('--source-statement', default='主题预览由 Skills Platform 自动生成，用于风格确认与内容发布选型。', help='来源声明')
@click.option('--user-note', default='', help='用户备注')
@click.option('--output-dir', default='data/reports', help='输出目录')
def list_daily_themes(report_date, title, description, author, source_name, source_statement, user_note, output_dir):
    """列出并生成所有日报主题预览"""
    logs = storage.daily_log_storage().get_all()
    if not logs:
        console.print("[red]✗[/red] 没有日报数据可用于主题预览")
        return

    target_date = report_date or max(log.date for log in logs)
    selected_logs = [log for log in logs if log.date == target_date]
    if not selected_logs:
        console.print(f"[red]✗[/red] 未找到 {target_date} 的日报数据")
        return

    gallery_path, bundles = render_theme_preview_gallery(
        selected_logs,
        date=target_date,
        title=title,
        description=description,
        author=author,
        source_name=source_name,
        source_statement=source_statement,
        user_note=user_note,
        output_dir=output_dir,
    )

    metadata = {item["key"]: item for item in list_themes()}
    table = Table(title="日报主题列表")
    table.add_column("Key", style="cyan")
    table.add_column("名称", style="green")
    table.add_column("说明")
    table.add_column("品牌色")
    table.add_column("预览")
    for bundle in bundles:
        theme_meta = metadata[bundle.theme]
        swatches = f"{theme_meta['accent']} / {theme_meta['accent_2']} / {theme_meta['accent_3']}"
        table.add_row(
            bundle.theme,
            bundle.name,
            bundle.description,
            swatches,
            bundle.poster_html_path.name,
        )

    console.print(table)
    console.print(f"[blue]预览页[/blue] {gallery_path}")


# ========== 公众号模板命令 ==========

@cli.group()
def wechat():
    """公众号图文模板"""
    pass


@wechat.command("render")
@click.argument("markdown_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--theme", default="mist-gallery", help="模板主题")
@click.option("--output-dir", default="data/wechat", help="输出目录")
@click.option("--author", default="Skills Workflow", help="作者名")
@click.option("--source-name", default="Skills Platform", help="来源名称")
@click.option("--source-statement", default=None, help="来源声明")
@click.option("--summary", default=None, help="摘要")
@click.option("--publish-date", default=None, help="发布日期，格式 YYYY-MM-DD")
def render_wechat(
    markdown_file: Path,
    theme: str,
    output_dir: str,
    author: str,
    source_name: str,
    source_statement: str | None,
    summary: str | None,
    publish_date: str | None,
):
    """根据 Markdown 和本地图片生成公众号风格模板"""
    rendered = render_wechat_article(
        markdown_file,
        theme=theme,
        output_dir=output_dir,
        author=author,
        source_name=source_name,
        source_statement=source_statement,
        summary=summary,
        publish_date=publish_date,
    )

    table = Table(title="公众号模板输出")
    table.add_column("产物", style="cyan")
    table.add_column("文件", style="green")
    table.add_row("封面 PNG", str(rendered.cover_png_path))
    table.add_row("首屏头图 PNG", str(rendered.article_header_png_path))
    table.add_row("正文长图 PNG", str(rendered.article_long_png_path))
    table.add_row("本地预览 HTML", str(rendered.preview_html_path))
    table.add_row("公众号完整 HTML", str(rendered.wechat_html_path))
    table.add_row("公众号正文片段", str(rendered.wechat_body_path))
    table.add_row("公众号粘贴片段", str(rendered.wechat_paste_path))
    table.add_row("公众号复制板", str(rendered.wechat_copyboard_path))
    table.add_row("素材目录", str(rendered.assets_dir))
    table.add_row("图片数量", str(rendered.image_count))
    console.print(table)
    console.print("[blue]说明[/blue] 优先打开 `wechat-copyboard.html`，点“一键复制富文本”后直接去公众号编辑器粘贴；图片仍需在微信编辑器内上传或托管到可访问地址。")


@wechat.command("theme-list")
def list_wechat_theme_cmd():
    """列出公众号模板主题"""
    table = Table(title="公众号模板主题")
    table.add_column("Key", style="cyan")
    table.add_column("名称", style="green")
    table.add_column("说明")
    table.add_column("强调色")
    for item in list_wechat_themes():
        table.add_row(item["key"], item["name"], item["description"], item["accent"])
    console.print(table)


# ========== 模板管理命令 ==========

@cli.group()
def template():
    """模板管理"""
    pass


@template.command('list')
def list_templates():
    """列出所有已安装模板"""
    from src.templates import TemplateRegistry

    registry = TemplateRegistry()
    templates = registry.list_templates()

    if not templates:
        console.print("[yellow]没有找到模板。请在 templates/ 目录下创建 manifest.yaml[/yellow]")
        return

    table = Table(title="已安装模板")
    table.add_column("ID", style="cyan")
    table.add_column("名称", style="green")
    table.add_column("版本")
    table.add_column("字段数")
    table.add_column("主题数")
    table.add_column("渲染器")
    table.add_column("标签")

    for t in templates:
        table.add_row(
            t["id"],
            t["name"],
            t["version"],
            str(t["field_count"]),
            str(t["theme_count"]),
            t["renderer"],
            ", ".join(t["tags"]) if t["tags"] else "-",
        )

    console.print(table)
    console.print(f"\n共 [bold]{len(templates)}[/bold] 个模板")


@template.command('inspect')
@click.argument('template_id')
def inspect_template(template_id):
    """查看模板详情"""
    from src.templates import TemplateRegistry

    registry = TemplateRegistry()
    detail = registry.inspect_template(template_id)

    if not detail:
        console.print(f"[red]✗[/red] 未找到模板：{template_id}")
        return

    # 基本信息
    console.print(Panel(f"[bold]模板: {detail['name']}[/bold] (ID: {detail['id']})", style="blue"))
    console.print(f"  版本：{detail['version']}")
    console.print(f"  作者：{detail['author']}")
    console.print(f"  渲染器：{detail['renderer']}")
    console.print(f"  标签：{', '.join(detail['tags']) if detail['tags'] else '-'}")

    # 字段列表
    if detail["fields"]:
        field_table = Table(title="字段定义")
        field_table.add_column("Key", style="cyan")
        field_table.add_column("类型")
        field_table.add_column("标签", style="green")
        field_table.add_column("必填")
        field_table.add_column("默认值")
        for f in detail["fields"]:
            field_table.add_row(
                f["key"],
                f.get("type", "string"),
                f.get("label", ""),
                "是" if f.get("required") else "否",
                str(f.get("default", "")) if f.get("default") is not None else "-",
            )
        console.print(field_table)

    # 主题列表
    if detail["themes"]:
        theme_table = Table(title="主题列表")
        theme_table.add_column("ID", style="cyan")
        theme_table.add_column("名称", style="green")
        theme_table.add_column("说明")
        theme_table.add_column("Token 数")
        for t in detail["themes"]:
            theme_table.add_row(
                t["id"],
                t["name"],
                t.get("description", ""),
                str(t.get("token_count", 0)),
            )
        console.print(theme_table)


@template.command('render')
@click.argument('template_id')
@click.option('--theme', '-t', default=None, help='主题 ID')
@click.option('--output-dir', '-o', default='data/reports', help='输出目录')
@click.option('--field', '-f', multiple=True, help='字段值 (格式：key=value)')
def render_template_cmd(template_id, theme, output_dir, field):
    """渲染模板"""
    from src.templates import TemplateRegistry

    # 解析字段
    input_data = {}
    for f in field:
        if "=" in f:
            key, value = f.split("=", 1)
            input_data[key] = value

    if not input_data:
        console.print("[yellow]请提供至少一个字段值 (--field key=value)[/yellow]")
        return

    try:
        registry = TemplateRegistry()
        result = registry.render_template(
            template_id,
            input_data,
            theme_id=theme,
            output_dir=Path(output_dir),
        )

        console.print(f"[green]✓[/green] 模板渲染完成：{template_id}")
        if isinstance(result, dict):
            for key, value in result.items():
                console.print(f"  [cyan]{key}[/]: {value}")
        else:
            console.print(str(result))

    except ValueError as e:
        console.print(f"[red]✗[/red] 渲染失败：{e}")
    except Exception as e:
        console.print(f"[red]✗[/red] 渲染异常：{e}")


@template.command('preview')
@click.argument('template_id')
@click.option('--theme', '-t', default=None, help='主题 ID')
@click.option('--field', '-f', multiple=True, help='字段值 (格式：key=value)')
def preview_template(template_id, theme, field):
    """预览模板（dry-run，显示字段要求和验证结果）"""
    from src.templates import TemplateRegistry

    registry = TemplateRegistry()
    manifest = registry.get_template(template_id)

    if not manifest:
        console.print(f"[red]✗[/red] 未找到模板：{template_id}")
        return

    console.print(Panel(f"[bold]预览模板: {manifest.name}[/bold] (ID: {manifest.id})", style="green"))

    # 显示所需字段
    console.print("\n[bold]必填字段:[/bold]")
    has_required = False
    for f in manifest.fields:
        if f.required:
            has_required = True
            desc = f"  [cyan]{f.key}[/] ({f.label})"
            if f.type:
                desc += f" [{f.type}]"
            if f.default is not None:
                desc += f" 默认: {f.default}"
            if f.description:
                desc += f"\n    {f.description}"
            console.print(desc)
    if not has_required:
        console.print("  (无必填字段)")

    console.print("\n[bold]可选字段:[/bold]")
    for f in manifest.fields:
        if not f.required:
            desc = f"  [dim]{f.key}[/] ({f.label})"
            if f.type:
                desc += f" [{f.type}]"
            if f.default is not None:
                desc += f" 默认: {f.default}"
            console.print(desc)

    # 显示输出
    console.print("\n[bold]将生成:[/bold]")
    for slot in manifest.slots:
        console.print(f"  [green]{slot.label}[/] ({', '.join(slot.formats)})")

    # 如果提供了字段，做验证
    if field:
        input_data = {}
        for f in field:
            if "=" in f:
                key, value = f.split("=", 1)
                input_data[key] = value

        errors = manifest.validate_fields(input_data)
        if errors:
            console.print("\n[red]✗ 验证失败:[/red]")
            for err in errors:
                console.print(f"  [red]- {err}[/]")
        else:
            console.print("\n[green]✓ 字段验证通过[/green]")


# ========== 主程序 ==========

if __name__ == '__main__':
    cli()
