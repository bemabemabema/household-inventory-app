import streamlit as st
import extra_streamlit_components as stx
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import pandas as pd
import datetime

# ページ設定
st.set_page_config(page_title="お家の在庫管理", page_icon="🏠", layout="centered", initial_sidebar_state="collapsed")

# CSSで見た目を調整
st.markdown("""
<style>
    /* 全体の余白調整 */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }
    
    /* 要素間の垂直余白を削る */
    .stMarkdown, .stText, .stCaption {
        margin-bottom: -0.6rem !important;
    }
    
    /* カラム間の余白 */
    div[data-testid="stHorizontalBlock"] {
        gap: 0.5rem !important;
    }
    
    /* 数量表示のスタイル */
    .qty-display {
        background-color: #f0f2f6;
        border-radius: 5px;
        text-align: center;
        font-weight: bold;
        font-size: 1.2rem;
        line-height: 2.2rem;
        height: 2.2rem;
    }
    
    /* ボタンの高さ調整 */
    .stButton button {
        height: 2.2rem !important;
        padding: 0 !important;
        width: 100%;
    }
    
    /* エクスパンダー（カテゴリ）の文字 */
    div[data-testid="stExpander"] p {
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Supabase接続設定
@st.cache_resource
def init_connection():
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url:
        try:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
        except (FileNotFoundError, KeyError):
            st.error("Supabaseの接続情報が見つかりません。")
            st.stop()
            
    return create_client(url, key)

supabase = init_connection()

# --- 認証機能 (Cookie対応) ---
def check_password():
    cookie_manager = stx.CookieManager()
    auth_token = cookie_manager.get("auth_token")

    try:
        correct_password = st.secrets["APP_PASSWORD"]
    except (FileNotFoundError, KeyError):
        correct_password = os.environ.get("APP_PASSWORD")
        if not correct_password:
            st.warning("パスワード(APP_PASSWORD)が設定されていません。")
            st.stop()
    
    SESSION_TOKEN = f"auth_{correct_password}"

    if auth_token == SESSION_TOKEN:
        return True

    if "auth_success" not in st.session_state:
        st.session_state.auth_success = False

    def password_entered():
        if st.session_state["password_input"] == correct_password:
            st.session_state.auth_success = True
            expires = datetime.datetime.now() + datetime.timedelta(days=30)
            cookie_manager.set("auth_token", SESSION_TOKEN, expires_at=expires)
        else:
            st.session_state.auth_success = False
            st.error("パスワードが違います")

    if not st.session_state.auth_success:
        st.text_input("合言葉を入力してください 🔒", type="password", key="password_input", on_change=password_entered)
        return False
    else:
        return True

if not check_password():
    st.stop()

# --- アプリ本体 ---

with st.sidebar:
    st.write("---")
    if st.button("ログアウト"):
        cookie_manager = stx.CookieManager()
        cookie_manager.delete("auth_token")
        st.session_state.auth_success = False
        st.rerun()

def load_data():
    response = supabase.table("household_inventory").select("*").order("created_at", desc=True).execute()
    return response.data

def update_quantity(item_id, current_quantity, change):
    new_quantity = max(0, current_quantity + change)
    supabase.table("household_inventory").update({"quantity": new_quantity}).eq("id", item_id).execute()
    st.rerun()

def delete_item(item_id):
    supabase.table("household_inventory").delete().eq("id", item_id).execute()
    st.rerun()

# サイドバー：新規登録
with st.sidebar:
    st.header("📝 新しく追加")
    with st.form("add_form", clear_on_submit=True):
        existing_data = load_data()
        existing_categories = sorted(list(set([item["category"] for item in existing_data])))
        default_categories = ["食料品", "日用品", "消耗品", "その他"]
        category_options = sorted(list(set(default_categories + existing_categories)))
        
        category = st.selectbox("カテゴリ", category_options)
        new_category = st.text_input("新しいカテゴリ（任意）")
        name = st.text_input("商品名")
        quantity = st.number_input("初期数量", min_value=1, value=1)
        notes = st.text_area("備考（任意）", height=100)
        
        submitted = st.form_submit_button("追加する")
        
        if submitted and name:
            final_category = new_category if new_category else category
            data = {"category": final_category, "name": name, "quantity": quantity, "notes": notes}
            supabase.table("household_inventory").insert(data).execute()
            st.rerun()

# メイン画面
st.title("🏠 お家の在庫管理")

items = load_data()

if not items:
    st.info("👈 左のサイドバーからアイテムを追加してください")
else:
    df = pd.DataFrame(items)
    categories = df["category"].unique()
    
    for cat in categories:
        with st.expander(f"📂 {cat}", expanded=True):
            cat_items = df[df["category"] == cat]
            
            for index, row in cat_items.iterrows():
                # --- スマホ向け 3行コンパクトレイアウト ---
                
                # 1行目: 商品名
                st.markdown(f"**{row['name']}**")
                
                # 2行目: 備考（あれば）
                if row['notes']:
                    st.caption(f"📝 {row['notes']}")
                
                # 3行目: 操作ボタン
                col_qty, col_minus, col_plus, col_del = st.columns([1.2, 1, 1, 0.8])
                
                with col_qty:
                    st.markdown(f"<div class='qty-display'>{row['quantity']}</div>", unsafe_allow_html=True)
                with col_minus:
                    if st.button("➖", key=f"minus_{row['id']}"):
                        update_quantity(row['id'], row['quantity'], -1)
                with col_plus:
                    if st.button("➕", key=f"plus_{row['id']}"):
                        update_quantity(row['id'], row['quantity'], 1)
                with col_del:
                    if st.button("🗑️", key=f"del_{row['id']}"):
                        delete_item(row['id'])
                
                # 区切り線
                st.markdown("<hr style='margin: 0.8rem 0; border: 0; border-top: 1px solid #eee;'/>", unsafe_allow_html=True)
