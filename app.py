import streamlit as st
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import pandas as pd

# ページ設定（スマホでも見やすく）
st.set_page_config(page_title="お家の在庫管理", page_icon="🏠", layout="centered")

# CSSで見た目を調整
st.markdown("""
<style>
    .big-font {
        font-size: 20px !important;
        font-weight: bold;
    }
    .stButton button {
        width: 100%;
    }
    div[data-testid="stExpander"] div[role="button"] p {
        font-size: 1.1rem;
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
    
    # Streamlit Cloudでのデプロイ時は st.secrets を使う
    if not url:
        try:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
        except (FileNotFoundError, KeyError):
            st.error("Supabaseの接続情報が見つかりません。.envファイルまたはSecretsを設定してください。")
            st.stop()
            
    return create_client(url, key)

# --- パスワード認証機能 ---
def check_password():
    """Returns `True` if the user had the correct password."""
    
    # パスワードが設定されていない（ローカルなどで.envにもない）場合はスルーするか、
    # 本番環境では必須にするか。ここでは st.secrets から取得を試みる
    try:
        password = st.secrets["APP_PASSWORD"]
    except (FileNotFoundError, KeyError):
        # ローカル開発などでパスワード設定がない場合は、os.environを見るか、
        # あるいは「設定なし」として通す手もあるが、今回は安全側に倒してエラー表示
        # ただしローカル開発を考慮し、環境変数もチェック
        password = os.environ.get("APP_PASSWORD")
        if not password:
            # パスワード設定がなければ（初回など）、一旦認証なしで通すか警告を出す
            # 今回は「設定必須」として実装
            st.warning("パスワード(APP_PASSWORD)が設定されていません。Secretsを設定してください。")
            st.stop()

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "合言葉（パスワード）を入力してください 🔒", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password was incorrect, show input + error.
        st.text_input(
            "合言葉（パスワード）を入力してください 🔒", type="password", on_change=password_entered, key="password"
        )
        st.error("パスワードが違います 😕")
        return False
    else:
        # Password was correct.
        return True

# まずパスワードチェック（通らなければここで止まる）
if not check_password():
    st.stop()

supabase = init_connection()

# データ取得
def load_data():
    response = supabase.table("household_inventory").select("*").order("created_at", desc=True).execute()
    return response.data

# 数量更新
def update_quantity(item_id, current_quantity, change):
    new_quantity = max(0, current_quantity + change)
    supabase.table("household_inventory").update({"quantity": new_quantity}).eq("id", item_id).execute()
    # キャッシュをクリアして再読み込みさせるため、rerunは呼び出し元で行うか、st.experimental_rerun()を使う
    # 最新のStreamlitでは st.rerun()
    st.rerun()

# 削除
def delete_item(item_id):
    supabase.table("household_inventory").delete().eq("id", item_id).execute()
    st.rerun()

# --- サイドバー：新規登録 ---
with st.sidebar:
    st.header("📝 新しく追加")
    with st.form("add_form", clear_on_submit=True):
        # 既存のカテゴリを取得して選択肢にする
        existing_data = load_data()
        existing_categories = sorted(list(set([item["category"] for item in existing_data])))
        default_categories = ["食料品", "日用品", "消耗品", "その他"]
        # マージして重複削除
        category_options = sorted(list(set(default_categories + existing_categories)))
        
        category = st.selectbox("カテゴリ", category_options)
        # 手入力も可能にするためのテキスト入力（今回はシンプルにSelectboxのみだが、要望あれば追加）
        new_category = st.text_input("新しいカテゴリを作る（既存なら空欄）")
        
        name = st.text_input("商品名（例：醤油）")
        quantity = st.number_input("初期数量", min_value=1, value=1)
        notes = st.text_area("備考（任意）")
        
        submitted = st.form_submit_button("追加する")
        
        if submitted and name:
            final_category = new_category if new_category else category
            data = {
                "category": final_category,
                "name": name,
                "quantity": quantity,
                "notes": notes
            }
            supabase.table("household_inventory").insert(data).execute()
            st.success(f"{name} を追加しました！")
            st.rerun()

# --- メイン画面：在庫一覧 ---
st.title("🏠 お家の在庫管理")

# データ読み込み
items = load_data()

if not items:
    st.info("👈 左のサイドバーからアイテムを追加してください")
else:
    # カテゴリごとにグループ化
    df = pd.DataFrame(items)
    categories = df["category"].unique()
    
    for cat in categories:
        with st.expander(f"📂 {cat}", expanded=True):
            cat_items = df[df["category"] == cat]
            
            for index, row in cat_items.iterrows():
                # 1行にレイアウト：名前(と備考), 数量, マイナス, プラス, 削除
                c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 0.5])
                
                with c1:
                    st.markdown(f"<div class='big-font'>{row['name']}</div>", unsafe_allow_html=True)
                    if row['notes']:
                        st.caption(f"📝 {row['notes']}")
                
                with c2:
                    st.markdown(f"<div style='text-align: center; font-size: 24px; font-weight: bold;'>{row['quantity']}</div>", unsafe_allow_html=True)
                
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

