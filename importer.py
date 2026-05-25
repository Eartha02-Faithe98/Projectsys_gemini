import pandas as pd
from database import get_session
from models import Project, Task, Resource, Assignment
from datetime import datetime

def validate_columns(df, mapping):
    """
    檢查必要欄位是否存在
    """
    required_fields = ['name', 'start_date', 'end_date']
    mapped_columns = [mapping.get(field) for field in required_fields]
    
    missing = [col for col in mapped_columns if col not in df.columns]
    if missing:
        return False, f"缺少必要欄位: {', '.join(missing)}"
    return True, ""

def process_excel_upload(file, project_id, mapping):
    """
    解析 Excel 檔案並寫入資料庫
    """
    try:
        df = pd.read_excel(file)
        
        # 驗證
        is_valid, error_msg = validate_columns(df, mapping)
        if not is_valid:
            return False, error_msg
            
        session = get_session()
        try:
            for index, row in df.iterrows():
                # 解析基本任務資料
                name = row.get(mapping.get('name'))
                if pd.isna(name): continue
                
                start_date = pd.to_datetime(row.get(mapping.get('start_date'))).date()
                end_date = pd.to_datetime(row.get(mapping.get('end_date'))).date()
                duration = (end_date - start_date).days
                
                # 取得其他非必填欄位
                stage = row.get(mapping.get('stage')) if mapping.get('stage') in df.columns else None
                if pd.isna(stage): stage = None
                
                deps = row.get(mapping.get('dependencies')) if mapping.get('dependencies') in df.columns else None
                
                # 處理 deps 字串
                if pd.isna(deps):
                    deps_str = ""
                else:
                    if isinstance(deps, (int, float)):
                        deps_str = str(int(deps))
                    else:
                        deps_str = str(deps)
                
                # 建立任務
                task = Task(
                    project_id=project_id,
                    name=str(name),
                    stage=str(stage) if stage else None,
                    start_date=start_date,
                    end_date=end_date,
                    duration=duration,
                    dependencies=deps_str
                )
                session.add(task)
                session.flush() # 取得 task.id
                
                # 解析並指派資源 (假設資源以逗號分隔的名字)
                resource_col = mapping.get('resources')
                if resource_col in df.columns:
                    res_str = row.get(resource_col)
                    if pd.notna(res_str):
                        res_names = [r.strip() for r in str(res_str).split(',') if r.strip()]
                        for r_name in res_names:
                            # 查詢資源是否存在，若無則自動建立 (MVP 階段方便測試)
                            resource = session.query(Resource).filter_by(name=r_name).first()
                            if not resource:
                                resource = Resource(name=r_name, type="Human")
                                session.add(resource)
                                session.flush()
                                
                            assignment = Assignment(task_id=task.id, resource_id=resource.id)
                            session.add(assignment)
            
            session.commit()
            return True, "匯入成功"
        except Exception as e:
            session.rollback()
            return False, f"寫入資料庫時發生錯誤: {str(e)}"
        finally:
            session.close()
            
    except Exception as e:
        return False, f"讀取 Excel 檔案失敗: {str(e)}"
