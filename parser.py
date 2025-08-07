#!/usr/bin/env python3
import re
import csv
from telethon.sync import TelegramClient

# Настройки
api_id = 24006747
api_hash = '20201870409f49b65b63e662c81651ae'
channel_username = 'most_official'

def normalize_wait(raw_text):
    if not raw_text:
        return 0
    raw_text = raw_text.lower()

    numbers = {
        'десяти': 10, 'девяти': 9, 'восьми': 8, 'семи': 7,
        'шести': 6, 'пяти': 5, 'четырех': 4, 'четырёх': 4,
        'трех': 3, 'трёх': 3, 'двух': 2, 'полутора': 1.5,
        'полтора': 1.5, 'одного': 1, 'один': 1, 'одна': 1,
    }

    for phrase in sorted(numbers, key=len, reverse=True):
        if phrase in raw_text:
            return float(numbers[phrase])

    if 'полчаса' in raw_text or 'пол часа' in raw_text:
        return 0.5

    if 'час' in raw_text:
        return 1.0

    match = re.search(r'\d+([.,]\d+)?', raw_text)
    if match:
        val = match.group(0).replace(',', '.')
        try:
            return float(val)
        except ValueError:
            pass
    return 0

def check_bridge_status(text_lower):
    closure_phrases = [
        "перекрыто движение",
        "движение перекрыто",
        "временно перекрыто",
        "приостановлено движение",
        "мост закрыт",
        "перекрыт проезд",
        "закрытие движения",
        "крымский мост временно перекрыт",
        "движение автотранспорта по крымскому мосту временно перекрыто"
    ]
    opening_phrases = [
        "возобновлено движение",
        "движение возобновлено",
        "мост открыт",
        "открыт проезд",
        "крымский мост открыт",
        "движение автотранспорта по крымскому мосту возобновлено"
    ]
    if any(phrase in text_lower for phrase in closure_phrases):
        return "Closed"
    if any(phrase in text_lower for phrase in opening_phrases):
        return "Opened"
    return None

def extract_wait(block):
    if not block:
        return 0
    pattern = r"(?:время\s+)?ожидани[ея]\s+(?:около|примерно|более|менее)?\s*([а-я0-9\sё-]+?)(?:[.,\n]|$)"
    match = re.search(pattern, block, re.IGNORECASE)
    return normalize_wait(match.group(1).strip() if match else "")

def extract_count(block):
    match = re.search(r"(находится|ожидает)\s+(\d+)", block)
    return int(match.group(2)) if match else 0

def extract_block(text, start_key):
    pattern = rf"{re.escape(start_key)}.*?(?:\n|$)"
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(0) if match else ""

def parse_message(text, msg_date):
    text_lower = text.lower()
    status = check_bridge_status(text_lower)
    if status:
        return {
            'date': msg_date.strftime("%d.%m.%Y"),
            'time': msg_date.strftime("%H:%M"),
            'to_crimea': status,
            'to_crimea_wait': status,
            'from_crimea': status,
            'from_crimea_wait': status
        }

    if not (len(text) >= 5 and text[:2].isdigit() and text[2] == ':' and text[3:5].isdigit()):
        return None

    date_str = msg_date.strftime("%d.%m.%Y")
    time_str = text.split('\n')[0].strip()

    to_block = extract_block(text, "со стороны Тамани")
    from_block = extract_block(text, "со стороны Керчи")

    data = {
        'date': date_str,
        'time': time_str,
        'to_crimea': extract_count(to_block),
        'to_crimea_wait': int(round(extract_wait(to_block))),
        'from_crimea': extract_count(from_block),
        'from_crimea_wait': int(round(extract_wait(from_block))),
    }
    return data

def load_existing_records(filename):
    existing_keys = set()
    try:
        with open(filename, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_keys.add((row['date'], row['time']))
    except FileNotFoundError:
        pass
    return existing_keys

def main():
    filename = 'crimea_bridge.csv'
    processed_count = 0
    added_count = 0

    with TelegramClient('bridge_session', api_id, api_hash) as client:
        messages = client.get_messages(channel_username, limit=200)
        existing_records = load_existing_records(filename)

        with open(filename, 'a', encoding='utf-8', newline='') as file:
            fieldnames = ['date', 'time', 'to_crimea', 'to_crimea_wait', 'from_crimea', 'from_crimea_wait']
            writer = csv.DictWriter(file, fieldnames=fieldnames)

            if file.tell() == 0:
                writer.writeheader()

            for msg in messages:
                if msg.media is not None or not msg.text:
                    continue
                processed_count += 1
                data = parse_message(msg.text, msg.date)
                if data:
                    key = (data['date'], data['time'])
                    if key not in existing_records:
                        writer.writerow(data)
                        existing_records.add(key)
                        added_count += 1
                        print(f"Добавлено: {data}")

    print(f"Обработано сообщений: {processed_count}")
    print(f"Добавлено новых записей: {added_count}")

if __name__ == "__main__":
    main()
