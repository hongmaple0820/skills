# Skills Platform v2.0

个人技能管理与工作流系统。当前代码库已经从早期的日报记录工具，演进为一套以 `Pydantic` 模型、`StorageManager` 存储层和 YAML 工作流执行引擎为核心的本地工作流平台。

## 当前能力

- 技能管理：新增、查询、统计、删除技能
- 日报记录：手工录入、按日查看
- 工作流执行：加载 YAML、执行顺序/并行/条件节点
- 模型迁移：v1 legacy dataclass -> v2 Pydantic
- 日报渲染：输出海报、截图底板、交互组件、文章页
- 主题预览：一条命令批量预览全部日报主题

## 目录结构

```text
skills/
├── src/
│   ├── cli/               # CLI 入口
│   ├── core/              # v2 核心模型与业务层
│   ├── reports/           # 日报渲染与主题系统
│   ├── storage/           # JSON / SQLite 存储
│   ├── workflows/         # 工作流解析与执行引擎
│   └── nodes/             # 内置工作流节点
├── scripts/               # 迁移与校验脚本
├── docs/                  # 架构与使用文档
├── data/                  # 本地数据与渲染输出
└── tests/                 # 单元测试
```

## 安装

```bash
pip install -r requirements.txt
```

## 快速开始

初始化或查看 CLI：

```bash
python -m src.cli.main --help
python src\cli.py --help
```

运行测试：

```bash
python -m pytest tests -q
```

## 常用命令

技能管理：

```bash
python -m src.cli.main skill add -n "Python" -l 3 -c technical -t backend
python -m src.cli.main skill list
python -m src.cli.main skill stats
```

工作流：

```bash
python -m src.cli.main workflow load data/workflows/daily-review.yaml
python -m src.cli.main workflow list
python -m src.cli.main workflow run <workflow-id> -v key=value
```

日报：

```bash
python -m src.cli.main daily add ^
  --skill "LLM Workflow" ^
  --content "优化日报工作流渲染器" ^
  --duration 90 ^
  --insight "统一渲染模型和主题体系" ^
  --problem "公众号正文无法直接执行自定义脚本" ^
  --plan "补长图模板" ^
  --mood 4

python -m src.cli.main daily today
```

## 日报渲染

生成单主题日报：

```bash
python -m src.cli.main daily render ^
  --date 2026-05-13 ^
  --theme maple-ai ^
  --title "AI 科技日报" ^
  --description "聚焦 AI 技术推进、工作流执行与次日动作的高密度日报卡片。" ^
  --author "Codex" ^
  --source-name "Skills Platform" ^
  --source-statement "数据来自 Skills Platform 当日工作流与日报记录，仅用于复盘与发布。" ^
  --user-note "枫叶红 / 秋金黄 / 自然绿品牌体系"
```

当前会输出：

- `poster.png`：适合公众号正文直接发图
- `poster.svg`：高清海报源文件
- `poster.html`：截图底板
- `widget.html`：交互版组件
- `article.html`：文章嵌入页

批量预览全部主题：

```bash
python -m src.cli.main daily theme list --date 2026-05-13
```

该命令会：

- 在终端列出主题 `key / 名称 / 说明 / 品牌色`
- 自动生成主题预览页 `data/reports/daily-<date>-theme-gallery.html`

## 主题体系

当前内置主题：

- `maple-ai`：AI 科技，强调信号密度、工作流推进和复盘节奏
- `maple-editorial`：品牌专栏，强调更接近内容成稿的出版感

品牌色体系：

- 枫叶红 `#B63A2B`
- 秋金黄 `#D89B1D`
- 自然绿 `#557C3E`

## 模型与迁移

项目目前同时保留两套模型：

- `src/models/`：v1 legacy dataclass，仅用于旧数据来源
- `src/core/models.py`：v2 当前标准模型，所有新代码应统一使用

迁移与校验脚本：

```bash
python scripts/migrate_v1_to_v2.py --dry
python scripts/verify_models.py
```

详细说明见：

- [模型架构说明](F:/project/skills/docs/architecture/model-architecture.md)
- [日报渲染指南](F:/project/skills/docs/daily-report-rendering.md)

## 当前约束

- 公众号正文不适合直接承载自定义前端脚本
- 交互版日报更适合 H5、知识库、官网文章页或原文跳转页
- `data/reports/` 下的渲染产物是生成物，不建议作为源码提交

## 开发说明

- 代码编辑优先使用 `src/core/models.py` 里的 v2 模型
- `src/core`、`src/workflows`、`src/nodes` 不应直接依赖 legacy v1 模型
- 测试覆盖重点在模型迁移、工作流执行语义、日报渲染输出

## 相关文档

- [架构评估](F:/project/skills/docs/architecture_assessment_v2.md)
- [实施计划](F:/project/skills/docs/implementation_plan_v2.md)
- [模型架构](F:/project/skills/docs/architecture/model-architecture.md)
- [日报渲染指南](F:/project/skills/docs/daily-report-rendering.md)
