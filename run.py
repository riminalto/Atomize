# atomize/run.py

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import core
import display

def run_execution_loop(task_manager: core.TaskManager):
    """执行任务的核心循环，支持动态修改。"""
    while True:
        task_info = task_manager.get_next_task_info()
        
        if not task_info:
            display.show_message("所有任务已完成！")
            time.sleep(2)
            break

        current_task = task_info['task']
        
        display.clear_screen()
        display.show_current_task(current_task, task_info['current_num'], task_info['total_num'])
        
        action = input("\n> ").lower().strip()

        result = None
        # --- 基本操作 ---
        if action in ['d', 'done']:
            result = task_manager.complete_task(current_task['id'])
        elif action in ['p', 'postpone']:
            result = task_manager.postpone_task(current_task['id'])
        elif action in ['q', 'quit']:
            display.show_message("任务执行已暂停，返回主菜单。")
            time.sleep(1.5)
            break
        
        # --- 动态管理操作 ---
        elif action in ['s', 'split']:
            sub_task_str = input("拆分子任务 (使用 , - () [] 规划): ")
            result = task_manager.split_task(current_task['id'], sub_task_str)
        elif action in ['a', 'add']:
            new_task_name = input("输入要添加的新任务名: ")
            result = task_manager.add_task_after(current_task['id'], new_task_name)
        elif action in ['e', 'edit']:
            new_name = input(f"修改任务名 [{current_task['name']}]: ")
            result = task_manager.edit_task(current_task['id'], new_name or current_task['name'])
        
        # --- 【指令优化】将 'x' (skip) 更改为 'c' (cancel) ---
        elif action in ['c', 'cancel']:
            confirm = input(f"确认取消任务 “{current_task['name']}” 吗? 此操作无法撤销 [y/N]: ").lower()
            if confirm == 'y':
                result = task_manager.cancel_task(current_task['id']) # 调用新方法
            else:
                display.show_message("操作已取消。", is_warning=True)
                time.sleep(1.5)
                continue
        else:
            display.show_message("无效操作。", is_warning=True)
            time.sleep(1.5)
            continue
        
        if result:
            display.show_message(result['message'], is_warning=(not result.get('success', False)))
            time.sleep(1.5 if result.get('success', False) else 2.5)


def main():
    """程序主函数，负责显示主菜单和分派用户操作。"""
    while True:
        display.clear_screen()
        display.show_main_menu()
        choice = input("> ").strip()
        
        if choice == '1':
            task_manager = core.TaskManager()
            overdue_tasks = task_manager.get_overdue_tasks()
            overdue_choice = '2'

            if overdue_tasks:
                display.show_overdue_prompt(overdue_tasks)
                overdue_choice = input("> ").strip()

            if overdue_choice == '3':
                continue
            
            display.clear_screen()
            display.show_message("规划或覆盖今天的任务规划")
            task_string = input("> ")
            
            if not task_string and overdue_choice != '1':
                display.show_message("输入不能为空，请重新开始。", is_warning=True)
                time.sleep(2)
                continue

            try:
                tasks_to_merge = overdue_tasks if overdue_choice == '1' else []
                task_manager.start_new_day(task_string, tasks_to_merge)
                display.show_message("任务解析成功，即将开始执行...")
                time.sleep(1)
                run_execution_loop(task_manager)
            except ValueError as e:
                display.show_message(f"任务解析失败: {e}", is_warning=True)
                time.sleep(3)

        elif choice == '2':
            task_manager = core.TaskManager()
            if task_manager.has_active_session():
                display.show_message("加载任务成功，继续执行...")
                time.sleep(1)
                run_execution_loop(task_manager)
            else:
                display.show_message("没有找到今天的任务记录，请先开始新的一天。", is_warning=True)
                time.sleep(2)

        elif choice == '3':
            task_manager = core.TaskManager()
            summary = task_manager.get_summary()
            display.clear_screen()
            display.show_summary(summary)
            input("\n按回车键返回主菜单...")

        elif choice == '4':
            display.show_message("保持专注，下次再见。")
            break
        else:
            display.show_message("无效输入，请输入 1-4 之间的数字。", is_warning=True)
            time.sleep(1.5)

if __name__ == "__main__":
    main()