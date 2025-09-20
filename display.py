# atomize/display.py

import os
import sys

class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    CYAN = '\033[96m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    MAGENTA = '\033[95m'
    DIM = '\033[2m'

def clear_screen():
    """根据操作系统类型清空终端屏幕。"""
    os.system('cls' if os.name == 'nt' else 'clear')

def _colorize(text: str, color_code: str) -> str:
    """给文本添加颜色。"""
    return f"{color_code}{text}{Colors.RESET}"

ASCII_LOGO = r"""   ___  __             _        
  / _ |/ /____  __ _  (_)__ ___ 
 / __ / __/ _ \/  ' \/ /_ // -_)
/_/ |_\__/\___/_/_/_/_//__/\__/ """

def show_main_menu():
    """显示主菜单界面。"""
    print(_colorize(ASCII_LOGO, Colors.BOLD))
    print("\n请选择操作：")
    print(f"[{_colorize('1', Colors.CYAN)}] 规划")
    print(f"[{_colorize('2', Colors.CYAN)}] 继续")
    print(f"[{_colorize('3', Colors.CYAN)}] 查看")
    print(f"[{_colorize('4', Colors.CYAN)}] 退出")

def show_current_task(task: dict, current_num: int, total_num: int):
    """格式化并显示当前正在执行的任务。"""
    context_path = ""
    if task.get('parent_chain'):
        context_path = " > ".join(task['parent_chain']) + " > "
    
    progress_bar = f"[{current_num}/{total_num}]"
    task_header = f"{progress_bar} {context_path}{_colorize(task['name'], Colors.BOLD)}"
    
    header_len = len(progress_bar) + len(context_path) + len(task['name']) + 2
    print("-" * header_len)
    print(task_header)
    print("-" * header_len)
    
    # --- 【UI更新】将操作指令整合到一行 ---
    core_actions = [
        f"[{_colorize('d', Colors.GREEN)}]one",
        f"[{_colorize('p', Colors.YELLOW)}]ostpone",
        f"[{_colorize('q', Colors.RED)}]uit"
    ]
    edit_actions = [
        f"[{_colorize('s', Colors.CYAN)}]plit",
        f"[{_colorize('a', Colors.CYAN)}]dd",
        f"[{_colorize('e', Colors.CYAN)}]dit",
        f"[{_colorize('c', Colors.MAGENTA)}]ancel"
    ]
    
    actions_line = " | ".join(core_actions) + "  " + _colorize("::", Colors.DIM) + "  " + " | ".join(edit_actions)
    print(f"\n操作: {actions_line}")


def show_summary(summary_data: dict):
    """显示当日的总结报告。"""
    date = summary_data.get('date', '未知日期')
    completed = summary_data.get('completed_count', 0)
    points = summary_data.get('total_points', 0)
    postponed = summary_data.get('postponed_count', 0)
    
    header = f"今日总结 ({date})"
    print(_colorize(header, Colors.BOLD))
    print("-" * len(header))
    print(f"已完成任务数: {_colorize(completed, Colors.CYAN)}")
    print(f"总获得专注点: {_colorize(str(points) + ' FP', Colors.GREEN)}")
    print(f"推迟任务次数: {_colorize(postponed, Colors.YELLOW)}")
    
    if completed > 0:
        print("\n干得漂亮！明天继续保持专注。")
    else:
        print("\n今天还没有完成任务，明天开始吧！")
        
def show_message(message: str, is_warning: bool = False):
    """显示一条普通消息或警告消息。"""
    color = Colors.YELLOW if is_warning else Colors.GREEN
    print(_colorize(message, color))

def show_overdue_prompt(overdue_tasks: list):
    """显示处理隔夜任务的提示。"""
    clear_screen()
    count = len(overdue_tasks)
    print(_colorize(f"检测到您昨天有 {count} 个任务未完成：", Colors.YELLOW))
    for task in overdue_tasks[:5]: # 最多显示5个
        parent_chain = " > ".join(task['parent_chain'])
        print(f"  - {parent_chain} > {task['name']}" if parent_chain else f"  - {task['name']}")
    if count > 5:
        print(f"  ...等 {count - 5} 个任务")

    print("\n请选择如何处理：")
    print(f"[{_colorize('1', Colors.CYAN)}] 合并")
    print(f"[{_colorize('2', Colors.CYAN)}] 抛弃")
    print(f"[{_colorize('3', Colors.CYAN)}] 取消")