import os
import json
import asyncio
import google.generativeai as genai
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

# ========================================
# 1. AI自然言語解析モジュール
# ========================================
def parse_input_with_ai(user_input: str) -> dict:
    """ユーザーの適当な入力文から、項目ごとのJSONを生成する"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEYが設定されていません。")
        return {}

    genai.configure(api_key=api_key)
    
    prompt = f"""
    以下の保護者のメモを解析し、保育園の連絡帳アプリ（コドモン）に入力するためのJSONデータを出力してください。
    指定されていない項目は null にしてください。
    出力は必ずJSON形式のみにし、マークダウンブロック(```json ... ```)を含めないでください。
    
    【ルール】
    - temperature: 体温（例: "36.8"）
    - mood: 機嫌（"よい", "ふつう", "わるい" のいずれかに分類）
    - meal: 食事（"全部食べた", "半分くらい", "少しだけ", "食べていない" のいずれか）
    - poop: 排便（"あり", "なし", "ゆるめ" のいずれか）
    - sleep_start: 就寝時間（"HH:MM" 形式）
    - sleep_end: 起床時間（"HH:MM" 形式）
    - note: 自由記述の連絡事項（体調、できごとなど）
    
    【ユーザー入力】
    {user_input}
    """
    
    try:
        # Gemini 1.5 Flashを使用（高速で安価）
        model = genai.GenerativeModel('gemini-1.5-flash', generation_config={"response_mime_type": "application/json"})
        response = model.generate_content(prompt)
        
        result = json.loads(response.text)
        return result
    except Exception as e:
        print(f"AI解析エラー: {e}")
        return {}

# ========================================
# 2. Playwright 操作モジュール
# ========================================
async def draft_codmon(data: dict):
    """Playwrightでコドモンにログインし、一時保存を行う"""
    codmon_id = os.environ.get("CODMON_ID")
    codmon_pw = os.environ.get("CODMON_PASSWORD")

    if not codmon_id or not codmon_pw:
        print("コドモンのIDまたはパスワードが設定されていません。")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("1. コドモンにログイン中...")
        await page.goto("https://www.codmon.com/mypage/")
        
        # ※HTML構造が不明なため、一般的なセレクタで記述しています
        # 実際の画面に合わせて修正が必要になる可能性があります
        try:
            await page.fill('input[type="text"], input[name="login_id"], input[placeholder*="ID"]', codmon_id)
            await page.fill('input[type="password"]', codmon_pw)
            await page.click('button[type="submit"], input[type="submit"], text="ログイン"')
            await page.wait_for_load_state("networkidle")
            
            print("2. 連絡帳ページに移動中...")
            # 連絡帳のリンクを探してクリック
            await page.click('text="連絡帳"')
            await page.wait_for_load_state("networkidle")

            print("3. データを入力中...")
            # 体温
            if data.get("temperature"):
                print(f" - 体温: {data['temperature']}")
                # 例: await page.fill('input[name="temperature"]', data["temperature"])
            
            # 機嫌、食事、排便など（ラジオボタンやセレクトボックス）
            if data.get("mood"):
                print(f" - 機嫌: {data['mood']}")
            if data.get("meal"):
                print(f" - 食事: {data['meal']}")
            if data.get("sleep_start") and data.get("sleep_end"):
                print(f" - 睡眠: {data['sleep_start']} 〜 {data['sleep_end']}")
                
            # メモ
            if data.get("note"):
                print(f" - メモ: {data['note']}")
                # 例: await page.fill('textarea', data["note"])

            print("4. 一時保存（下書き）を実行...")
            # 送信ボタンではなく、一時保存ボタンをクリック
            # 例: await page.click('text="一時保存"')
            
            print("処理が完了しました！")
            
        except Exception as e:
            print(f"ブラウザ操作中にエラーが発生しました: {e}")
            # エラー時はスクリーンショットを保存して原因調査に使う
            await page.screenshot(path="error_screenshot.png")
            print("エラー画面のスクリーンショットを error_screenshot.png に保存しました。")
            
        finally:
            await browser.close()

# ========================================
# 3. メイン処理
# ========================================
if __name__ == "__main__":
    user_input = os.environ.get("CODMON_INPUT", "熱36.6、ご飯全部食べた、機嫌よい。昨日は21時に寝て7時に起きた。元気です。")
    print(f"【入力文】: {user_input}\n")
    
    print("AIによる解析を開始します...")
    parsed_data = parse_input_with_ai(user_input)
    print(json.dumps(parsed_data, indent=2, ensure_ascii=False))
    
    if parsed_data:
        # 非同期でPlaywright処理を実行
        asyncio.run(draft_codmon(parsed_data))
    else:
        print("解析に失敗したため処理を終了します。")
