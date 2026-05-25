import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
from datetime import datetime, date
import os
import io

from database import init_db, get_session
from models import Project, Task, Resource, Assignment
from logic import calculate_schedule, detect_resource_conflicts
from importer import process_excel_upload

# 初始化資料庫
init_db()

st.set_page_config(page_title="科技業硬體研發專案管理系統", layout="wide")

# Sidebar 導覽列
st.sidebar.title("硬體研發 PM 系統")
menu = st.sidebar.radio("導覽", [
    "Dashboard 總覽", 
    "專案管理 (Gantt View)", 
    "Excel 匯入器", 
    "資源負載圖", 
    "基礎資料庫"
])

session = get_session()

def create_sample_excel():
    df = pd.DataFrame({
        "任務名稱": ["EVT Phase Start", "PCBA Layout", "PCBA Fabrication", "SMT", "Board Bring-up", "EVT Review"],
        "階段": ["EVT", "EVT", "EVT", "EVT", "EVT", "EVT"],
        "開始日期": ["2023-11-01", "2023-11-02", "2023-11-10", "2023-11-20", "2023-11-23", "2023-11-30"],
        "結束日期": ["2023-11-01", "2023-11-09", "2023-11-19", "2023-11-22", "2023-11-29", "2023-11-30"],
        "前置任務ID": ["", "1", "2", "3", "4", "5"],
        "負責人/資源": ["PM_John", "EE_Alice", "Vendor_A", "Factory_B", "EE_Alice, FW_Bob", "PM_John, EE_Alice"]
    })
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    processed_data = output.getvalue()
    return processed_data

if menu == "Dashboard 總覽":
    st.title("Dashboard 總覽")
    projects = session.query(Project).all()
    tasks = session.query(Task).count()
    resources = session.query(Resource).count()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("總專案數", len(projects))
    col2.metric("總任務數", tasks)
    col3.metric("資源數", resources)
    
    st.subheader("專案列表")
    if projects:
        proj_data = []
        for p in projects:
            proj_data.append({
                "專案 ID": p.id,
                "專案名稱": p.name,
                "專案編號": p.code,
                "PM": p.pm_name,
                "目標日期": p.target_date
            })
        st.dataframe(pd.DataFrame(proj_data), use_container_width=True)
    else:
        st.info("目前沒有專案。請到「基礎資料庫」建立新專案。")

elif menu == "專案管理 (Gantt View)":
    st.title("專案管理 (Gantt View)")
    projects = session.query(Project).all()
    if not projects:
        st.warning("請先建立專案！")
    else:
        proj_options = {p.name: p.id for p in projects}
        selected_proj_name = st.selectbox("選擇專案", list(proj_options.keys()))
        selected_proj_id = proj_options[selected_proj_name]
        
        tasks = session.query(Task).filter(Task.project_id == selected_proj_id).order_by(Task.start_date).all()
        
        if not tasks:
            st.info("此專案目前沒有任務，請到「Excel 匯入器」匯入。")
        else:
            # 繪製甘特圖
            df_gantt = []
            for t in tasks:
                df_gantt.append(dict(
                    Task=t.name,
                    Start=t.start_date,
                    Finish=t.end_date,
                    Resource=t.stage if t.stage else "Task",
                    ID=t.id
                ))
            
            if df_gantt:
                fig = ff.create_gantt(df_gantt, index_col='Resource', title=f"{selected_proj_name} 甘特圖", show_colorbar=True, group_tasks=True)
                # fig.update_layout(xaxis_type='category')
                st.plotly_chart(fig, use_container_width=True)
            
            # 手動調整任務時間
            st.subheader("任務調整")
            task_options = {f"[{t.id}] {t.name}": t.id for t in tasks}
            selected_task_name = st.selectbox("選擇要調整的任務", list(task_options.keys()))
            selected_task_id = task_options[selected_task_name]
            
            task_to_edit = session.query(Task).filter(Task.id == selected_task_id).first()
            new_start_date = st.date_input("新的開始日期", value=task_to_edit.start_date)
            
            if st.button("更新並連動計算"):
                try:
                    calculate_schedule(selected_task_id, new_start_date)
                    st.success("更新成功！受影響的後續任務已自動推移。")
                    st.rerun()
                except Exception as e:
                    st.error(f"更新失敗: {e}")

elif menu == "Excel 匯入器":
    st.title("Excel 智慧匯入器")
    st.markdown("下載範本填寫後，上傳以自動建立 WBS。")
    
    st.download_button(
        label="📥 下載 Excel 範本",
        data=create_sample_excel(),
        file_name="wbs_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    projects = session.query(Project).all()
    if not projects:
        st.warning("請先到「基礎資料庫」建立至少一個專案。")
    else:
        proj_options = {p.name: p.id for p in projects}
        selected_proj_name = st.selectbox("選擇要匯入的專案", list(proj_options.keys()))
        selected_proj_id = proj_options[selected_proj_name]
        
        uploaded_file = st.file_uploader("上傳 Excel 檔案", type=['xlsx', 'xls'])
        
        if uploaded_file is not None:
            # 簡單預覽
            df_preview = pd.read_excel(uploaded_file)
            st.write("資料預覽:", df_preview.head())
            
            st.subheader("欄位對應 (Mapping)")
            col1, col2 = st.columns(2)
            cols = df_preview.columns.tolist()
            
            with col1:
                name_col = st.selectbox("任務名稱欄位", cols, index=cols.index("任務名稱") if "任務名稱" in cols else 0)
                start_col = st.selectbox("開始日期欄位", cols, index=cols.index("開始日期") if "開始日期" in cols else 0)
                end_col = st.selectbox("結束日期欄位", cols, index=cols.index("結束日期") if "結束日期" in cols else 0)
            with col2:
                stage_col = st.selectbox("階段欄位 (可選)", ["(無)"] + cols, index=cols.index("階段")+1 if "階段" in cols else 0)
                deps_col = st.selectbox("前置任務ID欄位 (可選)", ["(無)"] + cols, index=cols.index("前置任務ID")+1 if "前置任務ID" in cols else 0)
                res_col = st.selectbox("資源/負責人欄位 (可選)", ["(無)"] + cols, index=cols.index("負責人/資源")+1 if "負責人/資源" in cols else 0)
            
            if st.button("執行匯入"):
                mapping = {
                    'name': name_col,
                    'start_date': start_col,
                    'end_date': end_col,
                }
                if stage_col != "(無)": mapping['stage'] = stage_col
                if deps_col != "(無)": mapping['dependencies'] = deps_col
                if res_col != "(無)": mapping['resources'] = res_col
                
                with st.spinner("匯入中..."):
                    success, msg = process_excel_upload(uploaded_file, selected_proj_id, mapping)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

elif menu == "資源負載圖":
    st.title("資源負載與衝突預警")
    
    st.markdown("偵測跨專案的資源過載狀況（同一資源在同一日被指派超過一項任務）")
    
    if st.button("掃描衝突"):
        conflicts = detect_resource_conflicts()
        if not conflicts:
            st.success("目前沒有偵測到資源衝突。")
        else:
            st.error(f"偵測到 {len(conflicts)} 筆資源衝突！")
            df_conflicts = pd.DataFrame(conflicts)
            df_conflicts['date'] = df_conflicts['date'].astype(str)
            df_conflicts['tasks'] = df_conflicts['tasks'].apply(lambda x: ", ".join(x))
            
            st.dataframe(df_conflicts, use_container_width=True)
            
            # Heatmap 呈現
            # 準備熱圖資料
            # 取得所有 assignments
            assignments = session.query(Assignment).all()
            if assignments:
                heatmap_data = []
                for a in assignments:
                    t = a.task
                    r = a.resource
                    if t and r:
                        dr = pd.date_range(t.start_date, t.end_date)
                        for d in dr:
                            heatmap_data.append({'Resource': r.name, 'Date': d.date(), 'Load': 1})
                
                df_hm = pd.DataFrame(heatmap_data)
                df_hm_grouped = df_hm.groupby(['Resource', 'Date'])['Load'].sum().reset_index()
                
                fig = px.density_heatmap(df_hm_grouped, x="Date", y="Resource", z="Load", 
                                         color_continuous_scale="Reds", title="資源負載熱圖 (越紅表示越過載)")
                st.plotly_chart(fig, use_container_width=True)

elif menu == "基礎資料庫":
    st.title("基礎資料管理")
    
    tab1, tab2 = st.tabs(["專案管理", "資源管理"])
    
    with tab1:
        st.subheader("新增專案")
        with st.form("add_project"):
            p_name = st.text_input("專案名稱")
            p_code = st.text_input("專案編號")
            p_pm = st.text_input("負責 PM")
            p_date = st.date_input("目標上市日期")
            
            if st.form_submit_button("新增專案"):
                if p_name and p_code:
                    new_p = Project(name=p_name, code=p_code, pm_name=p_pm, target_date=p_date)
                    session.add(new_p)
                    try:
                        session.commit()
                        st.success("專案新增成功！")
                        st.rerun()
                    except Exception as e:
                        session.rollback()
                        st.error(f"新增失敗 (編號可能重複): {e}")
                else:
                    st.warning("請填寫專案名稱與編號。")
                    
    with tab2:
        st.subheader("資源列表")
        resources = session.query(Resource).all()
        if resources:
            r_data = [{"ID": r.id, "名稱": r.name, "類型": r.type, "部門": r.department} for r in resources]
            st.dataframe(pd.DataFrame(r_data), use_container_width=True)
            
        st.subheader("新增資源")
        with st.form("add_resource"):
            r_name = st.text_input("資源名稱")
            r_type = st.selectbox("資源類型", ["Human", "Equipment"])
            r_dept = st.text_input("所屬部門")
            
            if st.form_submit_button("新增資源"):
                if r_name:
                    new_r = Resource(name=r_name, type=r_type, department=r_dept)
                    session.add(new_r)
                    session.commit()
                    st.success("資源新增成功！")
                    st.rerun()
                else:
                    st.warning("請填寫資源名稱。")

session.close()
