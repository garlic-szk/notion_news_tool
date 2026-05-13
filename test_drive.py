import os
import json
import asyncio
from news_tool import generate_notebooklm_briefing, upload_to_google_drive, KEYWORDS, fetch_google_news

# テスト用の環境設定
os.environ["GEMINI_API_KEY"] = "AIzaSyDieSpprdj1UvkwbwhZb_5AE_bTeuGKekI"
os.environ["GDRIVE_FOLDER_ID"] = "1jG14y9bYfpslTZEfJvI2MMStqjl-ju3e"

# JSONファイルからサービスアカウント情報を読み込む
json_path = r"c:\Users\stay-\Downloads\my-automation-496214-1a722d8e1293.json"
with open(json_path, "r", encoding="utf-8") as f:
    os.environ["GDRIVE_SERVICE_ACCOUNT_JSON"] = f.read()

def test_main():
    print("1. ニュースの取得テスト中...")
    test_news = {}
    # テスト用に各カテゴリ1件ずつ取得
    for cat, words in list(KEYWORDS.items()):
        test_news[cat] = fetch_google_news(words[0], max_items=1)
    
    print("2. Geminiによる要約レポート作成テスト中...")
    briefing = generate_notebooklm_briefing(test_news)
    if not briefing:
        print("要約に失敗しました。")
        return
    print("--- 生成されたレポート ---")
    print(briefing[:200] + "...")
    
    print("\n3. Google Driveへのアップロードテスト中...")
    filename = "TEST_NotebookLM_Briefing.txt"
    upload_to_google_drive(briefing, filename)
    print("テスト完了！Google Driveを確認してください。")

if __name__ == "__main__":
    test_main()
