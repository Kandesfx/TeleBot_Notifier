import json
import threading
import requests
import winsound
import tkinter as tk
import websocket
import time
from pymongo import MongoClient
from pystray import Icon, MenuItem, Menu
from PIL import Image

# 🔹 Kết nối MongoDB Atlas
MONGO_URI = "mongodb+srv://kandesfx:hehe1234@kandes.xdh45.mongodb.net/?retryWrites=true&w=majority&appName=Kandes"
client = MongoClient(MONGO_URI)
db = client['telebot']
ip_collection = db['server_ip']

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

# ======================= HIỂN THỊ CỬA SỔ CẢNH BÁO =======================
def show_alert(title, message):
    def close_window():
        alert_window.destroy()
    
    winsound.MessageBeep()
    alert_window = tk.Tk()
    alert_window.title(title)
    alert_window.geometry("300x150")
    
    tk.Label(alert_window, text=message, font=("Arial", 14), fg="red").pack(pady=20)
    tk.Button(alert_window, text="OK", command=close_window).pack()
    
    alert_window.mainloop()

# ======================= NHẬN THÔNG BÁO QUA WEBSOCKET =======================
def on_message(ws, message):
    data = json.loads(message)
    if "title" in data and "body" in data:
        show_alert(data["title"], data["body"])

def on_error(ws, error):
    print("❌ Lỗi WebSocket:", error)

def on_close(ws, close_status_code, close_msg):
    print("🔌 Kết nối WebSocket bị đóng.")

def on_open(ws):
    print("✅ Kết nối WebSocket thành công!")

def start_websocket():
    while True:
        try:
            print(f"🔗 Kết nối WebSocket tới {WS_SERVER}...")
            ws = websocket.WebSocketApp(WS_SERVER, on_message=on_message, on_error=on_error, on_close=on_close)
            ws.on_open = on_open
            ws.run_forever()
        except Exception as e:
            print("❌ Lỗi khi kết nối WebSocket:", e)
        time.sleep(5)  # Thử kết nối lại sau 5 giây nếu lỗi

# ======================= CHẠY ỨNG DỤNG TRONG SYSTEM TRAY =======================
def create_tray_icon():
    try:
        icon_image = Image.open("icon.png")
        menu = Menu(MenuItem("Thoát", lambda: exit(0)))
        tray_icon = Icon("notification_client", icon_image, menu=menu)
        tray_icon.run()
    except FileNotFoundError:
        print("⚠️ Không tìm thấy icon.png!")

# 🔹 Chạy ứng dụng
threading.Thread(target=auto_update_server_ip, daemon=True).start()
time.sleep(5)  # Chờ cập nhật IP trước khi kết nối WebSocket
threading.Thread(target=start_websocket, daemon=True).start()
threading.Thread(target=create_tray_icon, daemon=True).start()
while True:
    time.sleep(60)