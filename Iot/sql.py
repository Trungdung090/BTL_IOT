import sqlite3

# Kết nối (hoặc tạo mới) database có tên "access_control.db"
conn = sqlite3.connect("access_control.db")
# Tạo một đối tượng cursor để thao tác với database
cursor = conn.cursor()
cursor.execute("SELECT * FROM logs ORDER BY time DESC LIMIT 20")
rows = cursor.fetchall()

for row in rows:
    print(row)
# Đóng kết nối
conn.close()
print("Database và bảng đã được tạo thành công!")
