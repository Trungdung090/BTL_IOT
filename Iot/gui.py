import base64
import cv2
import os
import sqlite3
import threading
import queue
import paho.mqtt.client as mqtt
from datetime import datetime
from flask import Flask, render_template, send_from_directory, jsonify, request
from ultralytics import YOLO
import numpy as np

# Thông tin MQTT
MQTT_BROKER = "ca22e3360eda4cb68d49d3fcc4a16b58.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_TOPIC = "camera/image"
MQTT_USER = "dangtrungdung23"
MQTT_PASS = "Dung123456@"

# Cấu hình lưu ảnh
image_parts = ""
total_parts = 0
received_parts = 0
UPLOAD_FOLDER = "./uploads"   # Thư mục lưu ảnh
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Biến lưu tên ảnh hiện tại để hiển thị trong web
processed_image = ""    # Lưu ảnh đã nhận diện

# Load model YOLO
model_path = r"D:\Pycharm\Iot\train5\train5\weights\best.pt"
model = YOLO(model_path)

# Hàng đợi xử lý database
db_queue = queue.Queue()

def db_worker():
    conn = sqlite3.connect("access_control.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        time TEXT NOT NULL UNIQUE,       -- Đảm bảo mỗi thời điểm chỉ có 1 bản ghi
        people_count INTEGER DEFAULT 0,
        image_name TEXT
    )''')
    conn.commit()

    while True:
        query, params = db_queue.get()
        if query == "STOP":
            break
        cursor.execute(query, params)
        conn.commit()
    conn.close()        # Đóng kết nối sau khi sử dụng

def save_log(timestamp, people_count, image_name):
    if people_count >= 1:   # Chỉ lưu nếu phát hiện ít nhất 1 người
        time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect("access_control.db")
        cursor = conn.cursor()

        # Lấy ID lớn nhất hiện tại
        cursor.execute("SELECT MAX(id) FROM logs")
        max_id = cursor.fetchone()[0]  # Lấy giá trị lớn nhất
        new_id = 1 if max_id is None else max_id + 1  # Nếu không có dữ liệu, bắt đầu từ 1

        # Chèn dữ liệu với ID mới
        cursor.execute("INSERT INTO logs (id, time, people_count, image_name) VALUES (?, ?, ?, ?)",
                       (new_id, timestamp, people_count, image_name))
        conn.commit()

def detect_people(image_path):
    global processed_image  # Cập nhật biến này để gửi ảnh lên web
    image = cv2.imread(image_path)
    if image is None:
        print("Không thể mở ảnh")
        return 0
    results = model(image)
    boxes = results[0].boxes.xyxy.cpu().numpy()      # Chuyển tensor sang numpy
    people_count = len(boxes)

    if people_count >= 1:  # Chỉ xử lý khi có người
        for box in boxes:
            x1, y1, x2, y2 = map(int, box[:4])
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(image, 'Nguoi', (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        processed_image_name = "processed_" + os.path.basename(image_path)
        processed_image_path = os.path.join(UPLOAD_FOLDER, processed_image_name)
        cv2.imwrite(processed_image_path, image)
        processed_image = processed_image_name  # Cập nhật tên ảnh đã nhận diện
        save_log(people_count, processed_image_name)
        return people_count
    else:
        print("Không phát hiện người, không lưu ảnh.")
        os.remove(image_path)  # Xóa ảnh nếu không phát hiện người
        return 0

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"Connected with result code {rc}")
    client.subscribe(MQTT_TOPIC)

# Hàm nhận dữ liệu từ MQTT
def on_message(client, userdata, msg):
    global image_parts, total_parts, received_parts, processed_image
    message = msg.payload.decode()

    if message == "end":
        #print("End of image transmission received.")
        #print("Final concatenated image data (Base64):")
        #print(image_parts)

        # Lưu ảnh với timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"image_{timestamp}.jpg"
        file_path = os.path.join(UPLOAD_FOLDER, file_name)

        try:
            image_bytes = base64.b64decode(image_parts)
            with open(file_path, "wb") as img_file:
                img_file.write(image_bytes)
            print(f"Ảnh đã lưu: {file_name}")
            #processed_image = file_name
            people_count = detect_people(file_path)
            print(f"Số người phát hiện: {people_count}")
        except Exception as e:
            print(f"⚠️ Lỗi giải mã ảnh: {e}")
        image_parts = ""
        received_parts = 0
        total_parts = 0
    else:
        try:
            if '/' in message:
                index, rest = message.split('/', 1)
                index = int(index)
                part_data = rest.split(':', 1)[1]
                if received_parts == 0:
                    total_parts = int(rest.split('/', 1)[0].split(":")[0])
                image_parts += part_data
                received_parts += 1
            else:
                print(f"Lỗi tin nhắn không hợp lệ: {message}")
        except Exception as e:
            print(f"Lỗi xử lý dữ liệu MQTT: {e}")

# Thiết lập Flask
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index1.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Không có file nào được gửi!'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Chưa chọn file nào!'})

    # Lưu ảnh vào thư mục uploads
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"uploaded_{timestamp}.jpg"
    file_path = os.path.join(UPLOAD_FOLDER, file_name)
    try:
        file.save(file_path)
        print(f"Ảnh đã được lưu: {file_name}")  # Debug
        # Nhận diện người và cập nhật database
        people_count = detect_people(file_path)     # Gọi nhận diện, detect_people() sẽ tự lưu log
        return jsonify({'success': True, 'image_name': file_name, 'people_count': people_count})
    except Exception as e:
        print(f"Lỗi khi lưu ảnh: {e}")
        return jsonify({'success': False, 'error': 'Lỗi lưu ảnh!'})

@app.route('/processed-image')
def get_processed_image():
    return jsonify({'image_name': processed_image})

@app.route('/density-hourly')
def get_hourly_density():
    try:
        conn = sqlite3.connect("access_control.db")
        cursor = conn.cursor()

        # Truy vấn dữ liệu, nhóm theo giờ
        cursor.execute("""
            SELECT strftime('%H', time) as hour,SUM(people_count) as people_count 
            FROM logs 
            WHERE date(time) = date('now')  -- Lọc theo ngày hiện tại
            GROUP BY hour 
            ORDER BY hour
        """)
        data = {row[0]: row[1] for row in cursor.fetchall()}  # Chuyển thành dict
        conn.close()
        # Tạo danh sách đủ 24 giờ
        full_data = [{"hour": f"{h:02d}", "people_count": data.get(f"{h:02d}", 0)} for h in range(24)]

        return jsonify(full_data)   # ✅ Trả về danh sách JSON đủ 24 giờ
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/access_control')
def get_logs():
    conn = sqlite3.connect("access_control.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 20")  # Lấy 20 bản ghi mới nhất
    logs = [{"id": row[0], "time": row[1], "people_count": row[2], "image_name": row[3]} for row in cursor.fetchall()]
    conn.close()
    return jsonify(logs)

@app.route('/reset_database', methods=['POST'])
def reset_database():
    conn = sqlite3.connect("access_control.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM logs")  # Xóa toàn bộ dữ liệu trong bảng logs
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='logs'")
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Database đã được làm mới!'})

def mqtt_loop():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set()    # Nếu dùng TLS
    client.tls_insecure_set(True)
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.subscribe(MQTT_TOPIC)
    client.loop_start()     # Khởi động vòng lặp xử lý

if __name__ == "__main__":
    threading.Thread(target=db_worker, daemon=True).start()
    threading.Thread(target=mqtt_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)