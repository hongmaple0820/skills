"""
Skills Platform v2.0 - Storage Layer Abstraction
支持多种存储后端：JSON 文件、SQLite、内存
"""
import json
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, TypeVar, Generic, Any
from datetime import datetime
import threading

from src.core.models import Skill, Workflow, DailyLogEntry, ExecutionContext

T = TypeVar('T')


class StorageError(Exception):
    """存储层异常"""
    pass


class BaseStorage(ABC, Generic[T]):
    """存储层抽象基类"""

    @abstractmethod
    def save(self, item: T) -> bool:
        """保存单个项目"""
        pass

    @abstractmethod
    def get(self, item_id: str) -> Optional[T]:
        """获取单个项目"""
        pass

    @abstractmethod
    def get_all(self) -> List[T]:
        """获取所有项目"""
        pass

    @abstractmethod
    def delete(self, item_id: str) -> bool:
        """删除项目"""
        pass

    @abstractmethod
    def update(self, item_id: str, data: Dict[str, Any]) -> Optional[T]:
        """更新项目"""
        pass

    @abstractmethod
    def query(self, filters: Dict[str, Any]) -> List[T]:
        """查询项目"""
        pass


class JSONStorage(BaseStorage[T]):
    """JSON 文件存储实现"""

    def __init__(self, file_path: str, model_class: type):
        self.file_path = Path(file_path)
        self.model_class = model_class
        self._lock = threading.Lock()
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """确保文件存在"""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def _load_data(self) -> List[Dict]:
        """加载数据"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_data(self, data: List[Dict]):
        """保存数据"""
        with self._lock:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    def save(self, item: T) -> bool:
        """保存单个项目"""
        try:
            data = self._load_data()
            # 检查是否已存在
            item_id = getattr(item, 'id', None)
            if item_id:
                for i, existing in enumerate(data):
                    if existing.get('id') == item_id:
                        data[i] = item.model_dump()
                        self._save_data(data)
                        return True
            data.append(item.model_dump())
            self._save_data(data)
            return True
        except Exception as e:
            raise StorageError(f"Failed to save item: {e}")

    def get(self, item_id: str) -> Optional[T]:
        """获取单个项目"""
        data = self._load_data()
        for item_dict in data:
            if item_dict.get('id') == item_id:
                return self.model_class(**item_dict)
        return None

    def get_all(self) -> List[T]:
        """获取所有项目"""
        data = self._load_data()
        return [self.model_class(**item) for item in data]

    def delete(self, item_id: str) -> bool:
        """删除项目"""
        data = self._load_data()
        original_len = len(data)
        data = [item for item in data if item.get('id') != item_id]
        if len(data) < original_len:
            self._save_data(data)
            return True
        return False

    def update(self, item_id: str, data_update: Dict[str, Any]) -> Optional[T]:
        """更新项目"""
        data = self._load_data()
        for i, item_dict in enumerate(data):
            if item_dict.get('id') == item_id:
                item_dict.update(data_update)
                item_dict['updated_at'] = datetime.now().isoformat()
                data[i] = item_dict
                self._save_data(data)
                return self.model_class(**item_dict)
        return None

    def query(self, filters: Dict[str, Any]) -> List[T]:
        """查询项目"""
        data = self._load_data()
        results = []
        for item_dict in data:
            match = True
            for key, value in filters.items():
                if key not in item_dict or item_dict[key] != value:
                    match = False
                    break
            if match:
                results.append(self.model_class(**item_dict))
        return results


class SQLiteStorage(BaseStorage[T]):
    """SQLite 存储实现（可选，用于生产环境）"""

    def __init__(self, db_path: str, table_name: str, model_class: type):
        self.db_path = db_path
        self.table_name = table_name
        self.model_class = model_class
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """初始化数据库表"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id TEXT PRIMARY KEY,
                    data JSON NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            conn.close()

    def save(self, item: T) -> bool:
        """保存单个项目"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(f'''
                INSERT OR REPLACE INTO {self.table_name} (id, data, updated_at)
                VALUES (?, ?, ?)
            ''', (item.id, json.dumps(item.model_dump(), default=str), datetime.now()))
            conn.commit()
            conn.close()
            return True

    def get(self, item_id: str) -> Optional[T]:
        """获取单个项目"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT data FROM {self.table_name} WHERE id = ?', (item_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return self.model_class(**json.loads(row['data']))
        return None

    def get_all(self) -> List[T]:
        """获取所有项目"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT data FROM {self.table_name}')
        rows = cursor.fetchall()
        conn.close()
        return [self.model_class(**json.loads(row['data'])) for row in rows]

    def delete(self, item_id: str) -> bool:
        """删除项目"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(f'DELETE FROM {self.table_name} WHERE id = ?', (item_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return deleted

    def update(self, item_id: str, data_update: Dict[str, Any]) -> Optional[T]:
        """更新项目"""
        existing = self.get(item_id)
        if not existing:
            return None
        
        updated_data = {**existing.model_dump(), **data_update, 'updated_at': datetime.now()}
        self.save(self.model_class(**updated_data))
        return self.model_class(**updated_data)

    def query(self, filters: Dict[str, Any]) -> List[T]:
        """查询项目（简单实现，复杂查询建议使用 JSONStorage 或自定义 SQL）"""
        all_items = self.get_all()
        results = []
        for item in all_items:
            match = True
            item_dict = item.model_dump()
            for key, value in filters.items():
                if key not in item_dict or item_dict[key] != value:
                    match = False
                    break
            if match:
                results.append(item)
        return results


class StorageManager:
    """存储管理器 - 统一管理所有存储实例"""

    def __init__(self, base_dir: str = "data"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._storages: Dict[str, BaseStorage] = {}

    def get_storage(self, entity_type: str) -> BaseStorage:
        """获取或创建存储实例"""
        if entity_type not in self._storages:
            if entity_type == "skill":
                self._storages[entity_type] = JSONStorage(
                    str(self.base_dir / "skills.json"),
                    Skill
                )
            elif entity_type == "workflow":
                self._storages[entity_type] = JSONStorage(
                    str(self.base_dir / "workflows.json"),
                    Workflow
                )
            elif entity_type == "daily_log":
                self._storages[entity_type] = JSONStorage(
                    str(self.base_dir / "daily_logs.json"),
                    DailyLogEntry
                )
            elif entity_type == "execution":
                self._storages[entity_type] = JSONStorage(
                    str(self.base_dir / "executions.json"),
                    ExecutionContext
                )
            else:
                raise ValueError(f"Unknown entity type: {entity_type}")
        
        return self._storages[entity_type]

    def skill_storage(self) -> BaseStorage[Skill]:
        return self.get_storage("skill")

    def workflow_storage(self) -> BaseStorage[Workflow]:
        return self.get_storage("workflow")

    def daily_log_storage(self) -> BaseStorage[DailyLogEntry]:
        return self.get_storage("daily_log")

    def execution_storage(self) -> BaseStorage[ExecutionContext]:
        return self.get_storage("execution")
