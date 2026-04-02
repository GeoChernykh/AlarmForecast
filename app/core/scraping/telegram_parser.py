import os
from dotenv import load_dotenv
from telethon.sync import TelegramClient
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

load_dotenv()

api_id = os.getenv('TG_API_ID')
api_hash = os.getenv('API_HASH')

DEFAULT_CHANNELS = ["kievreal1", "ps_zsu", "air_alert_ua", "war_monitor"]


def fetch_messages(
    start_date: datetime,
    channels: list[str] = DEFAULT_CHANNELS,
) -> pd.DataFrame:
    """
    Збирає повідомлення з вказаних каналів від start_date до поточного моменту.

    :param channels:    Список юзернеймів Telegram-каналів.
    :param start_date:  Дата початку збору (datetime, бажано з tzinfo=UTC).
    :param output_file: Шлях до вихідного CSV-файлу.
    :return:            DataFrame з колонками id, channel, date, text.
    """
    if start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=timezone.utc)

    now = datetime.now(tz=timezone.utc)
    data = []

    with TelegramClient("session", api_id, api_hash) as client:
        for channel in channels:
            print(f"Парсинг каналу: {channel}")
            count = 0

            for msg in client.iter_messages(channel):
                if msg.date < start_date:
                    break
                if msg.date > now:
                    continue

                data.append({
                    "id": msg.id,
                    "channel": channel,
                    "date": msg.date,
                    "text": msg.text,
                })
                count += 1
                if count % 500 == 0:
                    print(f"  Зібрано {count} повідомлень з каналу {channel}")

            print(f"Завершено парсинг каналу {channel}: {count} повідомлень")

    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values(by="date").reset_index(drop=True)

    return df

def save_data(df, file_name: str = "telegram_data.csv") -> None:
    path = Path('data/telegram')
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)

    file_path = path / file_name

    df.to_csv(file_path, index=False)
    print(f"\nУспішно збережено до «{file_path}». Загальна кількість рядків: {len(df)}")


if __name__ == "__main__":
    start = datetime(2026, 4, 1, tzinfo=timezone.utc)
    df = fetch_messages(
        start_date=start,
    )

    # save_data(df)
    print(df)