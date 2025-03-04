#include "esp_camera.h"
#include <WiFi.h>
#include <base64.h>
#include <PubSubClient.h>  // Thư viện MQTT
#include <WiFiClientSecure.h> // Thư viện hỗ trợ kết nối SSL

#define CAMERA_MODEL_AI_THINKER 
#include "camera_pins.h"

// Wi-Fi credentials1
const char* ssid = ".....";
const char* password = "888899999";

// MQTT broker details
const char* mqtt_server = "ebf16958b9164dddb8a78512f3aca426.s1.eu.hivemq.cloud";
const int mqtt_port = 8883;
const char* mqtt_topic = "camera/image"; // Chủ đề để gửi ảnh

// Thêm tên đăng nhập và mật khẩu MQTT
const char* mqtt_user = "dangtrungdung23";  // Tên đăng nhập MQTT
const char* mqtt_password = "Dung123456@";  // Mật khẩu MQTT

void startCameraServer();
void setupLedFlash(int pin);

WiFiClientSecure espClient;  // Thay WiFiClient bằng WiFiClientSecure
PubSubClient client(espClient);

void connectMQTT() {
  while (!client.connected()) {
    Serial.println("Đang kết nối MQTT...");
    if (client.connect("ESP32Client", mqtt_user, mqtt_password)) {
      Serial.println("Connected to MQTT Broker!");
    } else {
      Serial.print("Failed. Retrying...");
      Serial.print(client.state());
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.frame_size = FRAMESIZE_SVGA;
  config.pixel_format = PIXFORMAT_JPEG; // for streaming
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 12;
  config.fb_count = 1;
  
  if(config.pixel_format == PIXFORMAT_JPEG){
    // Chất lượng ảnh
    if(psramFound()){
      config.jpeg_quality = 10;
      config.fb_count = 2;
      config.grab_mode = CAMERA_GRAB_LATEST;
    } else {
      config.frame_size = FRAMESIZE_SVGA;
      config.fb_location = CAMERA_FB_IN_DRAM;
    }
  } else {
    // Best option for face detection/recognition
    config.frame_size = FRAMESIZE_240X240;
#if CONFIG_IDF_TARGET_ESP32S3
    config.fb_count = 2;
#endif
  }

  // camera init
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

  sensor_t * s = esp_camera_sensor_get();
  if (s->id.PID == OV3660_PID) {
    s->set_vflip(s, 1); // flip it back
    s->set_brightness(s, 1); // up the brightness just a bit
    s->set_saturation(s, -2); // lower the saturation
  }
  if(config.pixel_format == PIXFORMAT_JPEG){
    s->set_framesize(s, FRAMESIZE_QVGA);
  }

// Setup LED FLash if LED pin is defined in camera_pins.h
#if defined(LED_GPIO_NUM)
  setupLedFlash(LED_GPIO_NUM);
#endif

  // Kết nối Wi-Fi
  WiFi.begin(ssid, password);
  WiFi.setSleep(false);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
  Serial.println("WiFi connected");

    startCameraServer();

  // Kết nối với MQTT qua SSL mà không cần chứng chỉ
  espClient.setInsecure();  // Thiết lập SSL không cần chứng chỉ
  client.setServer(mqtt_server, mqtt_port);

  while (!client.connected()) {
    connectMQTT();  
  }
  Serial.print("Camera Ready! Use 'http://");
  Serial.print(WiFi.localIP());
  Serial.println("' to connect");
}

void sendEncodedImage() {
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed");
    return;
  }

  // Mã hóa ảnh sang Base64
  String encodedImage = base64::encode(fb->buf, fb->len);

  // Chia nhỏ Base64 thành các phần nhỏ và gửi qua MQTT
  int partSize = 200; // Kích thước mỗi phần (tùy chỉnh)
  int totalParts = (encodedImage.length() + partSize - 1) / partSize;

  for (int i = 0; i < totalParts; i++) {
    String part = encodedImage.substring(i * partSize, (i + 1) * partSize);
    String message = String(i + 1) + "/" + String(totalParts) + ":" + part;
    client.publish(mqtt_topic, message.c_str());
    delay(100); // Thời gian giữa các phần gửi
  }

  // Gửi thông báo kết thúc
  client.publish(mqtt_topic, "end");
  Serial.println("Ảnh đã gửi thành công!");

  // Giải phóng bộ nhớ ảnh
  esp_camera_fb_return(fb);
}

void loop() {
  if (!client.connected()) {
    connectMQTT();  // Kiểm tra và kết nối lại MQTT nếu mất kết nối
  }
  client.loop();  // Xử lý các tin nhắn MQTT

  // Chụp ảnh và gửi lên MQTT
  sendEncodedImage();
  delay(5000);  // Gửi ảnh mỗi 5 giây
}
