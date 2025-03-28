import json
import threading
import requests
import winsound
import tkinter as tk
import websocket
import time
import socket
from pymongo import MongoClient
from pystray import Icon, MenuItem, Menu
from PIL import Image
import google.auth
from google.auth.transport.requests import Request
from telethon import TelegramClient, events

# 🔹 Kết nối MongoDB Atlas
MONGO_URI = "mongodb+srv://kandesfx:hehe1234@kandes.xdh45.mongodb.net/?retryWrites=true&w=majority&appName=Kandes"
client = MongoClient(MONGO_URI)
db = client['telebot']
ip_collection = db['server_ip']
tokens_collection = db['tokens']

# 🔹 Cấu hình Firebase
# SERVICE_ACCOUNT_FILE = "telebot-notifier-40f49352f756.json"
PROJECT_ID = "telebot-notifier"

# 🔹 Thông tin Telegram API
API_ID = 22359020
API_HASH = "6dbb9685d5fcb675affaa37ce5018d12"
GROUP_ID = -4646855241
telegram_client = TelegramClient("session_name", API_ID, API_HASH)

# 🔹 Cấu hình ban đầu
SERVER_URL = ""
WS_SERVER = ""

def get_latest_server_ip():
    global SERVER_URL, WS_SERVER
    try:
        doc = ip_collection.find_one(sort=[("timestamp", -1)])
        if doc and "ip" in doc:
            new_ip = doc["ip"]
            new_server_url = f"http://{new_ip}:5000"
            new_ws_server = f"ws://{new_ip}:6789"
            if new_server_url != SERVER_URL:
                print(f"🔄 Cập nhật IP server: {new_ip}")
                SERVER_URL = new_server_url
                WS_SERVER = new_ws_server
    except Exception as e:
        print("⚠️ Không thể lấy IP mới từ MongoDB:", e)

def auto_update_server_ip():
    while True:
        get_latest_server_ip()
        time.sleep(420)  # 7 phút (420 giây)

# 🔹 Chạy cập nhật IP trước khi tiếp tục
get_latest_server_ip()
if not WS_SERVER:
    print("❌ Không thể lấy IP từ MongoDB. Thoát chương trình!")
    exit(1)

# ======================= GỬI THÔNG BÁO TỚI FCM =======================
def get_access_token():
    credentials = google.auth.load_credentials_from_file(SERVICE_ACCOUNT_FILE, scopes=["https://www.googleapis.com/auth/cloud-platform"])[0]
    credentials.refresh(Request())
    return credentials.token

def get_all_tokens():
    return [doc["token"] for doc in tokens_collection.find()]

def send_fcm_notification(title, body):
    access_token = get_access_token()
    url = f"https://fcm.googleapis.com/v1/projects/{PROJECT_ID}/messages:send"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    tokens = get_all_tokens()
    if not tokens:
        print("❌ Không có thiết bị nào đăng ký.")
        return
    
    for token in tokens:
        payload = {
            "message": {
                "token": token,
                "notification": {
                    "title": title,
                    "body": body
                },
                "android": {
                    "priority": "high"
                },
                "apns": {
                    "payload": {
                        "aps": {
                            "sound": "default"
                        }
                    }
                }
            }
        }
        try:
            response = requests.post(url, headers=headers, json=payload)
            print("✅ Gửi FCM Response:", response.json())
        except Exception as e:
            print("❌ Lỗi khi gửi FCM:", e)

# ======================= LẮNG NGHE TIN NHẮN TELEGRAM =======================
async def start_telegram():
    async with telegram_client:
        @telegram_client.on(events.NewMessage(chats=GROUP_ID))
        async def handler(event):
            message = event.message.message
            if "điểm danh" in message.lower():
                print("📩 Có dấu hiệu thông báo điểm danh!")
                send_fcm_notification("Thông báo điểm danh", message)
        
        print("🚀 Telegram listener đang chạy...")
        await telegram_client.run_until_disconnected()

def run_telegram_listener():
    import asyncio
    asyncio.run(start_telegram())

# ======================= CẬP NHẬT IP PUBLIC =======================
def get_public_ip():
    try:
        response = requests.get("http://checkip.amazonaws.com", timeout=5)
        return response.text.strip()
    except Exception as e:
        print("⚠️ Không thể lấy IP public:", e)
        return None

# ======================= NHẬN THÔNG BÁO QUA WEBSOCKET =======================
def start_websocket():
    while True:
        get_latest_server_ip()  # 🔄 Lấy IP mới nhất trước mỗi lần kết nối
        if not WS_SERVER:
            print("❌ Chưa có địa chỉ WebSocket, chờ cập nhật...")
            time.sleep(10)
            continue
        
        try:
            print(f"🔗 Kết nối WebSocket tới {WS_SERVER}...")
            ws = websocket.WebSocketApp(WS_SERVER, 
                                        on_message=lambda ws, msg: send_fcm_notification("Thông báo", msg),
                                        on_error=lambda ws, err: print("❌ Lỗi WebSocket:", err),
                                        on_close=lambda ws, code, msg: print("🔌 Kết nối WebSocket bị đóng."))
            ws.on_open = lambda ws: print("✅ Kết nối WebSocket thành công!")
            ws.run_forever()
        except Exception as e:
            print("❌ Lỗi khi kết nối WebSocket:", e)
        time.sleep(5)  # Thử kết nối lại sau 5 giây nếu lỗi

# 🔹 Chạy ứng dụng
threading.Thread(target=auto_update_server_ip, daemon=True).start()
time.sleep(5)  # Chờ cập nhật IP trước khi kết nối WebSocket
threading.Thread(target=start_websocket, daemon=True).start()
threading.Thread(target=run_telegram_listener, daemon=True).start()

# 🔹 Cập nhật IP server lên MongoDB
try:
    public_ip = get_public_ip()
    if public_ip:
        ip_collection.insert_one({"ip": public_ip, "timestamp": time.time()})
        print(f"✅ IP server ({public_ip}) đã được cập nhật lên MongoDB.")
    else:
        print("⚠️ Không thể cập nhật IP public lên MongoDB.")
except Exception as e:
    print("⚠️ Lỗi khi cập nhật IP lên MongoDB:", e)

# Giữ chương trình chạy
while True:
    time.sleep(60)
