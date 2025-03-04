import base64
from flask import Flask, render_template, send_from_directory, jsonify
import paho.mqtt.client as mqtt
import os
from datetime import datetime
import threading
from ultralytics import YOLO

# Các thông số MQTT từ HiveMQ
MQTT_BROKER = "ebf16958b9164dddb8a78512f3aca426.s1.eu.hivemq.cloud"  # Địa chỉ broker HiveMQ
MQTT_PORT = 8883                   # Cổng cho SSL
MQTT_TOPIC = "camera/image"        # Chủ đề MQTT bạn muốn nhận

# Thông tin xác thực
MQTT_USER = "dangtrungdung23"   # Thay thế với tên người dùng của bạn
MQTT_PASS = "Dung123456@"   # Thay thế với mật khẩu của bạn

# Dữ liệu buffer để lưu ảnh
image_data = ""
total_parts = 0
received_parts = 0
UPLOAD_FOLDER = "./uploads"  # Thư mục lưu ảnh
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Biến lưu tên ảnh hiện tại để hiển thị trong web
current_image = ""

# Load YOLO model
model_path = r'D:\Pycharm\Iot\train5\train5\weights\best.pt'  # Đường dẫn mô hình
model = YOLO(model_path)

# Callback khi kết nối MQTT thành công
def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe(MQTT_TOPIC)

# Callback khi nhận thông điệp từ MQTT
def on_message(client, userdata, msg):
    global image_data, total_parts, received_parts, current_image
    message = msg.payload.decode()

    if message == "end":
        #print("End of image transmission received.")
        #print("Final concatenated image data (Base64):")
        #print(image_data)

        # Lưu ảnh với timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"image_{timestamp}.jpg"
        file_path = os.path.join(UPLOAD_FOLDER, file_name)

        if not image_data:
            print("No image data to decode!")
            return
        try:
            image_bytes = base64.b64decode(image_data)
            with open(file_path, "wb") as img_file:
                img_file.write(image_bytes)
            print(f"Image saved as {file_name}")
            current_image = file_name
        except Exception as e:
            print(f"Error decoding base64 data: {e}")
        image_data = ""
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
                image_data += part_data
                received_parts += 1
            else:
                print(f"Receive d invalid message: {message}")
        except Exception as e:
            print(f"Error processing message: {e}")

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/current-image')
def current_image_route():
    return jsonify({'image_name': current_image})

def mqtt_loop():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    # Cung cấp thông tin xác thực
    client.username_pw_set(MQTT_USER, MQTT_PASS)

    # Kết nối với SSL
    client.tls_set()  # Thiết lập kết nối SSL
    client.tls_insecure_set(True)  # Bỏ qua kiểm tra chứng chỉ nếu không có CA
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

if __name__ == "__main__":
    mqtt_thread = threading.Thread(target=mqtt_loop)
    mqtt_thread.start()

    app.run(host="0.0.0.0", port=5000, debug=True)




