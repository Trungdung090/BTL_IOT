import sqlite3

# Kết nối (hoặc tạo mới) database có tên "access_control.db"
conn = sqlite3.connect("access_control.db")

# Tạo một đối tượng cursor để thao tác với database
cursor = conn.cursor()

# Tạo bảng để lưu thông tin người ra vào
cursor.execute('''
    CREATE TABLE IF NOT EXISTS access_control (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        time TEXT NOT NULL,
        people_count INTEGER DEFAULT 0
        )''')

# Lưu thay đổi
conn.commit()

# Đóng kết nối
conn.close()

print("Database và bảng đã được tạo thành công!")
