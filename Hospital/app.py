import streamlit as st
import pandas as pd
from datetime import datetime

# 1. 初始化網頁設定與系統暫存資料庫 (使用 Streamlit Session State，重整網頁資料不會消失)
st.set_page_config(page_title="醫院病患資料管理系統", layout="wide")

if "patient_db" not in st.session_state:
    # 建立初始的空資料表，欄位與定義的 CSV 格式完全相同
    st.session_state.patient_db = pd.DataFrame(columns=[
        "病患編號", "姓名", "性別", "出生日期", "身分證字號", "聯絡電話", "主要病徵描述"
    ])

st.title("🏥 醫院病患資料管理系統 (紙本轉數位化原型)")
st.markdown("本系統支援**網頁上手動輸入**、**標準 CSV 批次匯入**與**資料整齊匯出**。")

# 建立分頁：分為「資料檢視與匯出」、「手動新增資料」、「批次 CSV 匯入」
tab1, tab2, tab3 = st.tabs(["📊 現有病患資料 & 匯出", "✍️ 手動輸入病患資料", "📥 批次匯入 CSV"])

# ==========================================
# 分頁一：資料檢視與匯出
# ==========================================
with tab1:
    st.subheader("目前系統內的病患名冊")
    if st.session_state.patient_db.empty:
        st.info("目前尚無病患資料，請至其他分頁手動輸入或匯入 CSV 檔案。")
    else:
        # 使用 st.data_editor 讓使用者可以直接在網頁上像 Excel 一樣微調修改資料
        updated_df = st.data_editor(st.session_state.patient_db, num_rows="dynamic", use_container_width=True)
        st.session_state.patient_db = updated_df
        
        # 💡 【優化點 1】匯出改用 'utf-8-sig'，確保 Windows Excel 打開不亂碼，且支援罕見字不報錯
        csv_data = st.session_state.patient_db.to_csv(index=False).encode('utf-8-sig')
        
        st.download_button(
            label="📥 匯出成標準 Excel/CSV 檔案",
            data=csv_data,
            file_name=f"patient_export_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

# ==========================================
# 分頁二：手動輸入病患資料
# ==========================================
with tab2:
    st.subheader("新病患資料臨櫃輸入表單")
    with st.form("patient_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            p_id = st.text_input("病患編號 (例: P001)*")
            p_name = st.text_input("姓名*")
            p_gender = st.selectbox("性別", ["男", "女", "其他"])
            p_dob = st.date_input("出生日期", min_value=datetime(1900, 1, 1))
        with col2:
            p_id_num = st.text_input("身分證字號*")
            p_phone = st.text_input("聯絡電話")
            p_symptoms = st.text_area("主要病徵描述")
            
        submit_btn = st.form_submit_button("儲存至系統")
        
        if submit_btn:
            if not p_id or not p_name or not p_id_num:
                st.error("請填寫必填欄位 (* 號項目)")
            elif p_id in st.session_state.patient_db["病患編號"].values:
                st.error(f"病患編號 {p_id} 已存在，請檢查是否重複！")
            else:
                # 組裝新資料
                new_data = {
                    "病患編號": p_id,
                    "姓名": p_name,
                    "性別": p_gender,
                    "出生日期": p_dob.strftime("%Y-%m-%d"),
                    "身分證字號": p_id_num,
                    "聯絡電話": p_phone,
                    "主要病徵描述": p_symptoms
                }
                # 新增至 Session State 資料庫
                st.session_state.patient_db = pd.concat([st.session_state.patient_db, pd.DataFrame([new_data])], ignore_index=True)
                st.success(f"成功手動新增病患：{p_name}")
                st.rerun()

# ==========================================
# 分頁三：批次匯入 CSV 檔案
# ==========================================
with tab3:
    st.subheader("上傳固定格式之 CSV 檔案")
    st.caption("提示：上傳的檔案欄位必須完全符合：[病患編號, 姓名, 性別, 出生日期, 身分證字號, 聯絡電話, 主要病徵描述]")
    
    # 提供一個空白範本供工作人員下載參考
    template_df = pd.DataFrame(columns=["病患編號", "姓名", "性別", "出生日期", "身分證字號", "聯絡電話", "主要病徵描述"])
    # 💡 【優化點 2】下載範本使用 utf-8-sig，讓 Excel 打開就是乾淨的中文欄位
    template_csv = template_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 下載空白 CSV 匯入範本", data=template_csv, file_name="patient_template.csv", mime="text/csv")
    
    uploaded_file = st.file_uploader("請選擇要匯入的 CSV 檔案", type=["csv"])
    
    if uploaded_file is not None:
        try:
            # 💡 【優化點 3】自動雙重容錯讀取邏輯
            imported_df = None
            
            # 第一步：先嘗試用 utf-8-sig 讀取
            try:
                # 重新將指標移到檔案開頭
                uploaded_file.seek(0)
                imported_df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
            except UnicodeDecodeError:
                # 如果噴編碼錯誤，代表可能是 Excel 的 cp950/big5 格式，切換到 cp950 讀取
                uploaded_file.seek(0)
                imported_df = pd.read_csv(uploaded_file, encoding='cp950')
            
            # 判讀格式：檢查欄位是否完全一致
            required_columns = list(template_df.columns)
            if imported_df is not None and list(imported_df.columns) == required_columns:
                st.success("檔案格式檢查通過！開始判讀內容...")
                
                # 點擊按鈕確認寫入系統
                if st.button("確認將 Excel/CSV 資料填入網站系統"):
                    # 排除重複的病患編號，避免蓋掉現有資料
                    existing_ids = st.session_state.patient_db["病患編號"].values
                    # 篩選出新資料
                    new_records = imported_df[~imported_df["病患編號"].isin(existing_ids)]
                    duplicate_count = len(imported_df) - len(new_records)
                    
                    if len(new_records) > 0:
                        st.session_state.patient_db = pd.concat([st.session_state.patient_db, new_records], ignore_index=True)
                        st.success(f"成功匯入 {len(new_records)} 筆新病患資料！")
                    if duplicate_count > 0:
                        st.warning(f"自動忽略了 {duplicate_count} 筆編號重複的資料。")
                    st.rerun()
            else:
                st.error("❌ 檔案格式錯誤！欄位名稱或順序與系統不符，請下載上方範本比對。")
        except Exception as e:
            st.error(f"讀取檔案時發生錯誤: {e}")
