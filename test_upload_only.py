import os
import json
from news_tool import upload_to_google_drive

# テスト用の環境設定
os.environ["GDRIVE_FOLDER_ID"] = "1jG14y9bYfpslTZEfJvI2MMStqjl-ju3e"

# JSONファイルからサービスアカウント情報を読み込む
json_path = r"c:\Users\stay-\Downloads\my-automation-496214-1a722d8e1293.json"
with open(json_path, "r", encoding="utf-8") as f:
    os.environ["GDRIVE_SERVICE_ACCOUNT_JSON"] = f.read()

def test_upload_only():
    print("1. Google Driveへのアップロードテスト開始...")
    content = "# Test Briefing\nThis is a test content for NotebookLM integration."
    filename = "QUICK_TEST_Upload.txt"
    upload_to_google_drive(content, filename)
    print("テスト完了！")

if __name__ == "__main__":
    test_upload_only()
