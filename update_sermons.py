import urllib.request
import xml.etree.ElementTree as ET
import json
import re
from datetime import datetime

RSS_URL = "https://anchor.fm/s/11798ff54/podcast/rss"

def parse_metadata(title_text, desc_text, pub_date_fallback):
    full_text = f"{title_text}\n{desc_text}"
    
    # 1. Title
    title = title_text.split('|')[0].strip() if title_text else "Untitled Message"
    
    # 2. Scripture
    passage = "Scripture Text"
    sc_match = re.search(r'Scripture:\s*([^|\n\r]+)', full_text, re.IGNORECASE)
    if sc_match:
        passage = sc_match.group(1).strip()
    else:
        bible_regex = r'\b(?:1\s*Corinthians|2\s*Corinthians|1\s*John|2\s*John|3\s*John|1\s*Peter|2\s*Peter|1\s*Timothy|2\s*Timothy|1\s*Th(?:essalonians)?|2\s*Th(?:essalonians)?|Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|1\s*Samuel|2\s*Samuel|1\s*Kings|2\s*Kings|1\s*Chronicles|2\s*Chronicles|Ezra|Nehemiah|Esther|Job|Psalms?|Proverbs|Ecclesiastes|Song\s+of\s+Solomon|Isaiah|Jeremiah|Lamentations|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|Matthew|Mark|Luke|John|Acts|Romans|Galatians|Ephesians|Philippians|Colossians|Titus|Philemon|Hebrews|James|Jude|Revelation)\s+\d+(?::\d+(?:-\d+)?)?'
        gen_match = re.search(bible_regex, full_text, re.IGNORECASE)
        if gen_match:
            passage = gen_match.group(0).strip()

    # 3. Book
    book = "General"
    if passage != "Scripture Text":
        bk_match = re.match(r'^(?:\d\s+)?[A-Za-z\s]+', passage)
        if bk_match:
            book = re.sub(r'\s+\d+$', '', bk_match.group(0).strip()).strip()

    # 4. Speaker
    speaker = "Pastor Deaton"
    sp_match = re.search(r'Speaker:\s*([^|\n\r]+)', full_text, re.IGNORECASE)
    if sp_match:
        speaker = sp_match.group(1).strip()
    elif "Pastor" in full_text:
        pst = re.search(r'Pastor\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', full_text)
        if pst:
            speaker = f"Pastor {pst.group(1).strip()}"

    # 5. Series
    series = "General Archive"
    sr_match = re.search(r'Series:\s*([^|\n\r<]+)', full_text, re.IGNORECASE)
    if sr_match:
        series = sr_match.group(1).split("Listen to")[0].split("Learn more")[0].strip()
    elif "providence" in full_text.lower():
        series = "From Providence"

    # 6. Date
    formatted_date = "2023-01-01"
    year = "2023"
    timestamp = 0

    dt_match = re.search(r'Date:\s*([^|\n\r]+)', full_text, re.IGNORECASE)
    if dt_match:
        try:
            dt_obj = datetime.strptime(dt_match.group(1).strip(), "%B %d, %Y")
            formatted_date = dt_obj.strftime("%Y-%m-%d")
            year = str(dt_obj.year)
            timestamp = int(dt_obj.timestamp())
        except Exception:
            pass

    if timestamp == 0 and pub_date_fallback:
        try:
            dt_obj = datetime.strptime(pub_date_fallback[:25], "%a, %d %b %Y %H:%M:%S")
            formatted_date = dt_obj.strftime("%Y-%m-%d")
            year = str(dt_obj.year)
            timestamp = int(dt_obj.timestamp())
        except Exception:
            pass

    return title, passage, book, speaker, series, formatted_date, year, timestamp

req = urllib.request.Request(RSS_URL, headers={'User-Agent': 'Mozilla/5.0'})
xml_data = urllib.request.urlopen(req).read()
root = ET.fromstring(xml_data)

items = root.findall('.//item')
sermons = []

for idx, item in enumerate(items):
    title_text = item.find('title').text if item.find('title') is not None else ""
    desc_elem = item.find('description')
    desc_text = desc_elem.text if desc_elem is not None else ""
    clean_desc = re.sub(r'<[^>]*>', '', desc_text).strip()
    pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
    
    enclosure = item.find('enclosure')
    audio_url = enclosure.attrib.get('url', '') if enclosure is not None else ""

    title, passage, book, speaker, series, date_str, year, ts = parse_metadata(title_text, clean_desc, pub_date)
    
    esv_url = f"https://www.esv.org/{urllib.parse.quote(passage)}/" if passage != "Scripture Text" else "https://www.esv.org/"

    sermons.append({
        "id": f"sermon-{idx}-{ts}",
        "title": title,
        "date": date_str,
        "year": year,
        "timestamp": ts,
        "author": speaker,
        "series": series,
        "passage": passage,
        "book": book,
        "esvUrl": esv_url,
        "url": audio_url,
        "description": desc_text,
        "cleanDesc": clean_desc
    })

sermons.sort(key=lambda x: x['timestamp'], reverse=True)

with open('sermons.json', 'w', encoding='utf-8') as f:
    json.dump(sermons, f, indent=2)

print(f"Successfully processed {len(sermons)} sermons.")
