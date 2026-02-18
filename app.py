import streamlit as st
import extra_streamlit_components as stx
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import pandas as pd
import datetime

# ページ設定（スマホでも見やすく）
st.set_page_config(page_title="お家の在庫管理", page_icon="🏠", layout="centered", initial_sidebar_state="collapsed")

# CSSで見た目を調整（コンパクト化）
st.markdown("""
<style>
    /* 全体の余白調整 */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }
    
    /* ボタンのスタイル */
    .stButton button {
        width: 100%;
        padding: 0px !important;
        height: 2.5rem !important;
        line-height: normal !important;
    }
    
    /* アイテム行のスタイル */
    .item-row {
        border-bottom: 1px solid #f0f0f0;
        padding: 0.5rem 0;
        display: flex;
        align-items: center;
    }
    
    /* 商品名 */
    .item-name {
        font-weight: bold;
        font-size: 1rem;
        margin-bottom: 0px !important;
    }
    
    /* 備考 */
    .item-note {
        font-size: 0.8rem;
        color: #666;
        margin-top: -3px !important;
        margin-bottom: 0px !important;
        line-height: 1.2;
    }
    
    /* 数量 */
    .item-qty {
        text-align: center;
        font-size: 1.3rem;
        font-weight: bold;
        line-height: 2.5rem;
    }
    
    /* アコーディオンの文字サイズ */
    div[data-testid="stExpander"] p {
        font-weight: bold;
    }
    
    /* Divider削除、代わりにborder-bottomを使うので調整 */
    hr {
        margin: 0.5rem 0 !important;
    }

    /* 【スマホ対策】強制的に横並びにする */
    /* 640px以下(Streamlitのスマホブレークポイント)で、カラム構成を強制上書きする */
    @media (max-width: 640px) {
        div[data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap !important;
            gap: 2px !important;
            align-items: center !important;
        }
        
        /* ボタンなどのカラム：固定幅にする */
        /* カラム2(数量), 3(減), 4(増), 5(削除) */
        div[data-testid="column"]:nth-of-type(2) { flex: 0 0 30px !important; min-width: 30px !important; }
        div[data-testid="column"]:nth-of-type(3) { flex: 0 0 36px !important; min-width: 36px !important; }
        div[data-testid="column"]:nth-of-type(4) { flex: 0 0 36px !important; min-width: 36px !important; }
        div[data-testid="column"]:nth-of-type(5) { flex: 0 0 36px !important; min-width: 36px !important; }
        
        /* カラム1(商品名)：残りの幅をすべて使う */
        div[data-testid="column"]:nth-of-type(1) {
            flex: 1 1 auto !important;
            min-width: 0 !important;
            padding-right: 4px !important;
        }
        
        /* Streamlitのデフォルトパディングを消す */
        div[data-testid="column"] {
            padding: 0 1px !important;
        }
        
        /* ボタン自体のスタイル調整 */
        .stButton button {
            min-width: 0px !important;
            padding: 0px !important;
        }
    }
    
    /* 長すぎる商品名は「...」で省略して、レイアウト崩れを防ぐ */
    .item-name {
        font-weight: bold;
        font-size: 0.95rem;
        margin-bottom: 0px !important;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
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
    # Cookieマネージャーの初期化
    cookie_manager = stx.CookieManager()
    
    # 認証済みCookieがあるか確認
    # (値の取得に少し時間がかかる場合があるため、st.rerunが必要になることも)
    params = st.query_params
    auth_token = cookie_manager.get("auth_token")

    # パスワード（正解）を取得
    try:
        correct_password = st.secrets["APP_PASSWORD"]
    except (FileNotFoundError, KeyError):
        correct_password = os.environ.get("APP_PASSWORD")
        if not correct_password:
            st.warning("パスワード(APP_PASSWORD)が設定されていません。")
            st.stop()
    
    # 簡単なトークン生成（本番ではもっと堅牢にすべきだが、簡易版としてパスワードそのものを使用）
    # ※セキュリティ向上のため、本来はハッシュ化すべきです
    SESSION_TOKEN = f"auth_{correct_password}"

    if auth_token == SESSION_TOKEN:
        return True

    # 認証されていない場合、パスワード入力フォームを表示
    if "auth_success" not in st.session_state:
        st.session_state.auth_success = False

    def password_entered():
        if st.session_state["password_input"] == correct_password:
            st.session_state.auth_success = True
            # Cookieに保存 (有効期限30日)
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
    else:
        # 入力成功直後
        return True

# まずパスワードチェック
if not check_password():
    st.stop()

# --- 以降、認証済みの処理 ---

# ログアウトボタン（サイドバー）
with st.sidebar:
    st.write("---")
    if st.button("ログアウト"):
        cookie_manager = stx.CookieManager()
        cookie_manager.delete("auth_token")
        st.session_state.auth_success = False
        st.rerun()

# データ取得
def load_data():
    response = supabase.table("household_inventory").select("*").order("created_at", desc=True).execute()
    return response.data

# 数量更新
def update_quantity(item_id, current_quantity, change):
    new_quantity = max(0, current_quantity + change)
    supabase.table("household_inventory").update({"quantity": new_quantity}).eq("id", item_id).execute()
    st.rerun()

# 削除
def delete_item(item_id):
    supabase.table("household_inventory").delete().eq("id", item_id).execute()
    st.rerun()

# --- サイドバー：新規登録 ---
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
            data = {
                "category": final_category,
                "name": name,
                "quantity": quantity,
                "notes": notes
            }
            supabase.table("household_inventory").insert(data).execute()
            st.rerun()

# --- メイン画面：在庫一覧 ---
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
                # コンパクトレイアウト: 名前エリア(3), 数量(1), マイナス(0.8), プラス(0.8), 削除(0.6)
                c1, c2, c3, c4, c5 = st.columns([3, 1, 0.8, 0.8, 0.6], gap="small")
                
                with c1:
                    # 商品名を表示
                    st.markdown(f"<div class='item-name'>{row['name']}</div>", unsafe_allow_html=True)
                    # 備考があれば小さく表示
                    if row['notes']:
                        st.markdown(f"<div class='item-note'>📝{row['notes']}</div>", unsafe_allow_html=True)
                
                with c2:
                    st.markdown(f"<div class='item-qty'>{row['quantity']}</div>", unsafe_allow_html=True)
                
                with c3:
                    if st.button("➖", key=f"minus_{row['id']}"):
                        update_quantity(row['id'], row['quantity'], -1)
                
                with c4:
                    if st.button("➕", key=f"plus_{row['id']}"):
                        update_quantity(row['id'], row['quantity'], 1)
                
                with c5:
                    if st.button("🗑️", key=f"del_{row['id']}"):
                        delete_item(row['id'])
                
                # 薄い区切り線（CSSでborder-bottomを使わず、st.dividerより細い線を引くにはmarkdownのhrが手っ取り早いが、余白大きくなりがち）
                # ここではCSSでitem-rowクラスを作ってborder引くのが綺麗だが、Streamlitの構造上divで囲むのが難しい
                # 代わりに薄いDividerを入れる
                st.markdown("<hr style='margin: 0.2rem 0; border: 0; border-top: 1px solid #eee;'/>", unsafe_allow_html=True)
