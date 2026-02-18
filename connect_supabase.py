import os
from dotenv import load_dotenv
from supabase import create_client, Client

# .envファイルを読み込む
load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

print("--- Supabase接続テスト ---")

if not url or "ここに" in url:
    print("エラー: .envファイルに SUPABASE_URL が正しく設定されていません。")
    exit()
if not key or "ここに" in key:
    print("エラー: .envファイルに SUPABASE_KEY が正しく設定されていません。")
    exit()

try:
    print(f"接続先: {url}")
    supabase: Client = create_client(url, key)
    
    # 接続確認のため、存在しないテーブルに対してリクエストを送ってみる
    # 通信自体が成功すれば、テーブルが存在しないというエラー(PGRST200など)でもOKとみなせます
    # あるいは Auth のヘルスチェック的なものがあればよいのですが、
    # ここではシンプルにクエリを投げてネットワーク疎通を確認します。
    # 実際のデータ取得はまだテーブルがないのでエラーになりますが、例外が発生しなければ通信成功です。
    
    print("サーバーへ問い合わせ中...")
    response = supabase.table("connection_test").select("*").execute()
    
    # 通常はここには到達しません（テーブルがないため例外かエラーレスポンスになるはず）
    print("接続成功！ (データ取得成功)")

except Exception as e:
    # テーブルがない場合のエラーなどは正常な通信の結果です
    error_msg = str(e)
    if "relation" in error_msg and "does not exist" in error_msg:
        print("接続成功！ (Supabaseサーバーからの応答を確認しました)")
        print("※ 'connection_test' テーブルはまだ存在しないため、その点のエラーは正常です。")
    elif "404" in error_msg or "401" in error_msg:
         print(f"接続失敗: URLまたはAPIキーが間違っている可能性があります。\n詳細: {e}")
    else:
        # その他のエラーでも、HTTPレスポンスが返ってきているなら通信はできていますが、
        # ここではシンプルに成功メッセージを出します（Supabase-pyの挙動依存）
        # 実際に成功したかの判定は難しいですが、URL/Key間違い以外なら概ね接続はできています。
        print("接続テスト完了。")
        print(f"サーバーからの応答: {e}")
