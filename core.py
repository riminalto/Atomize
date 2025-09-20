# atomize/core.py

import os
import json
import csv
import random # 引入 random 模块
from datetime import datetime

import parser

# --- 常量定义 (无变化) ---
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
SESSION_FILE = os.path.join(DATA_DIR, 'session.json')
HISTORY_FILE = os.path.join(DATA_DIR, 'history.csv')
POINTS_BASE = 10
POINTS_POSTPONED_BONUS = 5

class TaskManager:
    """
    负责所有核心业务逻辑，包括任务状态管理、数据持久化和统计。
    """
    def __init__(self):
        self.tasks = []
        self.total_points = 0
        self.postponed_today_count = 0
        self.session_date = datetime.now().strftime('%Y-%m-%d')
        
        os.makedirs(DATA_DIR, exist_ok=True)
        self._load_session()

    # --- 以下方法到 get_next_task_info 之前均无变化 ---
    def _load_session(self):
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('date') == self.session_date:
                        self.tasks = data.get('tasks', [])
                        self.total_points = data.get('total_points', 0)
                        self.postponed_today_count = data.get('postponed_today_count', 0)
            except (json.JSONDecodeError, IOError):
                self._clear_session_file()

    def _save_session(self):
        session_data = {
            'date': self.session_date,
            'tasks': self.tasks,
            'total_points': self.total_points,
            'postponed_today_count': self.postponed_today_count,
        }
        with open(SESSION_FILE, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=4)

    def _save_to_history(self, task, points_earned, status='done'):
        file_exists = os.path.isfile(HISTORY_FILE)
        parent_chain_str = " > ".join(task['parent_chain'])
        row = {
            'timestamp': datetime.now().isoformat(timespec='seconds'),
            'task_name': task['name'],
            'parent_chain': parent_chain_str,
            'status': status,
            'was_postponed': 'yes' if task['postponed_count'] > 0 else 'no',
            'focus_points': points_earned
        }
        with open(HISTORY_FILE, 'a', newline='', encoding='utf-8') as f:
            fieldnames = row.keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

    def _clear_session_file(self):
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)

    def _reset_state(self):
        self.tasks = []
        self.total_points = 0
        self.postponed_today_count = 0
        self.session_date = datetime.now().strftime('%Y-%m-%d')
    
    def get_overdue_tasks(self) -> list:
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if data.get('date') != self.session_date:
                    return [t for t in data.get('tasks', []) if t['status'] == 'pending']
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def has_active_session(self):
        return bool(self.tasks and any(t['status'] == 'pending' for t in self.tasks))

    def start_new_day(self, task_string: str, overdue_tasks_to_merge: list = None):
        self._clear_session_file()
        self._reset_state()
        new_tasks = parser.parse_task_string(task_string)
        
        # 健壮性：合并隔夜任务时，也要确保它们是有效的任务对象
        merged_tasks = (overdue_tasks_to_merge or []) + new_tasks
        self.tasks = merged_tasks
        
        if not self.tasks:
            # 允许用户不输入任何任务（例如只想处理隔夜任务）
            # 仅当合并后仍然没有任务才报错
            if not overdue_tasks_to_merge:
                 raise ValueError("解析后的任务列表为空，请检查输入格式。")
        self._save_session()

    # --- 核心修改：实现结构化随机调度 ---
    def get_next_task_info(self):
        """
        获取下一个可执行的任务。
        该方法实现了“结构化随机”逻辑：
        1. 优先从所有“常规任务”中选择。
        2. 仅当所有“常规任务”完成后，才开始从“末尾任务”中选择。
        3. 在每个阶段，只选择那些“前置依赖已完成”的任务。
        4. 从所有可执行的任务中随机选择一个进行推送。
        """
        pending_tasks = [t for t in self.tasks if t['status'] == 'pending']
        if not pending_tasks:
            self._clear_session_file()
            return None

        # 1. 创建已完成任务ID的集合，用于高效查询依赖关系
        done_task_ids = {t['id'] for t in self.tasks if t['status'] != 'pending'}

        # 2. 将待办任务分为“常规”和“末尾”两类
        normal_pending = [t for t in pending_tasks if not t.get('is_late_task', False)]
        late_pending = [t for t in pending_tasks if t.get('is_late_task', False)]
        
        # 3. 确定当前阶段要处理的任务池 (常规任务优先)
        target_pool = normal_pending
        # 如果常规任务已经全部完成，则切换到末尾任务池
        if not target_pool:
            target_pool = late_pending

        # 4. 从目标池中筛选出所有可执行的任务（依赖已解除）
        available_tasks = [
            task for task in target_pool 
            if not task.get('depends_on') or task.get('depends_on') in done_task_ids
        ]

        # 5. 从可用任务池中随机选择一个任务
        if not available_tasks:
            # 健壮性：如果没有可执行的任务，有两种可能：
            # a) 所有任务都已完成（最开始的 pending_tasks 检查会处理）。
            # b) 任务之间存在循环依赖或死锁。我们的解析器设计上避免了这种情况，
            #    但保留此检查可以防止未来可能出现的bug。
            #    此时返回 None，主循环会显示“所有任务已完成”。
            return None
        
        current_task = random.choice(available_tasks)
        
        done_count = len(done_task_ids)
        return {'task': current_task, 'current_num': done_count + 1, 'total_num': len(self.tasks)}

    # --- 以下方法均无变化 ---
    def complete_task(self, task_id: str):
        for task in self.tasks:
            if task['id'] == task_id:
                points_earned = POINTS_BASE + (POINTS_POSTPONED_BONUS if task['postponed_count'] > 0 else 0)
                self.total_points += points_earned
                task['status'] = 'done'
                self._save_to_history(task, points_earned, status='done')
                self._save_session()
                return {'success': True, 'message': f"+{points_earned} 专注点！任务 “{task['name']}” 已完成。"}
        return {'success': False, 'message': "错误：找不到指定任务。"}

    def postpone_task(self, task_id: str):
        task_index = next((i for i, t in enumerate(self.tasks) if t['id'] == task_id), -1)
        if task_index == -1: return {'success': False, 'message': "错误：找不到指定任务。"}
        
        task_to_move = self.tasks[task_index]
        
        # 健壮性：推迟任务时，将其插入到列表末尾，但要确保它在所有已完成任务之后，待办任务之中
        pending_tasks_start_index = next((i for i, t in enumerate(self.tasks) if t['status'] == 'pending'), len(self.tasks))
        
        if task_to_move['postponed_count'] > 0:
            return {'success': False, 'message': "[!] 此任务已被推迟过一次，请立即完成！"}
        
        task_to_move['postponed_count'] += 1
        self.postponed_today_count += 1
        
        self.tasks.pop(task_index)
        self.tasks.append(task_to_move) # 简单地移动到列表最后即可，调度逻辑会自动处理
        self._save_session()
        return {'success': True, 'message': "任务已推迟。它将在稍后再次出现。"}

    def cancel_task(self, task_id: str):
        for task in self.tasks:
            if task['id'] == task_id:
                task['status'] = 'skipped'
                self._save_to_history(task, 0, status='skipped')
                self._save_session()
                return {'success': True, 'message': f"任务 “{task['name']}” 已取消。"}
        return {'success': False, 'message': "错误：找不到指定任务。"}

    def edit_task(self, task_id: str, new_name: str):
        if not new_name.strip(): return {'success': False, 'message': "任务名不能为空。"}
        for task in self.tasks:
            if task['id'] == task_id:
                task['name'] = new_name.strip()
                self._save_session()
                return {'success': True, 'message': "任务已更新。"}
        return {'success': False, 'message': "错误：找不到指定任务。"}

    def add_task_after(self, current_task_id: str, new_task_name: str):
        if not new_task_name.strip(): return {'success': False, 'message': "任务名不能为空。"}
        current_task_index = next((i for i, t in enumerate(self.tasks) if t['id'] == current_task_id), -1)
        if current_task_index == -1: return {'success': False, 'message': "错误：找不到当前任务。"}
        current_task = self.tasks[current_task_index]
        
        # 新增的任务是常规任务，无依赖
        new_task = parser._create_atomic_task(new_task_name, current_task['parent_chain'])
        
        self.tasks.insert(current_task_index + 1, new_task)
        self._save_session()
        return {'success': True, 'message': f"新任务 “{new_task_name}” 已添加。"}

    def split_task(self, task_id: str, sub_task_string: str):
        if not sub_task_string.strip(): return {'success': False, 'message': "子任务描述不能为空。"}
        task_index = next((i for i, t in enumerate(self.tasks) if t['id'] == task_id), -1)
        if task_index == -1: return {'success': False, 'message': "错误：找不到要拆分的任务。"}
        
        original_task = self.tasks[task_index]
        new_parent_chain = original_task['parent_chain'] + [original_task['name']]
        
        try:
            # 拆分出的子任务，其 late 状态继承自父任务
            sub_tasks = parser._parse_children(sub_task_string, new_parent_chain, parent_is_late=original_task.get('is_late_task', False))
            if not sub_tasks: raise ValueError("未解析出任何子任务。")
        except ValueError as e:
            return {'success': False, 'message': f"子任务格式错误: {e}"}
            
        self.tasks.pop(task_index)
        self.tasks[task_index:task_index] = sub_tasks
        self._save_session()
        return {'success': True, 'message': f"任务已成功拆分为 {len(sub_tasks)} 个子任务。"}

    def get_summary(self):
        if self.has_active_session():
            completed_count = len([t for t in self.tasks if t['status'] == 'done'])
            return {'date': self.session_date, 'completed_count': completed_count, 'total_points': self.total_points, 'postponed_count': self.postponed_today_count}
        completed_count, points, postponed = 0, 0, 0
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['timestamp'].startswith(self.session_date):
                        if row['status'] == 'done':
                            completed_count += 1
                            points += int(row['focus_points'])
                        # 修复：总结报告中的 postponed 计数应基于历史记录中的 was_postponed 字段
                        if row['was_postponed'] == 'yes':
                            # 这可能会重复计算，更好的方式是计算推迟过的任务数
                            pass # 暂时维持原逻辑，但需要注意
        # 更好的 postponed 计数
        postponed_tasks_today = set()
        if os.path.exists(HISTORY_FILE):
             with open(HISTORY_FILE, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['timestamp'].startswith(self.session_date) and row['was_postponed'] == 'yes':
                         postponed_tasks_today.add(row['task_name'] + row['parent_chain'])
        
        return {'date': self.session_date, 'completed_count': completed_count, 'total_points': points, 'postponed_count': len(postponed_tasks_today)}