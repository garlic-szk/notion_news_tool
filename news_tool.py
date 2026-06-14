import os
import requests
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import jpholiday
from datetime import datetime
import pytz
import google.generativeai as genai
import json
def is_url_in_notion(url):
    """Notionのデータベースに同一のリンク（URL）が存在するか確認する"""
    if not NOTION_API_KEY or not DATABASE_ID:
        return False
    query_url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    filter_data = {
        "filter": {
            "property": "リンク",
            "url": {
                "equals": url.strip()
            }
        }
    }
    try:
        response = requests.post(query_url, headers=headers, json=filter_data, timeout=10)
        response.raise_for_status()
        results = response.json().get("results", [])
        return len(results) > 0
    except Exception as e:
        print(f"Notion重複確認エラー ({url}): {e}")
        return False

# ========================================
# 1. 環境変数の設定
# ========================================
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
DATABASE_ID = os.environ.get("DATABASE_ID")

# メール設定
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
WORK_EMAIL = os.environ.get("WORK_EMAIL")

# LINE設定
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

# 取得したいニュースのキーワード
KEYWORDS = {
    "仕事": ["マーケティング", "プロモーション", "ポイント経済圏", "Web広告"],
    "趣味": ["AI", "ワイン", "東京のレストラン", "グルメ"]
}

# LINEに配信するカテゴリごとの最大件数
MAX_ARTICLES_PER_CATEGORY = 4


# API/Drive設定
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GDRIVE_WEBAPP_URL = os.environ.get("GDRIVE_WEBAPP_URL")
GDRIVE_FOLDER_ID = os.environ.get("GDRIVE_FOLDER_ID")


# ========================================
# 2. 判定・取得ロジック
# ========================================

def is_holiday_or_weekend(dt):
    """土日祝日かどうかを判定する"""
    return dt.weekday() >= 5 or jpholiday.is_holiday(dt.date())

def fetch_google_news(keyword, max_items=2):
    """Googleニュース(RSS)から特定のキーワードのニュースを取得する"""
    url = f"https://news.google.com/rss/search?q={keyword}&hl=ja&gl=JP&ceid=JP:ja"
    try:
        response = requests.get(url)
        response.raise_for_status()
        news_list = []
        root = ET.fromstring(response.content)
        for item in root.findall('./channel/item')[:max_items]:
            title = item.find('title').text
            link = item.find('link').text
            pubDate = item.find('pubDate').text
            date_obj = parsedate_to_datetime(pubDate)
            date_str = date_obj.strftime("%Y-%m-%d")
            news_list.append({"title": title, "link": link, "date": date_str})
        return news_list
    except Exception as e:
        print(f"  ニュース取得エラー ({keyword}): {e}")
        return []

def add_to_notion(news, source_keyword):
    """Notionのデータベースにニュースを追加する"""
    if not NOTION_API_KEY or not DATABASE_ID:
        return
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "タイトル": {"title": [{"text": {"content": news['title']}}]},
            "リンク": {"url": news['link']},
            "取得日": {"date": {"start": news['date']}},
            "情報源": {"rich_text": [{"text": {"content": source_keyword}}]}
        }
    }
    try:
        requests.post(url, headers=headers, json=data).raise_for_status()
    except Exception as e:
        print(f"    Notion追加失敗: {e}")

# ========================================
# 3. AI解析・Drive連携ロジック
# ========================================

def generate_notebooklm_briefing(news_summary):
    """Geminiを使ってNotebookLM用の要約レポートを作成する"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEYが設定されていません。")
        return None

    genai.configure(api_key=api_key)
    
    # ニュース内容をテキストにまとめる
    content_text = ""
    for cat, items in news_summary.items():
        content_text += f"■カテゴリ: {cat}\n"
        for item in items:
            content_text += f"タイトル: {item['title']}\n"
    
    prompt = f"""
    あなたはプロのマーケティングアナリストです。
    以下の今日のニュースリストを読み、NotebookLMに読み込ませるための「朝刊ブリーフィング・レポート」を作成してください。

    【ニュース内容】
    {content_text}

    【レポートの構成案】
    1. 今日の注目トピック（最も重要なニュース3選とその背景）
    2. マーケティング・ポイント経済圏の動向（アナリストの視点での解説）
    3. ライフスタイル・トレンド（ワインやグルメに関するトピック）
    4. 今日一日のビジネスに役立つインサイト

    ※NotebookLMのポッドキャスト機能が面白くなるよう、事実だけでなく「なぜこれが重要なのか」「今後どう動くか」といった洞察を深めに含めてください。
    ※出力は日本語で、構造化されたMarkdown形式にしてください。
    """

    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Geminiレポート生成エラー: {e}")
        return None

def upload_to_google_drive(content, filename):
    """GAS（ウェブアプリ）経由でGoogle Driveにレポートをアップロードする"""
    webapp_url = os.environ.get("GDRIVE_WEBAPP_URL")
    folder_id = os.environ.get("GDRIVE_FOLDER_ID")

    if not all([webapp_url, folder_id]):
        print("Google Drive (GAS) の設定が不足しています。")
        return

    payload = {
        "folderId": folder_id,
        "filename": filename,
        "content": content
    }

    try:
        import json as json_module
        payload_str = json_module.dumps(payload)
        
        # デバッグ: 送信先URLの形式を確認
        print(f"DEBUG: GAS URL先頭20文字: {webapp_url[:20]}...")
        
        # GASへのPOSTリクエスト（リダイレクトは自動で追跡させる）
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            webapp_url,
            data=payload_str,
            headers=headers,
            timeout=60
        )
        
        # デバッグ: レスポンスの詳細
        print(f"DEBUG: ステータスコード={response.status_code}")
        print(f"DEBUG: レスポンス先頭200文字: {response.text[:200]}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get("status") == "success":
                    print(f"Google Driveにファイルをアップロードしました (File ID: {result.get('fileId')})")
                else:
                    print(f"GASエラー: {result.get('message')}")
            except Exception:
                # GASが正常にリダイレクトした場合、HTMLが返ることがある
                if "Moved Temporarily" not in response.text:
                    print(f"GAS応答（JSON以外）: {response.text[:300]}")
                else:
                    print("GASへの送信は完了しました（レスポンスはリダイレクトHTML）")
        else:
            print(f"GAS HTTPエラー: {response.status_code} - {response.text[:300]}")
    except Exception as e:
        print(f"Google Driveアップロード失敗: {e}")

# ========================================
# 3. 通知ロジック
# ========================================

def send_email(news_summary):
    """会社メールにニュースを送信する"""
    if not all([GMAIL_USER, GMAIL_APP_PASSWORD, WORK_EMAIL]):
        print("メール設定が不足しています。")
        return

    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = WORK_EMAIL
    msg['Subject'] = f"【自動配信】本日のニュースまとめ ({datetime.now(pytz.timezone('Asia/Tokyo')).strftime('%m/%d')})"

    body = "お疲れ様です。本日のニュースをお届けします。\n\n"
    for cat, items in news_summary.items():
        body += f"■ {cat}\n"
        for item in items:
            body += f"・{item['title']}\n  {item['link']}\n"
        body += "\n"
    
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("メールを送信しました。")
    except Exception as e:
        print(f"メール送信エラー: {e}")

def send_line(news_summary):
    """LINEにニュースを送信する"""
    token = LINE_CHANNEL_ACCESS_TOKEN
    user_id = LINE_USER_ID

    if not token or not user_id:
        print("LINE設定が不足しています。")
        return

    # 各カテゴリのニュースを指定された最大件数に絞り込む
    filtered_summary = {}
    for cat, items in news_summary.items():
        filtered_summary[cat] = items[:MAX_ARTICLES_PER_CATEGORY]

    # 送信する記事が全くない場合はスキップ
    total_articles = sum(len(items) for items in filtered_summary.values())
    if total_articles == 0:
        print("LINE送信対象となる新規ニュースがありません。送信をスキップします。")
        return

    message = "おはようございます！本日のニュースです。\n\n"
    for cat, items in filtered_summary.items():
        if not items:
            continue
        message += f"【{cat}】\n"
        for item in items:
            message += f"・{item['title']}\n{item['link']}\n\n"
    message += "詳細はNotionを確認してください。"

    # LINEのテキストメッセージ上限は5000文字
    if len(message) > 5000:
        message = message[:4990] + "\n..."

    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token.strip()}"
    }
    data = {
        "to": user_id.strip(),
        "messages": [{"type": "text", "text": message}]
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code != 200:
            print(f"LINE送信エラー (Status: {response.status_code}): {response.text}")
        else:
            print("LINEを送信しました。")
    except Exception as e:
        print(f"LINE送信中にエラーが発生しました: {e}")

# ========================================
# 4. メイン処理
# ========================================

def main():
    # 日本時間での現在時刻を取得
    jst = pytz.timezone('Asia/Tokyo')
    now = datetime.now(jst)
    is_holiday = is_holiday_or_weekend(now)

    print(f"実行時刻(JST): {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"判定: {'土日祝' if is_holiday else '平日'} (※現在は毎日LINE配信に統合されています)")

    # 1. ニュースを収集してNotionに保存 (未登録のもののみ保存＆LINE送信対象へ)
    all_news = {}
    for category, words in KEYWORDS.items():
        category_news = []
        for keyword in words:
            print(f"キーワード '{keyword}' のニュースを検索中...")
            items = fetch_google_news(keyword)
            for item in items:
                # Notionに既に同一URLが登録されているか（重複しているか）チェック
                if not is_url_in_notion(item['link']):
                    print(f"  [新規ニュース] Notion追加: {item['title']}")
                    add_to_notion(item, f"{category} ({keyword})")
                    category_news.append(item)
                else:
                    print(f"  [重複スキップ] すでに登録済み: {item['title']}")
        all_news[category] = category_news

    # 2. Geminiによる要約レポート作成 (NotebookLM用)
    print("NotebookLM用のレポートを生成中...")
    briefing_content = generate_notebooklm_briefing(all_news)
    
    if briefing_content:
        # Google Driveへアップロード
        filename = f"Marketing_Briefing_{now.strftime('%Y%m%d')}.txt"
        upload_to_google_drive(briefing_content, filename)
    
    # 3. 通知 (LINEのみに一本化)
    send_line(all_news)

if __name__ == "__main__":
    main()
