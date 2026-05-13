"""
Skills Platform v2.0 - YAML Workflow Parser
将 YAML 工作流定义解析为 Workflow 对象
"""
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from ..core.models import (
    Workflow, WorkflowNode, WorkflowNodeType, WorkflowTrigger, SkillAction
)


class WorkflowParseError(Exception):
    """工作流解析异常"""
    pass


class YamlWorkflowParser:
    """YAML 工作流解析器"""

    def parse_file(self, file_path: str) -> Workflow:
        """从 YAML 文件解析工作流"""
        path = Path(file_path)
        if not path.exists():
            raise WorkflowParseError(f"File not found: {file_path}")

        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        return self.parse_dict(data)

    def parse_string(self, yaml_string: str) -> Workflow:
        """从 YAML 字符串解析工作流"""
        data = yaml.safe_load(yaml_string)
        return self.parse_dict(data)

    def parse_dict(self, data: Dict[str, Any]) -> Workflow:
        """从字典解析工作流"""
        try:
            # 解析基本信息
            workflow = Workflow(
                name=data.get('name', 'Unnamed Workflow'),
                description=data.get('description'),
                version=data.get('version', '1.0.0'),
                entry_point=data.get('entry_point'),
                variables=data.get('variables', {}),
                tags=data.get('tags', [])
            )

            # 解析触发器
            if 'triggers' in data:
                workflow.triggers = [self._parse_trigger(t) for t in data['triggers']]

            # 解析节点
            if 'nodes' in data:
                workflow.nodes = {
                    node_id: self._parse_node(node_id, node_data)
                    for node_id, node_data in data['nodes'].items()
                }

            # 验证入口节点
            if workflow.entry_point and workflow.entry_point not in workflow.nodes:
                raise WorkflowParseError(f"Entry point '{workflow.entry_point}' not found in nodes")

            return workflow

        except KeyError as e:
            raise WorkflowParseError(f"Missing required field: {e}")
        except Exception as e:
            raise WorkflowParseError(f"Failed to parse workflow: {e}")

    def _parse_trigger(self, data: Dict[str, Any]) -> WorkflowTrigger:
        """解析触发器"""
        trigger_type = data.get('type', 'manual')
        if trigger_type not in ['manual', 'scheduled', 'event']:
            raise WorkflowParseError(f"Invalid trigger type: {trigger_type}")

        return WorkflowTrigger(
            type=trigger_type,
            cron=data.get('cron') if trigger_type == 'scheduled' else None,
            event=data.get('event') if trigger_type == 'event' else None
        )

    def _parse_node(self, node_id: str, data: Dict[str, Any]) -> WorkflowNode:
        """解析节点"""
        node_type_str = data.get('type', 'skill_action')
        
        try:
            node_type = WorkflowNodeType(node_type_str)
        except ValueError:
            raise WorkflowParseError(f"Invalid node type: {node_type_str}")

        # 解析动作
        action = None
        if 'action' in data:
            action_data = data['action']
            action = SkillAction(
                action_type=action_data.get('action_type', 'cli_function'),
                target=action_data.get('target', ''),
                params=action_data.get('params', {}),
                description=action_data.get('description')
            )

        # 解析条件
        condition = data.get('condition')
        if isinstance(condition, dict):
            # 复杂条件表达式
            condition = self._build_condition_expression(condition)

        # 解析子节点
        children = data.get('children', [])
        if isinstance(children, str):
            children = [children]

        return WorkflowNode(
            id=node_id,
            name=data.get('name', node_id),
            node_type=node_type,
            skill_id=data.get('skill_id'),
            action=action,
            condition=condition,
            inputs=data.get('inputs', {}),
            outputs=data.get('outputs', {}),
            children=children,
            retry_count=data.get('retry_count', 0),
            timeout=data.get('timeout'),
            metadata=data.get('metadata', {})
        )

    def _build_condition_expression(self, condition: Dict[str, Any]) -> str:
        """构建条件表达式"""
        # 支持简单的条件语法
        if 'if' in condition:
            expr = condition['if']
            if 'then' in condition:
                return f"{{{{ {expr} }}}}"
            return f"{{{{ {expr} }}}}"
        return str(condition)


def load_workflow(file_path: str) -> Workflow:
    """便捷函数：加载 YAML 工作流文件"""
    parser = YamlWorkflowParser()
    return parser.parse_file(file_path)


def create_workflow_from_yaml(yaml_content: str) -> Workflow:
    """便捷函数：从 YAML 字符串创建工作流"""
    parser = YamlWorkflowParser()
    return parser.parse_string(yaml_content)
