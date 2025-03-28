from telethon.sync import TelegramClient

api_id = 22359020 # Thay bằng API ID của bạn
api_hash = "6dbb9685d5fcb675affaa37ce5018d12"  # Thay bằng API Hash của bạn

with TelegramClient("session_name", api_id, api_hash) as client:
    dialogs = client.get_dialogs()
    for chat in dialogs:
        print(f"Tên nhóm: {chat.title}, ID: {chat.id}")
