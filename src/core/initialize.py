"""
Skills 项目初始化模块
"""
import json
from pathlib import Path


def initialize_project():
    """初始化项目结构"""
    print("🚀 初始化 Skills 项目...")
    
    # 创建必要的目录
    directories = [
        "data/skills",
        "data/logs",
        "data/reports",
        "docs/api",
        "docs/guides",
        "tests",
        "config"
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✅ 创建目录：{dir_path}")
    
    # 创建示例技能数据（v2 格式）
    from src.core.models import Skill, SkillLevel, SkillCategory

    sample_skills = [
        Skill(
            name="Python",
            level=SkillLevel.ADVANCED,
            category=SkillCategory.TECHNICAL,
            description="主要编程语言",
            tags=["backend", "automation", "data"]
        ),
        Skill(
            name="JavaScript",
            level=SkillLevel.INTERMEDIATE,
            category=SkillCategory.TECHNICAL,
            description="前端开发",
            tags=["frontend", "web"]
        )
    ]

    from src.storage.base import StorageManager
    storage = StorageManager()
    existing = storage.skill_storage().get_all()
    existing_names = {s.name for s in existing}

    for skill in sample_skills:
        if skill.name not in existing_names:
            storage.skill_storage().save(skill)
            print(f"✅ 创建示例技能：{skill.name}")
    
    # 创建配置文件
    config = {
        "project_name": "skills",
        "version": "1.0.0",
        "default_data_dir": "data",
        "date_format": "%Y-%m-%d",
        "timezone": "Asia/Shanghai"
    }
    
    config_file = Path("config/settings.json")
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print("✅ 创建配置文件")
    
    # 创建 .gitignore
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Data
data/*.json
data/logs/*.json
data/reports/*.md

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
"""
    
    gitignore_file = Path(".gitignore")
    if not gitignore_file.exists():
        with open(gitignore_file, 'w', encoding='utf-8') as f:
            f.write(gitignore_content)
        print("✅ 创建 .gitignore")
    
    print("\n✨ 项目初始化完成！")
    print("\n📝 快速开始:")
    print("  1. 添加技能：python -m skills.cli add-skill <技能名>")
    print("  2. 记录日报：python -m skills.cli add-learning <技能名> <时长> <内容>")
    print("  3. 查看帮助：python -m skills.cli --help")


if __name__ == "__main__":
    initialize_project()
