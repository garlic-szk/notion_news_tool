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

    message = "おはようございます！本日のニュースです。\n\n"
    for cat, items in news_summary.items():
        message += f"【{cat}】\n"
        for item in items:
            message += f"・{item['title']}\n  {item['link']}\n"
        message += "\n"
    message += "詳細はNotionを確認してください。"

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
    hour = now.hour
    is_holiday = is_holiday_or_weekend(now)

    print(f"実行時刻(JST): {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"判定: {'土日祝' if is_holiday else '平日'}")

    # 1. ニュースを収集してNotionに保存 (常に実行して蓄積)
    all_news = {}
    for category, words in KEYWORDS.items():
        category_news = []
        for keyword in words:
            items = fetch_google_news(keyword)
            for item in items:
                add_to_notion(item, f"{category} ({keyword})")
                category_news.append(item)
        all_news[category] = category_news

    # 確認テスト用：常に両方に送信する
    send_email(all_news)
    send_line(all_news)

if __name__ == "__main__":
    main()
