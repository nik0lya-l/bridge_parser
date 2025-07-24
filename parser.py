import re
from datetime import datetime
import csv
from telethon.sync import TelegramClient

# Настройки
api_id = 24006747  # Ваш api_id
api_hash = '20201870409f49b65b63e662c81651ae'  # Ваш api_hash
channel_username = 'most_official'

def normalize_wait(raw_text):
    if not raw_text:
        return None

    raw_text = raw_text.lower()

    # Словарь только числительных
    numbers = {
        'десяти': 10,
        'девяти': 9,
        'восьми': 8,
        'семи': 7,
        'шести': 6,
        'пяти': 5,
        'четырех': 4,
        'четырёх': 4,
        'трех': 3,
        'трёх': 3,
        'двух': 2,
        'полутора': 1.5,
        'полтора': 1.5,
        'одного': 1,
        'один': 1,
        'одна': 1,
    }

    # Ищем числительные в первую очередь
    for phrase in sorted(numbers, key=len, reverse=True):
        if phrase in raw_text:
            return float(numbers[phrase])

    # Если числительные не нашли, смотрим на полчаса
    if 'полчаса' in raw_text or 'пол часа' in raw_text:
        return 0.5

    # Если ничего выше не нашли, но есть слово час, считаем 1 час
    if 'час' in raw_text:
        return 1.0

    # Если есть число в цифрах, тоже можем получить число
    match = re.search(r'\d+([.,]\d+)?', raw_text)
    if match:
        val = match.group(0).replace(',', '.')
        try:
            return float(val)
        except ValueError:
            return None

    return None



def extract_wait(block):
    if not block:
        return None

    # Шаблон для поиска "время ожидания" или просто "ожидание" с разными вариациями
    pattern = r"(?:время\s+)?ожидани[ея]\s+(?:около|примерно|более|менее)?\s*([а-яА-Я0-9\sё-]+?)(?:[.,\n]|$)"
    match = re.search(pattern, block, re.IGNORECASE)
    if match:
        extracted = match.group(1).strip()
        return normalize_wait(extracted)

    return None


def parse_message(text, msg_date):
    # Проверяем, что сообщение начинается с времени в формате "08:00"
    if not (len(text) >= 5 and text[:2].isdigit() and text[2] == ':' and text[3:5].isdigit()):
        return None

    time_str = text.split('\n')[0].strip()
    date_str = msg_date.strftime("%d.%m.%Y")

    def extract_block(start_key):
        # Ищем весь абзац, начинающийся с ключевой фразы (например, "со стороны Тамани")
        pattern = rf"{re.escape(start_key)}.*?(?:\n|$)"
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(0) if match else ""

    def extract_count(block):
        # Ищем число транспорта в блоке, например "находится 440"
        match = re.search(r"находится\s+(\d+)", block)
        return int(match.group(1)) if match else 0

    def safe_int(val):
        if val is None:
            return None
        return int(round(val))

    to_block = extract_block("со стороны Тамани")
    from_block = extract_block("со стороны Керчи")

    to_crimea = extract_count(to_block)
    from_crimea = extract_count(from_block)
    to_wait = safe_int(extract_wait(to_block))
    from_wait = safe_int(extract_wait(from_block))

    return {
        'date': date_str,
        'time': time_str,
        'to_crimea': to_crimea,
        'to_crimea_wait': to_wait,
        'from_crimea': from_crimea,
        'from_crimea_wait': from_wait
    }


def load_existing_records(filename):
    """Загружает существующие записи из CSV и возвращает множество ключей (date+time)"""
    existing_keys = set()
    try:
        with open(filename, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = (row['date'], row['time'])
                existing_keys.add(key)
    except FileNotFoundError:
        # Если файла нет — значит записей ещё нет
        pass
    return existing_keys


def main():
    filename = 'crimea_bridge.csv'

    with TelegramClient('bridge_session', api_id, api_hash) as client:
        print("Подключение к Telegram...")

        messages = client.get_messages(channel_username, limit=200)

        existing_records = load_existing_records(filename)

        with open(filename, 'a', newline='', encoding='utf-8') as file:
            fieldnames = ['date', 'time', 'to_crimea', 'to_crimea_wait', 'from_crimea', 'from_crimea_wait']
            writer = csv.DictWriter(file, fieldnames=fieldnames)

            if file.tell() == 0:
                writer.writeheader()

            for msg in messages:
                if msg.media is not None:
                    continue

                if msg.text:
                    data = parse_message(msg.text, msg.date)
                    if data:
                        key = (data['date'], data['time'])
                        if key not in existing_records:
                            writer.writerow(data)
                            existing_records.add(key)
                            print(f"Добавлено: {data}")
                        else:
                            print(f"Пропущено (уже есть): {data}")

    print("Готово! Данные сохранены в crimea_bridge.csv")


if __name__ == "__main__":
    main()
