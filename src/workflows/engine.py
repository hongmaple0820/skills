"""
Skills Platform v2.0 - Workflow Engine
DAG 执行引擎，支持串行/并行/条件分支/子工作流嵌套
"""
import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from jinja2 import Environment

from ..core.models import (
    Workflow, WorkflowNode, WorkflowNodeType, ExecutionContext,
    SkillAction, MoodEmoji
)
from ..storage.base import StorageManager


class NodeExecutionError(Exception):
    """节点执行异常"""
    pass


class WorkflowEngine:
    """工作流执行引擎"""

    def __init__(self, storage_manager: StorageManager):
        self.storage = storage_manager
        self.node_executors: Dict[WorkflowNodeType, Callable] = {
            WorkflowNodeType.SKILL_ACTION: self._execute_skill_action,
            WorkflowNodeType.DECISION: self._execute_decision,
            WorkflowNodeType.PARALLEL: self._execute_parallel,
            WorkflowNodeType.SEQUENTIAL: self._execute_sequential,
            WorkflowNodeType.SUB_WORKFLOW: self._execute_sub_workflow,
            WorkflowNodeType.CUSTOM: self._execute_custom,
        }
        self._custom_handlers: Dict[str, Callable] = {}
        self._template_env = Environment()

    def register_custom_handler(self, name: str, handler: Callable):
        """注册自定义节点处理器"""
        self._custom_handlers[name] = handler

    def _template_context(self, context: ExecutionContext) -> Dict[str, Any]:
        return {
            "nodes": context.node_results,
            "variables": context.variables,
            "execution_id": context.execution_id,
            "workflow_id": context.workflow_id,
        }

    def resolve_template(self, template_str: str, context: ExecutionContext) -> Any:
        """解析 Jinja2 模板表达式"""
        if not isinstance(template_str, str):
            return template_str

        if "{{" not in template_str or "}}" not in template_str:
            return template_str

        template_context = self._template_context(context)
        stripped = template_str.strip()

        if stripped.startswith("{{") and stripped.endswith("}}") and stripped.count("{{") == 1:
            expr = stripped[2:-2].strip()
            try:
                return self._template_env.compile_expression(expr)(**template_context)
            except Exception as e:
                raise NodeExecutionError(f"Template expression failed: {e}")

        try:
            return self._template_env.from_string(template_str).render(**template_context)
        except Exception as e:
            raise NodeExecutionError(f"Template resolution failed: {e}")

    def resolve_value(self, value: Any, context: ExecutionContext) -> Any:
        """递归解析输入中的模板值。"""
        if isinstance(value, dict):
            return {key: self.resolve_value(item, context) for key, item in value.items()}
        if isinstance(value, list):
            return [self.resolve_value(item, context) for item in value]
        return self.resolve_template(value, context)

    def _coerce_condition(self, value: Any) -> bool:
        """将模板结果转换为条件布尔值。"""
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"", "false", "0", "none", "null", "no"}:
                return False
        return bool(value)

    def resolve_inputs(self, node: WorkflowNode, context: ExecutionContext) -> Dict[str, Any]:
        """解析节点输入"""
        resolved = {}
        for key, value in node.inputs.items():
            resolved[key] = self.resolve_value(value, context)
        return resolved

    async def execute_node(self, node: WorkflowNode, context: ExecutionContext) -> Dict[str, Any]:
        """执行单个节点"""
        context.add_log(node.id, f"Starting node: {node.name}", "info")
        
        # 检查条件
        if node.condition:
            condition_result = self.resolve_template(node.condition, context)
            if not self._coerce_condition(condition_result):
                context.add_log(node.id, f"Condition not met, skipping: {node.condition}", "warning")
                return {"skipped": True, "reason": "condition_not_met"}

        # 解析输入
        inputs = self.resolve_inputs(node, context)
        
        # 获取执行器
        executor = self.node_executors.get(node.node_type)
        if not executor:
            raise NodeExecutionError(f"No executor for node type: {node.node_type}")

        try:
            # 执行节点
            if asyncio.iscoroutinefunction(executor):
                result = await executor(node, inputs, context)
            else:
                result = executor(node, inputs, context)
            
            context.set_node_result(node.id, result)
            context.add_log(node.id, f"Node completed: {node.name}", "info")
            return result
        except Exception as e:
            error_msg = str(e)
            context.set_node_error(node.id, error_msg)
            context.add_log(node.id, f"Node failed: {error_msg}", "error")
            
            # 重试逻辑
            if node.retry_count > 0:
                context.add_log(node.id, f"Retrying ({node.retry_count} attempts)", "warning")
                for attempt in range(node.retry_count):
                    try:
                        if asyncio.iscoroutinefunction(executor):
                            result = await executor(node, inputs, context)
                        else:
                            result = executor(node, inputs, context)
                        context.set_node_result(node.id, result)
                        return result
                    except Exception:
                        if attempt == node.retry_count - 1:
                            raise
                        await asyncio.sleep(1)
            else:
                raise

    def _execute_skill_action(self, node: WorkflowNode, inputs: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """执行技能动作节点"""
        if not node.action:
            # 尝试从技能获取动作
            skill_storage = self.storage.skill_storage()
            skill = skill_storage.get(node.skill_id)
            # name-based fallback: 如果 ID 查询失败，尝试按名称查找
            if skill is None:
                results = skill_storage.query({'name': node.skill_id})
                skill = results[0] if results else None
            if not skill or not skill.actions:
                raise NodeExecutionError(f"No action defined for node: {node.name}")
            action = skill.actions[0]  # 使用第一个动作
        else:
            action = node.action

        # 根据动作类型执行
        if action.action_type == "cli_function":
            return self._execute_cli_function(action, inputs, context)
        elif action.action_type == "api_call":
            return self._execute_api_call(action, inputs, context)
        elif action.action_type == "workflow_trigger":
            return self._trigger_workflow(action, inputs, context)
        else:
            raise NodeExecutionError(f"Unknown action type: {action.action_type}")

    def _execute_cli_function(self, action: SkillAction, inputs: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """执行 CLI 函数"""
        # 这里应该动态导入并调用实际的 CLI 函数
        # 目前返回模拟结果
        return {
            "action": "cli_function",
            "target": action.target,
            "inputs": inputs,
            "output": f"Executed CLI function: {action.target}",
            "success": True
        }

    def _execute_api_call(self, action: SkillAction, inputs: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """执行 API 调用"""
        # 实际实现应使用 httpx 或 requests
        return {
            "action": "api_call",
            "target": action.target,
            "inputs": inputs,
            "output": {"status": "simulated", "data": {}},
            "success": True
        }

    def _trigger_workflow(self, action: SkillAction, inputs: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """触发子工作流"""
        workflow_id = action.target
        workflow_storage = self.storage.workflow_storage()
        workflow = workflow_storage.get(workflow_id)
        
        if not workflow:
            raise NodeExecutionError(f"Workflow not found: {workflow_id}")

        # 递归执行子工作流
        sub_execution = ExecutionContext(workflow_id=workflow_id, variables=inputs)
        result = asyncio.run(self.execute_workflow(workflow, sub_execution))
        
        return {
            "action": "workflow_trigger",
            "sub_workflow_id": workflow_id,
            "sub_execution_id": sub_execution.execution_id,
            "result": result,
            "success": result.status == "completed"
        }

    def _execute_decision(self, node: WorkflowNode, inputs: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """执行决策节点"""
        # 决策节点根据条件选择分支
        branches = node.metadata.get("branches", {})
        selected_branch = None
        
        for branch_name, condition in branches.items():
            if self._coerce_condition(self.resolve_template(condition, context)):
                selected_branch = branch_name
                break
        
        return {
            "decision": "branch_selected",
            "selected_branch": selected_branch,
            "next_node": node.children[0] if selected_branch and node.children else None
        }

    async def _execute_parallel(self, node: WorkflowNode, inputs: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """执行并行节点"""
        if not node.children:
            return {"parallel": "no_children", "results": []}

        workflow_storage = self.storage.workflow_storage()
        workflow = workflow_storage.get(context.workflow_id)
        
        tasks = []
        for child_id in node.children:
            child_node = workflow.nodes.get(child_id)
            if child_node:
                tasks.append(self.execute_node(child_node, context))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            "parallel": "completed",
            "children_count": len(node.children),
            "results": [str(r) if isinstance(r, Exception) else r for r in results]
        }

    async def _execute_sequential(self, node: WorkflowNode, inputs: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """执行顺序节点"""
        if not node.children:
            return {"sequential": "no_children", "results": []}

        workflow_storage = self.storage.workflow_storage()
        workflow = workflow_storage.get(context.workflow_id)
        
        results = []
        for child_id in node.children:
            child_node = workflow.nodes.get(child_id)
            if child_node:
                result = await self.execute_node(child_node, context)
                results.append(result)
        
        return {
            "sequential": "completed",
            "children_count": len(node.children),
            "results": results
        }

    async def _execute_sub_workflow(self, node: WorkflowNode, inputs: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """执行子工作流节点"""
        sub_workflow_id = node.metadata.get("workflow_id")
        if not sub_workflow_id:
            raise NodeExecutionError(f"No workflow_id specified in sub_workflow node: {node.name}")

        workflow_storage = self.storage.workflow_storage()
        sub_workflow = workflow_storage.get(sub_workflow_id)
        
        if not sub_workflow:
            raise NodeExecutionError(f"Sub-workflow not found: {sub_workflow_id}")

        sub_execution = ExecutionContext(
            workflow_id=sub_workflow_id,
            variables={**context.variables, **inputs}
        )
        
        result = await self.execute_workflow(sub_workflow, sub_execution)
        
        return {
            "sub_workflow": "completed",
            "workflow_id": sub_workflow_id,
            "execution_id": sub_execution.execution_id,
            "status": result.status,
            "node_results": sub_execution.node_results
        }

    def _execute_custom(self, node: WorkflowNode, inputs: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """执行自定义节点"""
        handler_name = node.metadata.get("handler")
        if not handler_name:
            raise NodeExecutionError(f"No handler specified for custom node: {node.name}")
        
        handler = self._custom_handlers.get(handler_name)
        if not handler:
            raise NodeExecutionError(f"Custom handler not found: {handler_name}")
        
        return handler(inputs, context)

    async def execute_workflow(self, workflow: Workflow, context: ExecutionContext) -> ExecutionContext:
        """执行完整工作流"""
        context.status = "running"
        context.add_log("workflow", f"Starting workflow: {workflow.name}", "info")

        try:
            # 从入口节点开始执行
            entry_node = workflow.nodes.get(workflow.entry_point)
            if not entry_node:
                raise NodeExecutionError(f"Entry point not found: {workflow.entry_point}")

            await self.execute_node(entry_node, context)

            # 遍历后续节点（简单 BFS）
            visited = {workflow.entry_point}
            queue = [workflow.entry_point]
            
            while queue:
                current_id = queue.pop(0)
                current_node = workflow.nodes.get(current_id)
                
                if current_node and current_node.children:
                    for child_id in current_node.children:
                        if child_id not in visited:
                            visited.add(child_id)
                            queue.append(child_id)
                            if child_id in context.node_results:
                                continue
                            child_node = workflow.nodes.get(child_id)
                            if child_node:
                                await self.execute_node(child_node, context)

            context.status = "completed"
            context.end_time = datetime.now()
            context.add_log("workflow", "Workflow completed successfully", "info")

        except Exception as e:
            context.status = "failed"
            context.error = str(e)
            context.end_time = datetime.now()
            context.add_log("workflow", f"Workflow failed: {str(e)}", "error")

        return context

    def run(self, workflow_id: str, variables: Optional[Dict[str, Any]] = None) -> ExecutionContext:
        """同步运行工作流"""
        workflow_storage = self.storage.workflow_storage()
        workflow = workflow_storage.get(workflow_id)
        
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        context = ExecutionContext(workflow_id=workflow_id, variables=variables or {})
        return asyncio.run(self.execute_workflow(workflow, context))
