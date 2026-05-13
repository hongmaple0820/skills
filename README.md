# Skills Platform v2.0 🚀

> 个人工作流操作系统 - 从日报工具到自动化工作流引擎

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📖 项目简介

Skills Platform 是一个强大的个人技能管理与工作流自动化平台。v2.0 版本实现了从简单日报工具到完整工作流操作系统的升级，支持：

- **原子化技能管理** - 将技能定义为可执行的能力单元
- **YAML 工作流编排** - 类似 GitHub Actions 的声明式工作流定义
- **DAG 执行引擎** - 支持串行/并行/条件分支/子工作流嵌套
- **上下文传递** - 节点间数据流动 (`{{ nodes.xxx.output }}`)
- **插件系统** - 动态加载技能节点，无需修改框架

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI / Web UI                            │
├─────────────────────────────────────────────────────────────┤
│                       Workflow Engine                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Sequential│  │ Parallel │  │ Decision │  │  Custom  │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
├─────────────────────────────────────────────────────────────┤
│                    Built-in Skill Nodes                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │DailyReport│  │CodeAnalysis│ │GitStats │  │  ...     │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
├─────────────────────────────────────────────────────────────┤
│                     Storage Layer                            │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │   JSON Files     │  │    SQLite (opt)  │                 │
│  └──────────────────┘  └──────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 安装依赖

```bash
pip install pydantic pyyaml rich click networkx jinja2 pytest
```

### 基本使用

#### 1. 技能管理

```bash
# 添加技能
PYTHONPATH=/workspace python src/cli/main.py skill add -n "Python" -l 3 -c technical -t backend

# 查看技能列表
PYTHONPATH=/workspace python src/cli/main.py skill list

# 技能统计
PYTHONPATH=/workspace python src/cli/main.py skill stats
```

#### 2. 工作流管理

```bash
# 加载 YAML 工作流
PYTHONPATH=/workspace python src/cli/main.py workflow load data/workflows/daily-review.yaml

# 查看工作流
PYTHONPATH=/workspace python src/cli/main.py workflow list

# 执行工作流
PYTHONPATH=/workspace python src/cli/main.py workflow run <workflow-id> -v key=value
```

#### 3. 日报管理

```bash
# 手动添加日报
PYTHONPATH=/workspace python src/cli/main.py daily add \
  -s "Python" \
  -c "学习了 Pydantic" \
  -d 60 \
  -i "心得 1" \
  -p "问题 1" \
  -P "明天计划" \
  -m 4

# 查看今日日报
PYTHONPATH=/workspace python src/cli/main.py daily today
```

## 📁 项目结构

```
/workspace
├── src/
│   ├── core/           # 核心模型
│   │   └── models.py   # Skill, Workflow, ExecutionContext 等
│   ├── storage/        # 存储层
│   │   └── base.py     # JSON/SQLite 存储实现
│   ├── workflows/      # 工作流引擎
│   │   ├── engine.py   # DAG 执行引擎
│   │   └── parser.py   # YAML 解析器
│   ├── nodes/          # 技能节点
│   │   └── builtin.py  # 内置节点（日报、代码分析、Git 统计）
│   └── cli/            # 命令行界面
│       └── main.py     # CLI 入口
├── data/
│   ├── schemas/        # JSON Schema
│   │   └── workflow.json
│   ├── workflows/      # YAML 工作流定义
│   │   └── daily-review.yaml
│   └── *.json          # 数据存储文件
├── tests/
│   ├── unit/           # 单元测试
│   └── integration/    # 集成测试
└── docs/               # 文档
    ├── blueprint.md
    ├── architecture_assessment_v2.md
    └── implementation_plan_v2.md
```

## 🔧 自定义工作流

创建 `my-workflow.yaml`:

```yaml
name: "My Custom Workflow"
description: "自定义工作流示例"
version: "1.0.0"
entry_point: "start"

variables:
  my_var: "hello"

nodes:
  start:
    name: "开始"
    type: sequential
    children:
      - node1
      - node2

  node1:
    name: "自定义节点"
    type: custom
    metadata:
      handler: daily_report
    inputs:
      skill_name: "My Skill"
      learning_content: "学习内容"
      duration_minutes: 30
      mood: 4

  node2:
    name: "条件节点"
    type: decision
    condition: "{{ nodes.node1.output.success }}"
    metadata:
      branches:
        success: "true"
        fail: "false"
```

## 🧪 运行测试

```bash
PYTHONPATH=/workspace pytest tests/ -v
```

## 📊 功能对比

| 功能 | v1.0 | v2.0 |
|------|------|------|
| 技能管理 | ✅ | ✅ |
| 日报记录 | ✅ | ✅ |
| 工作流引擎 | ❌ | ✅ |
| YAML 编排 | ❌ | ✅ |
| 并行执行 | ❌ | ✅ |
| 条件分支 | ❌ | ✅ |
| 子工作流 | ❌ | ✅ |
| 插件系统 | ❌ | ✅ |
| 上下文传递 | ❌ | ✅ |

## 🎯 路线图

- [ ] v2.1: Web 可视化编排界面
- [ ] v2.2: AI 辅助创建工作流
- [ ] v2.3: 定时任务调度器
- [ ] v2.4: 团队协作功能
- [ ] v2.5: 云同步服务

## 📝 License

MIT License

---

**Built with ❤️ using Python & Pydantic**
