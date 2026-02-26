import streamlit as st
import extra_streamlit_components as stx
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import pandas as pd
import datetime

# --- 1. 環境変数の読み込み ---
load_dotenv()

# --- 2. 安全な設定値取得関数の定義 ---
def get_config(key):
    """環境変数またはStreamlit Secretsから値を取得する"""
    val = os.environ.get(key)
    if val:
        return val
    try:
        return st.secrets.get(key)
    except Exception:
        return None

# --- 3. ページ設定 ---
st.set_page_config(page_title="お家の在庫管理", page_icon="🏠", layout="centered")

# --- 修正ポイント：背景色を濃紺(#000080)に変更し、文字色を調整 ---
st.markdown("""
<style>
    /* アプリ全体の背景色と基本文字色 */
    .stApp {
        background-color: #2d4b4d;
        color: white;
    }
    
    /* サイドバーのスタイル調整（必要に応じて） */
    [data-testid="stSidebar"] {
        background-color: #1d3133;
    }
    
    /* ボタンの横幅をいっぱいに広げる */
    .stButton > button {
        width: 100%;
    }

    /* エクスパンダーの見出し文字色 */
    .streamlit-expanderHeader {
        color: white;
        background-color: rgba(255, 255, 255, 0.1);
    }
    
    /* 入力ラベル等の文字色 */
    label, .stMarkdown {
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. Supabase接続設定 ---
@st.cache_resource
def init_connection():
    url = get_config("SUPABASE_URL")
    key = get_config("SUPABASE_KEY")

    if not url or not key:
        st.error("Supabaseの接続情報 (SUPABASE_URL, SUPABASE_KEY) が見つかりません。")
        st.stop()
        
    return create_client(url, key)

supabase = init_connection()

# --- 5. 認証機能 (Cookie対応) ---
def check_password():
    cookie_manager = stx.CookieManager()
    auth_token = cookie_manager.get("auth_token")

    correct_password = get_config("APP_PASSWORD")

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
        st.text_input(
            "合言葉を入力してください 🔒",
            type="password",
            key="password_input",
            on_change=password_entered
        )
        return False

    return True

if not check_password():
    st.stop()

# --- 6. データ操作関数 ---
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

# --- 7. サイドバー：操作画面 ---
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
        notes = st.text_area("備考（任意）")
        
        submitted = st.form_submit_button("追加する")
        if submitted and name:
            final_category = new_category if new_category else category
            data = {"category": final_category, "name": name, "quantity": quantity, "notes": notes}
            supabase.table("household_inventory").insert(data).execute()
            st.success(f"{name} を追加しました！")
            st.rerun()

    st.write("---")
    if st.button("ログアウト"):
        cookie_manager = stx.CookieManager()
        cookie_manager.delete("auth_token")
        st.session_state.auth_success = False
        st.rerun()

# --- 8. メイン画面：在庫一覧 ---
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
                # 修正ポイント：カラム指定をリスト形式 [比率] で記述
                c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 0.5])
                
                with c1:
                    st.markdown(f"**{row['name']}**")
                    if row['notes']:
                        st.caption(f"📝 {row['notes']}")
                
                with c2:
                    st.markdown(f"### {row['quantity']}")
                
                with c3:
                    if st.button("➖", key=f"minus_{row['id']}"):
                        update_quantity(row['id'], row['quantity'], -1)
                
                with c4:
                    if st.button("➕", key=f"plus_{row['id']}"):
                        update_quantity(row['id'], row['quantity'], 1)
                
                with c5:
                    if st.button("🗑️", key=f"del_{row['id']}"):
                        delete_item(row['id'])
                
                st.divider()