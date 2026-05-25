import pandas as pd
from datetime import timedelta
from database import get_session
from models import Task, Assignment, Resource, Project

def calculate_schedule(task_id, new_start_date):
    """
    更新任務的開始日期，並遞迴推移所有下游依賴任務 (Finish-to-Start)。
    """
    session = get_session()
    try:
        task = session.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False
        
        # 計算偏移天數
        old_start_date = task.start_date
        
        # 確保 new_start_date 是 datetime.date 類型
        if isinstance(new_start_date, pd.Timestamp):
            new_start_date = new_start_date.date()
            
        delta = new_start_date - old_start_date
        
        # 更新目前任務
        task.start_date = new_start_date
        task.end_date = task.end_date + delta
        session.commit()
        
        # 尋找下游任務並推移
        all_tasks = session.query(Task).filter(Task.project_id == task.project_id).all()
        task_dict = {t.id: t for t in all_tasks}
        
        queue = [task_id]
        while queue:
            current_id = queue.pop(0)
            current_task = task_dict[current_id]
            
            for t in all_tasks:
                if t.dependencies:
                    deps_str = str(t.dependencies).split(',')
                    deps = []
                    for x in deps_str:
                        if x.strip().isdigit():
                            deps.append(int(x.strip()))
                            
                    if current_id in deps:
                        # t 依賴於 current_task (Finish-to-Start)
                        if t.start_date <= current_task.end_date:
                            shift_delta = (current_task.end_date + timedelta(days=1)) - t.start_date
                            t.start_date = t.start_date + shift_delta
                            t.end_date = t.end_date + shift_delta
                            queue.append(t.id)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def detect_resource_conflicts():
    """
    掃描指派任務，找出同一個資源在同一天被指派超過1個任務的情況。
    回傳：列表包含 dict {resource_name, date, tasks}
    """
    session = get_session()
    try:
        assignments = session.query(Assignment).all()
        data = []
        for a in assignments:
            task = a.task
            resource = a.resource
            if task and resource:
                # 取得專案名稱
                project_name = task.project.name if task.project else "Unknown"
                data.append({
                    'resource_id': resource.id,
                    'resource_name': resource.name,
                    'task_name': f"[{project_name}] {task.name}",
                    'start_date': task.start_date,
                    'end_date': task.end_date
                })
        
        if not data:
            return []
            
        df = pd.DataFrame(data)
        
        expanded_data = []
        for _, row in df.iterrows():
            # 使用 pd.date_range 產生日期範圍
            date_range = pd.date_range(start=row['start_date'], end=row['end_date'])
            for d in date_range:
                expanded_data.append({
                    'resource_id': row['resource_id'],
                    'resource_name': row['resource_name'],
                    'date': d.date(),
                    'task_name': row['task_name']
                })
        
        if not expanded_data:
            return []
            
        expanded_df = pd.DataFrame(expanded_data)
        
        # 找出同一天被指派超過一個任務的資源
        grouped = expanded_df.groupby(['resource_id', 'resource_name', 'date'])['task_name'].apply(list).reset_index()
        conflicts = grouped[grouped['task_name'].apply(len) > 1]
        
        result = []
        for _, row in conflicts.iterrows():
            result.append({
                'resource_name': row['resource_name'],
                'date': row['date'],
                'tasks': row['task_name']
            })
            
        return result
    finally:
        session.close()
