import requests
import xml.etree.ElementTree as ET

r = requests.get('https://news.google.com/rss/search?q=AI&hl=ja&gl=JP&ceid=JP:ja')
print(f"Status: {r.status_code}")
root = ET.fromstring(r.content)
items = root.findall('./channel/item')[:2]
print(f"Found {len(items)} items")
for i in items:
    title = i.find('title').text
    link = i.find('link').text
    print(f"  title: {title}")
    print(f"  link: {link}")
    print()
