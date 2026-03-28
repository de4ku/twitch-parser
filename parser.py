#!/usr/bin/env python3
"""
Twitch Parser - парсер русскоязычных стримеров с малым онлайном
"""
import requests
import time
import re
from datetime import datetime
from typing import List, Dict, Optional
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET, GOOGLE_CREDENTIALS_FILE, SPREADSHEET_NAME

class TwitchParser:
    def __init__(self):
        self.client_id = TWITCH_CLIENT_ID
        self.client_secret = TWITCH_CLIENT_SECRET
        self.access_token = None
        self.base_url = "https://api.twitch.tv/helix"
        
    def get_access_token(self) -> str:
        """Получить OAuth токен для Twitch API"""
        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        response = requests.post(url, params=params)
        response.raise_for_status()
        self.access_token = response.json()["access_token"]
        return self.access_token
    
    def get_headers(self) -> Dict[str, str]:
        """Заголовки для запросов к API"""
        if not self.access_token:
            self.get_access_token()
        return {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.access_token}"
        }
    
    def get_live_streams(self, language: str = "ru", limit: int = 100) -> List[Dict]:
        """Получить список живых стримов на русском языке"""
        url = f"{self.base_url}/streams"
        params = {
            "language": language,
            "first": limit
        }
        
        all_streams = []
        cursor = None
        
        while True:
            if cursor:
                params["after"] = cursor
            
            response = requests.get(url, headers=self.get_headers(), params=params)
            response.raise_for_status()
            data = response.json()
            
            streams = data.get("data", [])
            all_streams.extend(streams)
            
            # Проверяем наличие следующей страницы
            pagination = data.get("pagination", {})
            cursor = pagination.get("cursor")
            
            if not cursor or len(all_streams) >= 500:  # Ограничение для безопасности
                break
            
            time.sleep(0.5)  # Rate limiting
        
        return all_streams
    
    def get_user_info(self, user_ids: List[str]) -> List[Dict]:
        """Получить информацию о пользователях (описание канала и т.д.)"""
        url = f"{self.base_url}/users"
        
        # API позволяет запрашивать до 100 пользователей за раз
        all_users = []
        for i in range(0, len(user_ids), 100):
            batch = user_ids[i:i+100]
            params = {"id": batch}
            
            response = requests.get(url, headers=self.get_headers(), params=params)
            response.raise_for_status()
            users = response.json().get("data", [])
            all_users.extend(users)
            
            time.sleep(0.5)
        
        return all_users
    
    def extract_contacts(self, description: str) -> Dict[str, Optional[str]]:
        """Извлечь контакты из описания канала"""
        contacts = {
            "discord": None,
            "vk": None,
            "telegram": None,
            "email": None
        }
        
        if not description:
            return contacts
        
        # Discord
        discord_pattern = r'(?:discord\.gg/|discord\.com/invite/)([a-zA-Z0-9]+)'
        discord_match = re.search(discord_pattern, description, re.IGNORECASE)
        if discord_match:
            contacts["discord"] = f"discord.gg/{discord_match.group(1)}"
        
        # VK
        vk_pattern = r'(?:vk\.com/)([a-zA-Z0-9_]+)'
        vk_match = re.search(vk_pattern, description, re.IGNORECASE)
        if vk_match:
            contacts["vk"] = f"vk.com/{vk_match.group(1)}"
        
        # Telegram
        tg_pattern = r'(?:t\.me/|telegram\.me/)([a-zA-Z0-9_]+)'
        tg_match = re.search(tg_pattern, description, re.IGNORECASE)
        if tg_match:
            contacts["telegram"] = f"t.me/{tg_match.group(1)}"
        
        # Email
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        email_match = re.search(email_pattern, description)
        if email_match:
            contacts["email"] = email_match.group(0)
        
        return contacts
    
    def filter_by_viewers(self, streams: List[Dict], max_viewers: int = 150) -> List[Dict]:
        """Фильтровать стримы по количеству зрителей"""
        return [s for s in streams if s.get("viewer_count", 0) <= max_viewers]
    
    def parse(self, max_viewers: int = 150) -> List[Dict]:
        """Основной метод парсинга"""
        print("🔍 Получаю список живых стримов...")
        streams = self.get_live_streams()
        print(f"✅ Найдено {len(streams)} стримов")
        
        print(f"🔍 Фильтрую по онлайну до {max_viewers} зрителей...")
        filtered_streams = self.filter_by_viewers(streams, max_viewers)
        print(f"✅ Отфильтровано {len(filtered_streams)} стримов")
        
        if not filtered_streams:
            print("❌ Не найдено стримов с подходящим онлайном")
            return []
        
        print("🔍 Получаю информацию о стримерах...")
        user_ids = [s["user_id"] for s in filtered_streams]
        users = self.get_user_info(user_ids)
        
        # Создаём словарь для быстрого поиска
        users_dict = {u["id"]: u for u in users}
        
        print("🔍 Извлекаю контакты...")
        results = []
        for stream in filtered_streams:
            user_id = stream["user_id"]
            user = users_dict.get(user_id, {})
            
            description = user.get("description", "")
            contacts = self.extract_contacts(description)
            
            results.append({
                "username": stream["user_login"],
                "display_name": stream["user_name"],
                "viewers": stream["viewer_count"],
                "game": stream["game_name"],
                "title": stream["title"],
                "started_at": stream["started_at"],
                "channel_url": f"https://twitch.tv/{stream['user_login']}",
                "discord": contacts["discord"],
                "vk": contacts["vk"],
                "telegram": contacts["telegram"],
                "email": contacts["email"],
                "description": description[:200]  # Первые 200 символов
            })
        
        print(f"✅ Парсинг завершён! Найдено {len(results)} стримеров")
        return results


class GoogleSheetsExporter:
    def __init__(self, credentials_file: str, spreadsheet_name: str):
        self.credentials_file = credentials_file
        self.spreadsheet_name = spreadsheet_name
        self.client = None
        self.sheet = None
        
    def connect(self):
        """Подключиться к Google Sheets"""
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            self.credentials_file, scope
        )
        self.client = gspread.authorize(creds)
        
        # Открываем или создаём таблицу
        try:
            self.sheet = self.client.open(self.spreadsheet_name).sheet1
        except gspread.SpreadsheetNotFound:
            spreadsheet = self.client.create(self.spreadsheet_name)
            self.sheet = spreadsheet.sheet1
            # Делаем таблицу доступной для всех с ссылкой
            spreadsheet.share('', perm_type='anyone', role='reader')
    
    def export(self, data: List[Dict]):
        """Экспортировать данные в Google Sheets (с накоплением, без дубликатов)"""
        if not self.sheet:
            self.connect()
        
        # Заголовки
        headers = [
            "Username", "Display Name", "Viewers", "Game", "Title",
            "Started At", "Channel URL", "Discord", "VK", "Telegram",
            "Email", "Description", "First Seen"
        ]
        
        # Получаем существующие данные
        existing_data = self.sheet.get_all_records()
        existing_usernames = {row["Username"].lower() for row in existing_data if row.get("Username")}
        
        # Если таблица пустая, добавляем заголовки
        if not existing_data:
            self.sheet.clear()
            self.sheet.append_row(headers)
        
        # Фильтруем новых стримеров (без дубликатов)
        new_streamers = []
        duplicates_count = 0
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for item in data:
            username_lower = item["username"].lower()
            if username_lower not in existing_usernames:
                new_streamers.append(item)
                existing_usernames.add(username_lower)  # Добавляем в set, чтобы избежать дубликатов внутри текущей выборки
            else:
                duplicates_count += 1
        
        # Записываем только новых стримеров
        if new_streamers:
            for item in new_streamers:
                row = [
                    item["username"],
                    item["display_name"],
                    item["viewers"],
                    item["game"],
                    item["title"],
                    item["started_at"],
                    item["channel_url"],
                    item["discord"] or "",
                    item["vk"] or "",
                    item["telegram"] or "",
                    item["email"] or "",
                    item["description"],
                    current_time
                ]
                self.sheet.append_row(row)
            
            print(f"✅ Добавлено {len(new_streamers)} новых стримеров")
        else:
            print("ℹ️ Новых стримеров не найдено")
        
        if duplicates_count > 0:
            print(f"ℹ️ Пропущено {duplicates_count} дубликатов (уже есть в таблице)")
        
        total_count = len(existing_data) + len(new_streamers)
        print(f"📊 Всего в базе: {total_count} стримеров")
        print(f"🔗 Ссылка: {self.sheet.spreadsheet.url}")


def main():
    print("🚀 Запуск парсера Twitch...")
    print(f"⏰ Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)
    
    # Парсинг
    parser = TwitchParser()
    results = parser.parse(max_viewers=150)
    
    if not results:
        print("❌ Нет данных для экспорта")
        return
    
    # Экспорт в Google Sheets
    print("\n📊 Экспорт в Google Sheets...")
    exporter = GoogleSheetsExporter(GOOGLE_CREDENTIALS_FILE, SPREADSHEET_NAME)
    exporter.export(results)
    
    print("\n✅ Готово!")


if __name__ == "__main__":
    main()
