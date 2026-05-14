# 日报渲染指南

本文说明 Skills Platform 当前的日报渲染工作流、主题预览命令以及面向公众号/H5 的产物差异。

## 目标

同一份日报数据，输出两类发布形式：

1. 图片版日报：适合公众号正文、封面图、社交平台分发
2. 交互版日报：适合 H5、知识库、官网文章页、原文跳转页

## CLI 命令

### 1. 生成单主题日报

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

### 2. 批量预览全部主题

```bash
python -m src.cli.main daily theme list --date 2026-05-13
```

该命令会同时做三件事：

- 在终端列出主题信息
- 为每个主题生成完整日报产物
- 输出一个汇总预览页 `daily-<date>-theme-gallery.html`

## 输出文件说明

单次 `daily render` 会产出以下文件：

- `daily-<date>-<theme>-poster.png`
  - 公众号正文优先用这个
  - 适合发图、做封面、朋友圈长图
- `daily-<date>-<theme>-poster.svg`
  - 矢量版海报
  - 适合继续编辑或高清导出
- `daily-<date>-<theme>-poster.html`
  - 截图底板
  - 浏览器直接打开即可截图
- `daily-<date>-<theme>-widget.html`
  - 交互组件
  - 适合外链页、H5、知识库嵌入
- `daily-<date>-<theme>-article.html`
  - 成稿型文章嵌入页
  - 适合“阅读原文”或官网文章承接

## 截图方式

如果目标平台只接受图片，不要截 `widget.html`，优先用：

1. `poster.png` 直接发
2. 或打开 `poster.html` 在浏览器里截图

`poster.html` 的意义是：

- 按截图场景重新排过版
- 有完整标题、日期、作者、来源、来源声明
- 不依赖交互状态

## 主题体系

当前内置两套主题：

### `maple-ai`

- 定位：AI 科技日报
- 用途：工作流复盘、技术推进、自动化日报
- 视觉重点：信号密度、指标块、行动导向

### `maple-editorial`

- 定位：品牌专栏日报
- 用途：内容栏目、周报摘要、文章头图
- 视觉重点：出版层级、留白、成稿感

### 品牌色

- 枫叶红：`#B63A2B`
- 秋金黄：`#D89B1D`
- 自然绿：`#557C3E`

## 用户可输入字段

渲染层当前支持以下输入：

- `date`
- `theme`
- `title`
- `description`
- `author`
- `source_name`
- `source_statement`
- `user_note`

这些字段会被注入到海报、截图底板、交互组件和文章页中。

## 平台适配建议

### 公众号正文

建议放：

- `poster.png`

不建议直接放：

- `widget.html`

原因很直接：公众号正文不是通用前端运行容器，自定义脚本承载能力有限，稳定性也不够。

### H5 / 官网 / 知识库

建议放：

- `widget.html`
- `article.html`

适合需要更强信息层级和交互承接的场景。

## 开发落点

相关实现文件：

- 渲染器：[F:\project\skills\src\reports\daily_renderer.py](F:/project/skills/src/reports/daily_renderer.py)
- CLI 入口：[F:\project\skills\src\cli\main.py](F:/project/skills/src/cli/main.py)
- 测试：[F:\project\skills\tests\unit\test_daily_renderer.py](F:/project/skills/tests/unit/test_daily_renderer.py)

## 验证

建议至少跑这两组：

```bash
python -m pytest tests/unit/test_daily_renderer.py -q
python -m src.cli.main daily theme list --date 2026-05-13
```

如果你后面继续扩展主题或补“长图版公众号正文模板”，这里是应该先更新的文档入口。*** End Patch
