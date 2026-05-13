# 📚 Skills - 个人技能管理与日报系统

> 鸿枫的 skills 集合体 - 记录成长，追踪进步

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com)
[![Python](https://img.shields.io/badge/python-3.9+-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)](https://opensource.org/licenses/MIT)

---

## 🌟 项目简介

Skills 是一个个人技能管理与日报系统，帮助你：
- 📋 **系统化管理** 个人技能树
- 📝 **每日记录** 学习内容与心得
- 📊 **可视化追踪** 成长轨迹
- 💡 **知识沉淀** 形成可复用的知识库

---

## 🚀 快速开始

### 1. 初始化项目

```bash
cd /workspace
python -m src.core.initialize
```

### 2. 使用 CLI 工具

#### 查看帮助
```bash
python -m src.cli --help
```

#### 管理技能
```bash
# 添加新技能
python -m src.cli add-skill "Python" -c technical -l 3 -d "主要编程语言" -t "backend,automation"

# 列出所有技能
python -m src.cli list-skills

# 按分类筛选
python -m src.cli list-skills -c technical

# 查看统计
python -m src.cli stats

# 导出技能清单
python -m src.cli export-skills -o skills.md
```

#### 记录日报
```bash
# 添加学习记录
python -m src.cli add-learning "Python" 2.0 "学习装饰器" -n "理解了@语法糖"

# 添加心得
python -m src.cli add-insight "装饰器本质是 higher-order function"

# 记录问题
python -m src.cli add-problem "装饰器参数传递" -s "使用 functools.wraps"

# 添加明日计划
python -m src.cli add-plan "学习生成器和迭代器"

# 设置心情
python -m src.cli set-mood 5

# 查看今日日报
python -m src.cli today

# 导出日报
python -m src.cli export-report -d 2026-05-13
```

#### 周期统计
```bash
# 查看周期统计
python -m src.cli period-stats --start 2026-01-01 --end 2026-12-31

# 导出周期报告
python -m src.cli export-report -p 2026-01-01:2026-01-31 -o january_report.md
```

---

## 📁 项目结构

```
skills/
├── README.md              # 项目说明
├── docs/
│   └── blueprint.md       # 蓝图规划
├── src/
│   ├── __init__.py
│   ├── cli.py             # 命令行工具
│   ├── core/
│   │   ├── skill_manager.py   # 技能管理
│   │   ├── daily_report.py    # 日报系统
│   │   └── initialize.py      # 初始化
│   └── models/
│       ├── skill.py           # 技能模型
│       └── daily_log.py       # 日志模型
├── data/
│   ├── skills/            # 技能数据
│   ├── logs/              # 日志数据
│   └── reports/           # 报告输出
├── config/
│   └── settings.json      # 配置文件
└── requirements.txt       # 依赖管理
```

---

## 🛠️ 命令参考

| 命令 | 说明 | 示例 |
|------|------|------|
| `add-skill` | 添加新技能 | `add-skill "JS" -c technical -l 2` |
| `list-skills` | 列出技能 | `list-skills -c technical` |
| `stats` | 技能统计 | `stats` |
| `export-skills` | 导出技能清单 | `export-skills -o skills.md` |
| `add-learning` | 添加学习记录 | `add-learning "Python" 1.5 "内容"` |
| `add-insight` | 添加心得 | `add-insight "心得体会"` |
| `add-problem` | 记录问题 | `add-problem "问题" -s "解决"` |
| `add-plan` | 添加计划 | `add-plan "明日计划"` |
| `set-mood` | 设置心情 | `set-mood 4` |
| `today` | 查看今日日报 | `today` |
| `period-stats` | 周期统计 | `period-stats --start 2026-01-01` |
| `export-report` | 导出报告 | `export-report -d 2026-05-13` |

---

## 📊 日报模板示例

```markdown
# 日报 - 2026-05-13

## 📚 今日学习
- **深度学习** | 2.0h | 学习反向传播算法
  - _理解了梯度下降的原理_

## 💡 收获与心得
- 反向传播是神经网络训练的核心

## 🐛 遇到的问题
- **问题**: 梯度消失问题
  - **解决**: 使用 ReLU 激活函数

## 📝 明日计划
- [ ] 学习卷积神经网络 CNN

## 📊 今日统计
- 总学习时长：2.0 小时
- 涉及技能：1 个
- 心情指数：⭐⭐⭐⭐⭐
```

---

## 🔧 配置说明

配置文件位于 `config/settings.json`:

```json
{
  "project_name": "skills",
  "version": "1.0.0",
  "default_data_dir": "data",
  "date_format": "%Y-%m-%d",
  "timezone": "Asia/Shanghai"
}
```

---

## 📈 开发路线图

- ✅ **v1.0** - 基础功能 (CLI + 数据存储)
- 🔄 **v1.1** - 数据可视化 (图表生成)
- 📅 **v2.0** - Web 界面 (FastAPI + Vue)
- 📅 **v2.5** - AI 辅助建议
- 📅 **v3.0** - 多端同步

详细规划请查看 [蓝图文档](docs/blueprint.md)

---

## 🤝 贡献指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: add AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

MIT License

---

*Made with ❤️ by 鸿枫*
