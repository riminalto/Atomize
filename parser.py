import uuid

def _create_atomic_task(name: str, parent_chain: list, depends_on: str = None, is_late_task: bool = False) -> dict:
    """创建一个标准的原子任务对象。"""
    return {
        'id': str(uuid.uuid4()),
        'name': name.strip(),
        'parent_chain': parent_chain,
        'status': 'pending',
        'postponed_count': 0,
        'depends_on': depends_on,
        'is_late_task': is_late_task
    }

def _split_at_level(text: str, delimiter: str = ',') -> list:
    """在顶层按分隔符切分字符串，忽略括号/中括号内的分隔符。"""
    parts = []
    balance = 0
    start = 0
    for i, char in enumerate(text):
        if char in '([':
            balance += 1
        elif char in ')]':
            balance -= 1
        elif char == delimiter and balance == 0:
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    
    if balance != 0:
        raise ValueError("括号或中括号不匹配")
        
    return [p.strip() for p in parts if p.strip()]

def _parse_segment(segment: str, parent_chain: list, is_late_task: bool = False) -> list:
    """
    递归地解析一个任务片段。
    【核心修改】此函数现在能正确处理 "A-B-C(...)" 这样的链式父任务结构。
    """
    segment = segment.strip()
    
    try:
        first_bracket_index = min(
            segment.index(c) for c in '([' if c in segment
        )
    except ValueError:
        first_bracket_index = -1

    if first_bracket_index == -1:
        task_names = [name.strip() for name in segment.split('-') if name.strip()]
        if not task_names:
            return []

        created_tasks = []
        previous_task_id = None
        for name in task_names:
            new_task = _create_atomic_task(name, parent_chain, depends_on=previous_task_id, is_late_task=is_late_task)
            created_tasks.append(new_task)
            previous_task_id = new_task['id']
        return created_tasks

    else:
        prefix = segment[:first_bracket_index]
        last_hyphen_index = prefix.rfind('-')
        
        all_tasks = []
        last_precusor_id = None

        if last_hyphen_index != -1:
            precursor_names_str = prefix[:last_hyphen_index]
            # 解析 "A-B" 部分
            precursor_tasks = _parse_segment(precursor_names_str, parent_chain, is_late_task)
            if precursor_tasks:
                all_tasks.extend(precursor_tasks)
                last_precusor_id = precursor_tasks[-1]['id']

        parent_name_start = last_hyphen_index + 1
        task_name = prefix[parent_name_start:].strip()

        if not task_name:
            raise ValueError(f"无效的父任务格式，括号前缺少任务名: '{segment}'")
        
        last_bracket_index = len(segment) - 1
        if (segment[first_bracket_index] == '(' and segment[-1] != ')') or \
           (segment[first_bracket_index] == '[' and segment[-1] != ']'):
            raise ValueError(f"任务 '{task_name}' 的括号不匹配")
        
        children_string = segment[first_bracket_index + 1 : last_bracket_index]
        new_parent_chain = parent_chain + [task_name]
        
        children_tasks = _parse_children(children_string, new_parent_chain, parent_is_late=is_late_task)
        
        if children_tasks:
            for child in children_tasks:
                if child['depends_on'] is None and last_precusor_id is not None:
                    child['depends_on'] = last_precusor_id
            all_tasks.extend(children_tasks)
        
        return all_tasks


def _parse_children(children_string: str, parent_chain: list, parent_is_late: bool = False) -> list:
    """解析一个父任务的子任务字符串。"""
    if not children_string:
        return []

    child_segments = _split_at_level(children_string, ',')
    
    all_tasks = []
    late_tasks_segments = []

    for seg in child_segments:
        if seg.startswith('-'):
            late_tasks_segments.append(seg[1:])
        else:
            all_tasks.extend(_parse_segment(seg, parent_chain, is_late_task=parent_is_late))
    
    for seg in late_tasks_segments:
        all_tasks.extend(_parse_segment(seg, parent_chain, is_late_task=True))
        
    return all_tasks

def parse_task_string(input_string: str) -> list:
    """解析用户输入的完整任务规划字符串。"""
    if not input_string.strip():
        return []
    try:
        return _parse_children(input_string, [])
    except ValueError as e:
        raise ValueError(f"任务字符串格式错误: {e}")
    except Exception:
        raise ValueError("发生了未知的解析错误，请检查语法。")