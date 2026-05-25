這是一份根據您的 PRD 內容，專為初學者與 AI 輔助開發優化的**精簡版系統設計文件 (SDD)**。

---

# 系統設計文件 (SDD)：科技業硬體研發專案管理系統 (MVP)

| 文件版本 | 狀態 | 作者 | 日期 |
| :--- | :--- | :--- | :--- |
| v1.0 | 草案 | 系統架構師 | 2023-10-27 |

---

## 1. 簡介

### 1.1 專案概述
本專案旨在開發一個專為硬體研發設計的輕量化專案管理系統。透過結構化的 Stage-Gate 流程管理、Excel 智慧匯入與資源衝突預警功能，解決硬體開發中時程連動複雜與資源分配混亂的痛點，取代傳統且難以維護的 Excel 管理模式。

### 1.2 系統目標
*   **結構化排程**：建立符合 NPI (New Product Introduction) 流程的 WBS 結構。
*   **自動化計算**：實作任務依賴邏輯，自動計算關鍵路徑與日期連動。
*   **高效能匯入**：提供 Excel 批次處理能力，大幅降低 PM 資料輸入成本。
*   **資源透明化**：可視化呈現工程師與實驗設備的負載狀態。
*   **衝突預警**：主動偵測並標示跨專案的資源過載衝突。

### 1.3 技術選型
本系統採用全 Python 生態系，以降低開發複雜度並提高 AI 程式碼生成的準確度：
*   **程式語言**：Python 3.9+
*   **Web UI 框架**：**Streamlit** (提供即時的數據互動介面)
*   **資料處理**：Pandas, Openpyxl (處理 Excel 匯入與邏輯運算)
*   **資料庫**：SQLite (單一檔案資料庫，無需安裝)
*   **資料庫 ORM**：SQLAlchemy (簡化資料庫操作)
*   **可視化庫**：Plotly (用於渲染動態甘特圖與資源熱圖)

---

## 2. 系統架構與運作流程

### 2.1 整體架構
系統採用單機 Web 架構，使用者透過瀏覽器存取由 Streamlit 驅動的介面，後端邏輯與 SQLite 資料庫直接運行於本地環境。

```
[使用者瀏覽器] <-> [Streamlit 互動介面] <-> [核心業務邏輯 (Python)] <-> [SQLAlchemy ORM] <-> [SQLite 資料庫 (.db)]
                                                ^
                                                |
                                         [Excel 檔案匯入]
```

### 2.2 運作流程詳解
1.  **初始化**：系統啟動時，SQLAlchemy 檢查 SQLite 資料庫是否存在，若無則自動建立資料表。
2.  **資料匯入**：PM 上傳 Excel 檔案，系統透過 Pandas 解析資料，進行格式預檢（Data Validation），並寫入資料庫。
3.  **邏輯運算**：系統根據任務間的依賴關係 (Dependency) 計算關鍵路徑，並掃描所有資源分配狀況。
4.  **視覺化呈現**：Streamlit 讀取資料庫數據，動態生成互動式甘特圖與資源負荷地圖。
5.  **衝突提示**：若偵測到同一日期下資源使用率 > 100%，介面即時顯示紅字警示。

---

## 3. 核心模組設計

### 3.1 檔案結構建議
*   `app.py`：主程式與 UI 佈局。
*   `models.py`：定義資料庫結構 (SQLAlchemy Models)。
*   `database.py`：資料庫連線與增刪查改 (CRUD) 封裝。
*   `logic.py`：關鍵路徑演算法與資源衝突掃描邏輯。
*   `importer.py`：Excel 解析與資料清洗。

### 3.2 模組職責說明
| 模組名稱 | 職責 | 核心功能 |
| :--- | :--- | :--- |
| `models.py` | 定義資料結構 | 定義 Project, Task, Resource, Assignment 資料表 |
| `logic.py` | 業務逻辑計算 | `calculate_critical_path()`, `detect_conflicts()` |
| `importer.py` | 外部資料處理 | `process_excel_upload()`, `validate_columns()` |
| `app.py` | UI 渲染與互動 | `render_gantt_chart()`, `render_resource_heatmap()` |

---

## 4. 資料庫設計

### 4.1 資料庫選型
使用 **SQLite**。其優點為無需配置伺服器、資料隨檔案移動，非常適合 MVP 階段與本地端快速部署。

### 4.2 資料表設計

#### Table: `projects` (專案基本資訊)
| 欄位名稱 | 資料型態 | 說明 | 備註 |
| :--- | :--- | :--- | :--- |
| id | INTEGER | 唯一識別碼 | 主鍵 |
| name | VARCHAR | 專案名稱 | |
| code | VARCHAR | 專案編號 | 唯一值 |
| pm_name | VARCHAR | 負責 PM | |
| target_date | DATE | 目標上市日期 | |

#### Table: `tasks` (工作任務)
| 欄位名稱 | 資料型態 | 說明 | 備註 |
| :--- | :--- | :--- | :--- |
| id | INTEGER | 唯一識別碼 | 主鍵 |
| project_id | INTEGER | 所屬專案 ID | 外鍵 |
| name | VARCHAR | 任務名稱 | |
| stage | VARCHAR | 所屬階段 | EVT/DVT/PVT/MP |
| start_date | DATE | 開始日期 | |
| end_date | DATE | 結束日期 | |
| duration | INTEGER | 持續天數 | |
| dependencies | VARCHAR | 前置任務 ID | 逗號分隔字串 |
| is_milestone | BOOLEAN | 是否為里程碑 | |

#### Table: `resources` (人員與設備資源)
| 欄位名稱 | 資料型態 | 說明 | 備註 |
| :--- | :--- | :--- | :--- |
| id | INTEGER | 唯一識別碼 | 主鍵 |
| name | VARCHAR | 資源名稱 | |
| type | VARCHAR | 資源類型 | Human / Equipment |
| department | VARCHAR | 所屬部門 | |

#### Table: `assignments` (資源指派關聯)
| 欄位名稱 | 資料型態 | 說明 | 備註 |
| :--- | :--- | :--- | :--- |
| id | INTEGER | 唯一識別碼 | 主鍵 |
| task_id | INTEGER | 任務 ID | 外鍵 |
| resource_id | INTEGER | 資源 ID | 外鍵 |

---

## 5. 使用者介面與互動規劃

### 5.1 頁面結構
系統採用 Streamlit Sidebar 導覽列：
1.  **Dashboard 總覽**：顯示專案清單與狀態統計。
2.  **專案管理 (Gantt View)**：選擇特定專案，查看互動式甘特圖，並可手動編輯任務。
3.  **Excel 匯入器**：上傳 WBS Excel 檔案，進行欄位對照與資料預檢。
4.  **資源負載圖**：跨專案查看所有資源的 Heatmap，並標示衝突點。
5.  **基礎資料管理**：人員與設備的新增/修改/刪除。

### 5.2 核心互動流程
1.  **匯入專案**：用戶進入「Excel 匯入器」 -> 上傳檔案 -> 系統顯示欄位對照清單 -> 確認無誤後點擊「執行匯入」。
2.  **調整時程**：在甘特圖頁面調整某一任務日期 -> 系統自動根據 `dependencies` 欄位更新後續任務日期 -> 重新計算關鍵路徑並高亮顯示。
3.  **檢查衝突**：切換至「資源負載圖」 -> 系統掃描所有指派紀錄 -> 若同一人在同一天有多個任務，該區塊顯示深紅色並跳出驚嘆號。

---

## 6. 功能函數設計 (核心邏輯)

### 6.1 `calculate_schedule(task_id, new_start_date)`
*   **輸入**：任務 ID，新的開始日期。
*   **職責**：遞迴更新所有下游任務 (Downstream Tasks) 的日期。
*   **內部邏輯**：
    1.  更新目標任務的 `start_date` 與 `end_date`。
    2.  查找所有以該任務為 `dependencies` 的子任務。
    3.  同步推移子任務日期，確保滿足 FS (Finish-to-Start) 關係。

### 6.2 `detect_resource_conflicts()`
*   **職責**：掃描全系統任務與指派關聯。
*   **輸出**：衝突列表 (Resource, Date, Conflict_Tasks)。
*   **內部邏輯**：使用 Pandas `resample` 功能，將每個指派任務展開為日期數組，加總每日負載，篩選出數值 > 1.0 (或 8 小時) 的紀錄。

---

## 7. 錯誤處理策略

| 錯誤情境 | 處理策略 | UI 呈現 |
| :--- | :--- | :--- |
| Excel 欄位缺失 | 停止匯入，列出缺少的必要欄位名稱 | 紅色錯誤 Banner 並提示導引 |
| 循環依賴 (Cycle) | 偵測到 A->B->A 的關係時阻止儲存 | 彈出式警告視窗「偵測到邏輯循環」 |
| 日期邏輯錯誤 | 結束日期早於開始日期 | 自動將結束日期校正為開始日期 + 1 天 |
| 資源過載 | 指派時資源已佔用 | 在甘特圖上顯示紅色感嘆號圖標 |

---

## 8. 實作路徑 (Implementation Roadmap)

### 8.1 環境建置與依賴安裝
```bash
# 建立專案
mkdir hw_pm_system
cd hw_pm_system
python -m venv venv
source venv/bin/activate  # macOS/Linux
# .\venv\Scripts\activate # Windows
```

**requirements.txt:**
```text
streamlit
pandas
sqlalchemy
openpyxl
plotly
```

**安裝指令:**
```bash
pip install -r requirements.txt
```

### 8.2 資料庫模組開發 (`models.py`, `database.py`)
1.  使用 SQLAlchemy 定義第 4 節所述的四個資料表。
2.  編寫 `init_db()` 函數，在程式啟動時呼叫 `Base.metadata.create_all(engine)`。

### 8.3 核心業務邏輯開發 (`logic.py`)
1.  **時程引擎**：實作前推法 (Forward Pass) 計算任務日期。
2.  **Excel 處理器**：使用 `pandas.read_excel()` 並實作欄位 Mapping 映射邏輯。

### 8.4 使用者介面開發 (`app.py`)
1.  **佈局設計**：使用 `st.sidebar` 建立選單。
2.  **甘特圖渲染**：使用 `plotly.figure_factory.create_gantt` 繪製圖表。
3.  **熱圖渲染**：使用 `plotly.graph_objects.Heatmap` 繪製資源負載。

### 8.5 測試與驗證
1.  **匯入測試**：準備一個包含 50 條任務且具備依賴關係的 Excel 檔案進行壓力測試。
2.  **衝突測試**：指派同一個人在同一時段參與兩個專案，確認 Heatmap 是否變紅。

### 8.6 部署與運行說明
在本機環境執行：
```bash
streamlit run app.py
```
系統將自動開啟瀏覽器視窗（通常為 `http://localhost:8501`）。

---
**本文件完結。** (本 SDD 結構完整且技術選型單一，極度適合 AI 工具如 ChatGPT, Claude 根據各小節內容逐步生成程式碼實作。)