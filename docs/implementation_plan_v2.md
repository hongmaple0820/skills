# Skills 项目 v2.0 重构实施计划

**目标**: 从单体日报工具转型为基于技能原子的工作流引擎  
**周期**: 8 周  
**状态**: 待启动  

---

## 第一阶段：核心架构重构 (Week 1-2)

### 1.1 数据模型升级 - 引入 Pydantic

**问题**: 当前使用 dataclass，缺乏严格验证和序列化能力

**实施方案**:

#### 1.1.1 安装依赖
```bash
pip install pydantic pyyaml networkx
```

#### 1.1.2 重构技能模型 (`src/models/skill.py`)

```python
# 新代码结构示例
from pydantic import BaseModel, Field, validator
from enum import Enum
from datetime import datetime
from typing import List, Optional, Dict, Any

class SkillLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    MASTER = "master"

class SkillCategory(str, Enum):
    TECHNICAL = "technical"
    SOFT_SKILL = "soft_skill"
    LANGUAGE = "language"
    MANAGEMENT = "management"
    DESIGN = "design"
    OTHER = "other"

class SkillAction(BaseModel):
    """技能绑定的可执行动作"""
    type: str  # command, api, script, function
    config: Dict[str, Any]  # 动作配置
    timeout: int = 300  # 超时时间 (秒)
    
class SkillNode(BaseModel):
    """技能节点 - 工作流的基本单元"""
    id: str
    name: str
    category: SkillCategory
    level: SkillLevel
    description: str = ""
    tags: List[str] = []
    actions: List[SkillAction] = []  # 新增：技能可执行的动作
    dependencies: List[str] = []  # 依赖的其他技能 ID
    metadata: Dict[str, Any] = {}  # 扩展元数据
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # 统计字段
    total_hours: float = 0.0
    execution_count: int = 0  # 新增：被调用次数
    last_executed: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

#### 1.1.3 创建工作流模型 (`src/models/workflow.py`) - **新增文件**

```python
from pydantic import BaseModel, Field, validator
from enum import Enum
from datetime import datetime
from typing import List, Optional, Dict, Any, Union

class NodeType(str, Enum):
    SKILL = "skill"          # 技能节点
    CONDITION = "condition"  # 条件判断
    LOOP = "loop"           # 循环
    PARALLEL = "parallel"   # 并行组
    SUB_WORKFLOW = "sub_workflow"  # 子工作流

class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

class WorkflowNode(BaseModel):
    """工作流节点定义"""
    id: str
    type: NodeType
    name: str
    skill_id: Optional[str] = None  # 关联的技能 ID
    params: Dict[str, Any] = {}     # 节点参数
    condition: Optional[str] = None  # 条件表达式 (Jinja2 模板)
    depends_on: List[str] = []      # 依赖的前置节点 ID
    retry_count: int = 0            # 重试次数
    timeout: int = 300              # 超时时间
    
class WorkflowTrigger(BaseModel):
    """工作流触发器"""
    type: str  # cron, manual, event, api
    config: Dict[str, Any] = {}
    
class Workflow(BaseModel):
    """工作流定义"""
    id: str
    name: str
    version: str = "1.0"
    description: str = ""
    nodes: List[WorkflowNode] = []
    triggers: List[WorkflowTrigger] = []
    variables: Dict[str, Any] = {}  # 全局变量
    on_success: List[Dict] = []     # 成功回调
    on_failure: List[Dict] = []     # 失败回调
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def validate_dag(self) -> bool:
        """验证是否是有向无环图"""
        # 使用拓扑排序检测环
        from collections import deque
        
        in_degree = {node.id: 0 for node in self.nodes}
        graph = {node.id: node.depends_on for node in self.nodes}
        
        for node_id, deps in graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[node_id] += 1
        
        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        visited = 0
        
        while queue:
            node_id = queue.popleft()
            visited += 1
            for nid, deps in graph.items():
                if node_id in deps:
                    in_degree[nid] -= 1
                    if in_degree[nid] == 0:
                        queue.append(nid)
        
        return visited == len(self.nodes)
```

#### 1.1.4 创建执行上下文模型 (`src/models/context.py`) - **新增文件**

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any, List, Optional

class ExecutionContext(BaseModel):
    """工作流执行上下文"""
    workflow_id: str
    execution_id: str
    started_at: datetime = Field(default_factory=datetime.now)
    variables: Dict[str, Any] = {}
    node_outputs: Dict[str, Any] = {}  # 节点输出
    node_statuses: Dict[str, str] = {}  # 节点状态
    errors: List[Dict] = []
    
    def get_variable(self, key: str, default=None):
        return self.variables.get(key, default)
    
    def set_variable(self, key: str, value: Any):
        self.variables[key] = value
    
    def get_node_output(self, node_id: str):
        return self.node_outputs.get(node_id)
    
    def set_node_output(self, node_id: str, output: Any):
        self.node_outputs[node_id] = output
    
    def set_node_status(self, node_id: str, status: str):
        self.node_statuses[node_id] = status
    
    def add_error(self, node_id: str, error: str):
        self.errors.append({
            "node_id": node_id,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
```

### 1.2 存储层抽象 (`src/storage/`)

#### 1.2.1 创建存储接口 (`src/storage/base.py`)

```python
from abc import ABC, abstractmethod
from typing import List, Optional, TypeVar, Generic

T = TypeVar('T')

class BaseStorage(ABC, Generic[T]):
    """存储层抽象基类"""
    
    @abstractmethod
    def get(self, id: str) -> Optional[T]:
        pass
    
    @abstractmethod
    def list(self, filters: dict = None) -> List[T]:
        pass
    
    @abstractmethod
    def save(self, item: T) -> T:
        pass
    
    @abstractmethod
    def delete(self, id: str) -> bool:
        pass
    
    @abstractmethod
    def exists(self, id: str) -> bool:
        pass
```

#### 1.2.2 实现 JSON 文件存储 (`src/storage/json_storage.py`)

```python
import json
from pathlib import Path
from typing import List, Optional, Type
from .base import BaseStorage

class JSONStorage(BaseStorage):
    """基于 JSON 文件的存储实现"""
    
    def __init__(self, model_class: Type, data_dir: str, file_name: str):
        self.model_class = model_class
        self.data_dir = Path(data_dir)
        self.file_path = self.data_dir / file_name
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._cache = {}
        self._load()
    
    def _load(self):
        if self.file_path.exists():
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for id, item_data in data.items():
                    self._cache[id] = self.model_class(**item_data)
    
    def _save(self):
        data = {id: item.dict() for id, item in self._cache.items()}
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get(self, id: str) -> Optional[T]:
        return self._cache.get(id)
    
    def list(self, filters: dict = None) -> List[T]:
        items = list(self._cache.values())
        if filters:
            for key, value in filters.items():
                items = [i for i in items if getattr(i, key, None) == value]
        return items
    
    def save(self, item: T) -> T:
        id = getattr(item, 'id', getattr(item, 'name'))
        self._cache[id] = item
        self._save()
        return item
    
    def delete(self, id: str) -> bool:
        if id in self._cache:
            del self._cache[id]
            self._save()
            return True
        return False
    
    def exists(self, id: str) -> bool:
        return id in self._cache
```

### 1.3 技能管理器重构 (`src/core/skill_manager.py`)

```python
from typing import List, Optional
from ..models.skill import SkillNode, SkillAction
from ..storage.json_storage import JSONStorage

class SkillManager:
    """技能管理器 - 支持工作流集成"""
    
    def __init__(self, data_dir: str = "data/skills"):
        self.storage = JSONStorage(
            model_class=SkillNode,
            data_dir=data_dir,
            file_name="skills.json"
        )
    
    def create_skill(self, **kwargs) -> SkillNode:
        """创建技能"""
        skill = SkillNode(id=kwargs['name'], **kwargs)
        return self.storage.save(skill)
    
    def bind_action(self, skill_id: str, action: SkillAction) -> SkillNode:
        """为技能绑定可执行动作"""
        skill = self.storage.get(skill_id)
        if not skill:
            raise ValueError(f"Skill {skill_id} not found")
        
        skill.actions.append(action)
        skill.updated_at = datetime.now()
        return self.storage.save(skill)
    
    def execute_skill(self, skill_id: str, context: dict = None) -> any:
        """执行技能绑定的动作"""
        skill = self.storage.get(skill_id)
        if not skill or not skill.actions:
            raise ValueError(f"No executable action for skill {skill_id}")
        
        # 执行第一个动作 (后续可支持多动作选择)
        action = skill.actions[0]
        return self._execute_action(action, context)
    
    def _execute_action(self, action: SkillAction, context: dict):
        """执行具体动作"""
        if action.type == "command":
            import subprocess
            result = subprocess.run(
                action.config['command'],
                shell=True,
                capture_output=True,
                text=True,
                timeout=action.timeout
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        elif action.type == "api":
            import requests
            response = requests.request(
                method=action.config.get('method', 'GET'),
                url=action.config['url'],
                headers=action.config.get('headers', {}),
                json=action.config.get('body'),
                timeout=action.timeout
            )
            return response.json()
        # 其他类型...
```

---

## 第二阶段：工作流引擎开发 (Week 3-5)

### 2.1 工作流解析器 (`src/engine/parser.py`)

```python
import yaml
from pathlib import Path
from typing import Dict, Any
from ..models.workflow import Workflow, WorkflowNode, NodeType

class WorkflowParser:
    """工作流定义解析器"""
    
    @staticmethod
    def from_file(file_path: str) -> Workflow:
        """从 YAML 文件加载工作流"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return Workflow(**data)
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Workflow:
        """从字典创建"""
        return Workflow(**data)
    
    @staticmethod
    def validate(workflow: Workflow) -> List[str]:
        """验证工作流定义"""
        errors = []
        
        # 检查 DAG
        if not workflow.validate_dag():
            errors.append("Workflow contains circular dependencies")
        
        # 检查节点引用
        node_ids = {n.id for n in workflow.nodes}
        for node in workflow.nodes:
            for dep in node.depends_on:
                if dep not in node_ids:
                    errors.append(f"Node {node.id} depends on non-existent node {dep}")
        
        return errors
```

### 2.2 工作流执行器 (`src/engine/executor.py`)

```python
import asyncio
from datetime import datetime
from typing import Dict, Any, Callable
from ..models.workflow import Workflow, WorkflowNode, NodeStatus
from ..models.context import ExecutionContext
from ..core.skill_manager import SkillManager

class WorkflowExecutor:
    """工作流执行引擎"""
    
    def __init__(self, skill_manager: SkillManager):
        self.skill_manager = skill_manager
        self.node_handlers: Dict[NodeType, Callable] = {
            NodeType.SKILL: self._execute_skill_node,
            NodeType.CONDITION: self._execute_condition_node,
            NodeType.PARALLEL: self._execute_parallel_node,
        }
    
    async def execute(self, workflow: Workflow, 
                     initial_context: Dict[str, Any] = None) -> ExecutionContext:
        """执行工作流"""
        context = ExecutionContext(
            workflow_id=workflow.id,
            execution_id=f"{workflow.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            variables=initial_context or {}
        )
        
        # 拓扑排序确定执行顺序
        sorted_nodes = self._topological_sort(workflow.nodes)
        
        for node in sorted_nodes:
            # 检查依赖是否完成
            if not self._check_dependencies(node, context):
                context.set_node_status(node.id, NodeStatus.SKIPPED)
                continue
            
            # 检查条件
            if node.condition and not self._evaluate_condition(node.condition, context):
                context.set_node_status(node.id, NodeStatus.SKIPPED)
                continue
            
            try:
                context.set_node_status(node.id, NodeStatus.RUNNING)
                
                # 执行节点
                handler = self.node_handlers.get(node.type)
                if handler:
                    output = await handler(node, context)
                    context.set_node_output(node.id, output)
                    context.set_node_status(node.id, NodeStatus.SUCCESS)
                else:
                    raise ValueError(f"Unknown node type: {node.type}")
                    
            except Exception as e:
                context.set_node_status(node.id, NodeStatus.FAILED)
                context.add_error(node.id, str(e))
                
                if node.retry_count > 0:
                    # 重试逻辑
                    pass
                else:
                    # 失败处理
                    break
        
        return context
    
    def _topological_sort(self, nodes):
        """拓扑排序"""
        from collections import deque
        
        in_degree = {n.id: len(n.depends_on) for n in nodes}
        graph = {n.id: [] for n in nodes}
        
        for node in nodes:
            for dep in node.depends_on:
                if dep in graph:
                    graph[dep].append(node.id)
        
        queue = deque([n for n in nodes if in_degree[n.id] == 0])
        result = []
        
        while queue:
            node = queue.popleft()
            result.append(node)
            
            for neighbor_id in graph[node.id]:
                in_degree[neighbor_id] -= 1
                if in_degree[neighbor_id] == 0:
                    neighbor = next(n for n in nodes if n.id == neighbor_id)
                    queue.append(neighbor)
        
        return result
    
    def _check_dependencies(self, node: WorkflowNode, context: ExecutionContext) -> bool:
        """检查依赖节点是否成功"""
        for dep_id in node.depends_on:
            status = context.node_statuses.get(dep_id)
            if status != NodeStatus.SUCCESS:
                return False
        return True
    
    def _evaluate_condition(self, condition: str, context: ExecutionContext) -> bool:
        """评估条件表达式"""
        from jinja2 import Template
        template = Template(condition)
        result = template.render(**context.variables, **context.node_outputs)
        return eval(result)
    
    async def _execute_skill_node(self, node: WorkflowNode, context: ExecutionContext):
        """执行技能节点"""
        if not node.skill_id:
            raise ValueError(f"Skill node {node.id} has no skill_id")
        
        return self.skill_manager.execute_skill(
            node.skill_id,
            context=context.variables
        )
    
    async def _execute_condition_node(self, node: WorkflowNode, context: ExecutionContext):
        """执行条件节点"""
        return self._evaluate_condition(node.condition, context)
    
    async def _execute_parallel_node(self, node: WorkflowNode, context: ExecutionContext):
        """执行并行节点"""
        # TODO: 实现并行执行逻辑
        pass
```

### 2.3 工作流管理器 (`src/core/workflow_manager.py`)

```python
from typing import List, Optional
from ..models.workflow import Workflow
from ..storage.json_storage import JSONStorage
from .engine.executor import WorkflowExecutor
from .skill_manager import SkillManager

class WorkflowManager:
    """工作流管理器"""
    
    def __init__(self, data_dir: str = "data/workflows"):
        self.storage = JSONStorage(
            model_class=Workflow,
            data_dir=data_dir,
            file_name="workflows.json"
        )
        self.skill_manager = SkillManager()
        self.executor = WorkflowExecutor(self.skill_manager)
    
    def create_workflow(self, workflow: Workflow) -> Workflow:
        """创建工作流"""
        errors = WorkflowParser.validate(workflow)
        if errors:
            raise ValueError(f"Invalid workflow: {', '.join(errors)}")
        return self.storage.save(workflow)
    
    def load_workflow(self, file_path: str) -> Workflow:
        """从文件加载并保存工作流"""
        workflow = WorkflowParser.from_file(file_path)
        return self.create_workflow(workflow)
    
    async def run_workflow(self, workflow_id: str, 
                          context: dict = None) -> ExecutionContext:
        """运行工作流"""
        workflow = self.storage.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        return await self.executor.execute(workflow, context)
    
    def list_workflows(self) -> List[Workflow]:
        """列出所有工作流"""
        return self.storage.list()
```

---

## 第三阶段：日报系统改造为工作流插件 (Week 6)

### 3.1 创建日报技能节点 (`src/skills/daily_report_skill.py`)

```python
from ..models.skill import SkillNode, SkillAction, SkillCategory, SkillLevel
from ..core.daily_report import DailyReportManager

class DailyReportSkill:
    """日报技能封装"""
    
    @staticmethod
    def create_skill_node() -> SkillNode:
        """创建日报技能节点"""
        return SkillNode(
            id="daily-report",
            name="Daily Report Generator",
            category=SkillCategory.SOFT_SKILL,
            level=SkillLevel.ADVANCED,
            description="自动生成个人日报",
            tags=["productivity", "reporting"],
            actions=[
                SkillAction(
                    type="function",
                    config={
                        "module": "src.skills.daily_report_skill",
                        "function": "generate_report"
                    }
                )
            ]
        )
    
    @staticmethod
    def generate_report(context: dict) -> dict:
        """生成日报"""
        mgr = DailyReportManager()
        
        # 从上下文获取数据
        date_str = context.get('date', 'today')
        include_stats = context.get('include_stats', True)
        
        # 生成报告
        report = mgr.export_report()
        
        return {
            "report": report,
            "success": True
        }
```

### 3.2 创建工作流示例

创建 `data/workflows/daily-review.yaml`:

```yaml
id: daily-review
name: 每日研发效能复盘
version: "1.0"
description: 自动拉取 Git 提交，分析代码量，生成日报

variables:
  date: "{{ today }}"
  
nodes:
  - id: fetch_git
    type: skill
    name: 获取 Git 提交
    skill_id: git-log
    params:
      since: "24 hours ago"
  
  - id: analyze_code
    type: skill
    name: 分析代码变更
    skill_id: code-analyzer
    depends_on: [fetch_git]
    params:
      input: "{{ nodes.fetch_git.output }}"
  
  - id: collect_mood
    type: skill
    name: 收集心情评分
    skill_id: mood-tracker
  
  - id: generate_report
    type: skill
    name: 生成日报
    skill_id: daily-report
    depends_on: [analyze_code, collect_mood]
    params:
      git_stats: "{{ nodes.analyze_code.output }}"
      mood: "{{ nodes.collect_mood.output }}"

on_success:
  - type: notify
    channel: console
    message: "日报生成成功!"
```

---

## 第四阶段：CLI 升级与测试 (Week 7-8)

### 4.1 新增 CLI 命令 (`src/cli.py`)

```python
# 添加工作流相关命令
def cmd_run_workflow(args):
    """运行工作流"""
    import asyncio
    from .core.workflow_manager import WorkflowManager
    
    mgr = WorkflowManager()
    
    # 加载上下文变量
    context = {}
    if args.vars:
        for var in args.vars:
            key, value = var.split('=')
            context[key] = value
    
    # 执行
    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(mgr.run_workflow(args.workflow_id, context))
    
    print(f"✅ 工作流执行完成: {result.execution_id}")
    print(f"状态：{result.node_statuses}")

def cmd_create_workflow(args):
    """创建工作流"""
    from .core.workflow_manager import WorkflowManager
    from .models.workflow import Workflow
    
    mgr = WorkflowManager()
    
    # 从 YAML 文件加载
    workflow = WorkflowParser.from_file(args.file)
    saved = mgr.create_workflow(workflow)
    
    print(f"✅ 工作流已创建：{saved.id}")

# 在 main() 中注册新命令
p_wf_run = subparsers.add_parser('run-workflow', help='运行工作流')
p_wf_run.add_argument('workflow_id', help='工作流 ID')
p_wf_run.add_argument('--vars', nargs='*', help='上下文变量 key=value')
p_wf_run.set_defaults(func=cmd_run_workflow)

p_wf_create = subparsers.add_parser('create-workflow', help='创建工作流')
p_wf_create.add_argument('file', help='YAML 文件路径')
p_wf_create.set_defaults(func=cmd_create_workflow)
```

### 4.2 单元测试 (`tests/test_workflow_engine.py`)

```python
import pytest
from src.models.workflow import Workflow, WorkflowNode, NodeType
from src.engine.executor import WorkflowExecutor
from src.core.skill_manager import SkillManager

@pytest.fixture
def sample_workflow():
    return Workflow(
        id="test-wf",
        name="Test Workflow",
        nodes=[
            WorkflowNode(
                id="node1",
                type=NodeType.SKILL,
                name="First Node",
                skill_id="test-skill"
            ),
            WorkflowNode(
                id="node2",
                type=NodeType.SKILL,
                name="Second Node",
                skill_id="test-skill",
                depends_on=["node1"]
            )
        ]
    )

def test_workflow_validation(sample_workflow):
    assert sample_workflow.validate_dag() is True

def test_circular_dependency():
    workflow = Workflow(
        id="circular-wf",
        name="Circular",
        nodes=[
            WorkflowNode(id="a", type=NodeType.SKILL, depends_on=["b"]),
            WorkflowNode(id="b", type=NodeType.SKILL, depends_on=["a"])
        ]
    )
    assert workflow.validate_dag() is False

@pytest.mark.asyncio
async def test_workflow_execution(sample_workflow):
    skill_mgr = SkillManager()
    executor = WorkflowExecutor(skill_mgr)
    
    context = await executor.execute(sample_workflow)
    
    assert context.node_statuses["node1"] == "success"
    assert context.node_statuses["node2"] == "success"
```

---

## 迁移指南：现有数据兼容

### 5.1 技能数据迁移脚本

```python
# scripts/migrate_skills.py
import json
from pathlib import Path
from src.models.skill import SkillNode, SkillCategory, SkillLevel

def migrate_old_skills():
    old_file = Path("data/skills/skills.json")
    new_file = Path("data/skills/skills_new.json")
    
    with open(old_file, 'r', encoding='utf-8') as f:
        old_data = json.load(f)
    
    new_data = {}
    for name, skill_dict in old_data.items():
        # 转换为新格式
        skill = SkillNode(
            id=name,
            name=name,
            category=SkillCategory(skill_dict.get('category', 'other')),
            level=SkillLevel(skill_dict.get('level', 1)),
            description=skill_dict.get('description', ''),
            tags=skill_dict.get('tags', []),
            total_hours=skill_dict.get('total_hours', 0.0)
        )
        new_data[name] = skill.dict()
    
    with open(new_file, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
    
    print(f"迁移完成：{len(new_data)} 个技能")

if __name__ == "__main__":
    migrate_old_skills()
```

---

## 成功指标

1. **功能完整性**: 支持至少 5 种节点类型，可运行组合工作流
2. **性能**: 简单工作流 (<10 节点) 执行延迟 < 100ms
3. **兼容性**: 100% 兼容现有技能数据
4. **测试覆盖**: 核心引擎测试覆盖率 > 80%
5. **文档**: 完整 API 文档 + 3 个以上工作流示例

---

## 风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 架构复杂度过高 | 开发延期 | 分阶段迭代，先实现核心串行执行 |
| 性能瓶颈 | 用户体验差 | 引入异步执行，优化拓扑排序算法 |
| 数据迁移丢失 | 用户数据损失 | 编写自动化迁移脚本 + 手动验证 |
| 学习曲线陡峭 | 用户流失 | 提供丰富模板 + 可视化编排工具 |

---

**下一步行动**:
1. ✅ 评审本实施计划
2. ⬜ 创建 Git 分支 `feature/v2-architecture`
3. ⬜ 执行 Week 1 任务：Pydantic 模型重构
4. ⬜ 编写第一批单元测试
