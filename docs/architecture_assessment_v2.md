# Skills 项目架构重构蓝图与全维度评估报告

**版本**: v2.0 (Workflow Engine Edition)  
**日期**: 2023-10-27  
**状态**: 架构重构规划中  

---

## 第一部分：战略定位与核心理念升级

### 1.1 愿景重新定义
*   **旧定位**: 个人技能成长记录与日报工具。
*   **新定位**: **基于技能原子的个人智能工作流操作系统 (Skill-Based Personal Workflow OS)**。
*   **核心价值**: 将“技能”从静态标签转化为动态的“能力原子”，通过“工作流引擎”将原子组合成解决具体问题的“能力链”，实现从“记录成长”到“赋能产出”的闭环。

### 1.2 核心概念模型升级
为了支持多工作流和组合工作流，数据模型需从扁平化转向图谱化：

1.  **技能原子 (Skill Atom)**: 
    *   最小能力单元，具备输入/输出定义、触发条件、执行上下文。
    *   *例*: `Python-DataAnalysis` 不仅是标签，它包含工具集 (Pandas)、常用脚本库、关联文档。
2.  **工作流 (Workflow)**: 
    *   有向无环图 (DAG)，由多个技能原子串联或并联组成。
    *   *类型*: 单一工作流 (如：日报生成)、复合工作流 (如：全栈开发流程 = 需求分析 + 编码 + 测试 + 部署)。
3.  **上下文 (Context)**: 
    *   工作流运行时的状态容器，携带数据在不同技能节点间流转。
4.  **触发器 (Trigger)**: 
    *   时间、事件、API 调用、手动指令等多模态启动方式。

---

## 第二部分：全新架构设计 (Target Architecture)

### 2.1 总体架构图 (逻辑视图)

```mermaid
graph TD
    User[用户] --> Interface[交互层 (CLI/Web/API)]
    Interface --> WorkflowEngine[核心：工作流引擎]
    
    subgraph "核心引擎层"
        WorkflowEngine --> Scheduler[调度器]
        WorkflowEngine --> Executor[执行器]
        WorkflowEngine --> ContextMgr[上下文管理器]
        WorkflowEngine --> RuleEngine[规则/组合逻辑引擎]
    end
    
    subgraph "能力资源层"
        SkillGraph[(技能知识图谱)]
        WorkflowRepo[工作流仓库]
        TemplateLib[模板库]
    end
    
    subgraph "数据持久层"
        DB[(SQLite/PostgreSQL)]
        VectorDB[(向量数据库 - 用于 AI 检索)]
        FileSystem[文件/日志存储]
    end
    
    WorkflowEngine <--> SkillGraph
    WorkflowEngine <--> WorkflowRepo
    Executor <--> DB
    Executor <--> VectorDB
```

### 2.2 模块详细设计

#### A. 技能图谱模块 (Skill Graph Module)
*   **功能**: 管理技能的层级、依赖关系、关联资源。
*   **升级点**: 
    *   支持技能依赖检测 (学习 B 前需掌握 A)。
    *   技能绑定具体“动作” (Action)，如：`Git-Commit` 技能绑定具体的 shell 命令或 API。

#### B. 工作流引擎 (Workflow Engine) - **核心新增**
*   **定义语言**: 采用 YAML/JSON 定义工作流 (类似 GitHub Actions 或 LangChain)。
*   **执行模式**:
    *   **串行**: 步骤 A -> 步骤 B -> 步骤 C。
    *   **并行**: 同时执行数据分析与文档撰写。
    *   **条件分支**: 如果 测试失败 -> 触发 修复工作流。
*   **组合工作流**: 支持子工作流嵌套，例如 `Morning-Routine` 工作流内部调用 `News-Summary` 和 `Plan-Generator` 两个子工作流。

#### C. 交互适配层 (Interface Adapter)
*   **CLI**: 保持高效，增加 `run-workflow` 命令。
*   **Web Dashboard**: 可视化工作流编排画布 (Drag & Drop)。
*   **API Server**: 允许外部系统 (如 IDE 插件、CI/CD) 调用工作流。

#### D. 智能增强层 (AI Copilot)
*   **工作流推荐**: 根据当前任务自动推荐技能组合。
*   **自动填充**: 利用 LLM 自动填写日报中的“心得”和“问题”。
*   **异常处理**: 工作流执行失败时，AI 分析原因并建议修复方案。

---

## 第三部分：全维度评估报告 (Current State Audit)

基于当前 v1.0 代码状态，对照 v2.0 目标进行严格评估。

| 评估维度 | 评分 (1-10) | 现状分析 | 缺陷与风险 | 改进建议 |
| :--- | :---: | :--- | :--- | :--- |
| **1. 产品业务功能完整度** | 4 | 仅覆盖“记录”场景，缺乏“执行”和“编排”能力。 | 缺失工作流定义、任务调度、技能组合逻辑。无法支撑“组合工作流”需求。 | **高优先级**: 引入工作流定义格式 (YAML)，开发引擎解析器。 |
| **2. 交互合理性** | 6 | CLI 交互线性，适合简单录入，不适合复杂流程配置。 | 配置复杂工作流时 CLI 参数过长，体验极差；缺乏可视化反馈。 | 保留 CLI 做执行端，开发 Web 端做配置端；引入交互式 TUI (如 Rich library)。 |
| **3. 功能实现合理性** | 5 | 硬编码逻辑较多，扩展性差。 | `DailyReportManager` 耦合了具体业务逻辑，难以复用到其他工作流。 | **重构**: 抽取 `BaseNode` 基类，所有功能模块化插件化。 |
| **4. 逻辑合理性** | 6 | 数据流向单一 (输入->存储)，缺乏流转逻辑。 | 缺乏状态机管理，无法处理异步任务或长流程中断/恢复。 | 引入有限状态机 (FSM) 管理工作流生命周期。 |
| **5. 技术实现合理性** | 5 | 单体脚本结构，难以支撑并发和复杂依赖。 | 缺乏依赖注入，全局变量使用，测试困难。 | 采用分层架构 (Controller-Service-Repository)，引入依赖注入容器。 |
| **6. 准确性** | 7 | 基础 CRUD 准确，但统计逻辑简单。 | 缺乏数据校验机制，脏数据可能破坏工作流执行。 | 引入 Pydantic 进行严格的数据模型验证。 |
| **7. 可落地情况** | 8 | 当前 MVP 可运行，但新架构跨度大。 | 工作流引擎开发成本高，需分阶段迭代。 | **分阶段**: P1 实现 YAML 解析+串行执行; P2 实现并行+条件; P3 可视化。 |
| **8. 实际实现情况** | 3 | 目前仅实现了“日报”一个孤立场景。 | 距离“操作系统”级别的目标差距巨大。 | 制定明确的 Milestone，先打通一个“组合工作流”Demo。 |
| **9. 闭环情况** | 4 | 只有“记录”闭环，缺乏“行动->反馈->优化”闭环。 | 技能提升未反哺工作流优化，工作流执行结果未量化技能成长。 | 建立反馈回路：工作流执行效率作为技能熟练度的量化指标。 |
| **10. 缺陷问题** | - | - | 1. 强耦合<br>2. 无并发支持<br>3. 无撤销/重做<br>4. 无权限/多租户预留 | 逐步重构，优先解耦数据层与业务层。 |
| **11. 代码质量** | 5 | 功能可用，但缺乏设计模式应用。 | 缺少单元测试，异常处理粗糙，日志不规范。 | 引入 `pytest` 全覆盖，规范 Logging，应用 Strategy/Factory 模式。 |
| **12. 扩展性** | 3 | 新增技能类型需修改核心代码。 | 违反开闭原则 (OCP)，不支持动态加载插件。 | 设计插件系统，支持通过配置文件或独立 Python 文件动态加载新技能节点。 |

---

## 第四部分：实施路线图 (Roadmap to v2.0)

### 阶段一：内核重构 (Core Refactoring) - [预计 2 周]
*   **目标**: 解耦现有代码，建立插件化架构。
*   **任务**:
    1.  引入 `Pydantic` 重构数据模型，确保类型安全。
    2.  设计 `SkillNode` 抽象基类，将现有的日报功能改造为第一个 `DailyReportNode` 插件。
    3.  实现简单的 `WorkflowRunner`，支持按顺序执行多个 Node。
    4.  定义 `workflow.yaml` 标准格式。

### 阶段二：工作流引擎成型 (Engine MVP) - [预计 3 周]
*   **目标**: 支持组合工作流和条件分支。
*   **任务**:
    1.  实现 DAG (有向无环图) 解析器，检测循环依赖。
    2.  开发上下文管理器 (`ContextManager`)，实现节点间数据传递。
    3.  实现条件分支逻辑 (`If/Else` 节点)。
    4.  新增技能类型：`CommandSkill` (执行 Shell), `APISkill` (调用接口)。

### 阶段三：交互与生态 (Interaction & Ecosystem) - [预计 3 周]
*   **目标**: 提升易用性，支持多场景。
*   **任务**:
    1.  开发 TUI (文本图形界面) 用于监控工作流运行状态。
    2.  构建“工作流市场”原型，允许导入/导出工作流配置。
    3.  集成 AI 模块，实现自然语言创建工作流 (`"创建一个周报生成工作流"`).

### 阶段四：可视化与云同步 (Web & Sync) - [未来规划]
*   **目标**: Web 编排画布，多端同步。
*   **任务**: ReactFlow 前端画布，后端 API 服务，云端数据库同步。

---

## 第五部分：示例：未来的工作流定义 (workflow.yaml)

为了让您直观感受架构升级后的能力，这是一个**“每日研发效能复盘”**组合工作流的定义示例：

```yaml
name: daily-dev-review
version: 1.0
description: 自动拉取 Git 提交，分析代码量，结合人工心得，生成日报并推送到 Notion
trigger:
  cron: "0 20 * * *" # 每晚 8 点
  manual: true

context:
  date: "{{ today }}"
  git_stats: null
  user_insight: null

nodes:
  - id: fetch_git_log
    type: command_skill
    skill: git-analysis
    params:
      since: "24 hours ago"
    output: git_stats

  - id: collect_mood
    type: input_skill
    skill: mood-tracker
    prompt: "今天心情如何？(1-5)"
    output: mood_score

  - id: generate_content
    type: ai_skill
    skill: report-generator
    inputs:
      stats: "{{ nodes.fetch_git_log.output }}"
      mood: "{{ nodes.collect_mood.output }}"
    prompt: "根据提交记录和心情，生成一份专业的日报，突出技术难点。"
    output: draft_report

  - id: conditional_notify
    type: condition
    condition: "{{ nodes.collect_mood.output }} < 3"
    true_branch:
      - id: send_alert
        type: notification_skill
        skill: slack-notify
        message: "检测到开发者心情低落，请 Team Leader 关注。"
    
  - id: save_to_notion
    type: api_skill
    skill: notion-writer
    inputs:
      content: "{{ nodes.generate_content.output }}"
    depends_on: [fetch_git_log, collect_mood]

on_success:
  - action: log
    message: "工作流执行成功，日报已发送。"
on_failure:
  - action: rollback
  - action: notify
    channel: email
```

---

## 第六部分：总结与建议

当前项目处于 **MVP 验证期**，核心痛点是**架构刚性**，无法支撑您提出的“多工作流组合”和“技能动态编排”的宏伟目标。

**立即行动建议**:
1.  **暂停新功能堆砌**: 暂时不要添加新的独立命令。
2.  **启动重构**: 按照“阶段一”计划，将现有的 `DailyReportManager` 改造为第一个符合新标准的 `Plugin`。
3.  **定义标准**: 确定 `workflow.yaml` 的 Schema，这是未来生态的基石。

这个项目有潜力成为个人的“第二大脑”执行层，架构的灵活性将决定其上限。我们现在的方向是从“记账本”转向“自动化流水线”。
