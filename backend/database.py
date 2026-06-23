import sqlite3
import time
import os

DB_FILE = "tarot_users.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Khởi tạo cấu trúc các bảng dữ liệu nếu chưa tồn tại"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Bảng người dùng
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        energy INTEGER DEFAULT 5,
        last_energy_refill INTEGER DEFAULT 0,
        created_at INTEGER
    )
    """)
    
    # Bảng lịch sử rút bài
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS draw_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER,
        card_id TEXT,
        direction TEXT,
        category TEXT,
        draw_time INTEGER,
        FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
    )
    """)
    
    conn.commit()
    conn.close()

def get_user(telegram_id):
    """Lấy thông tin người dùng từ DB"""
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
    conn.close()
    if user:
        return dict(user)
    return None

def create_or_update_user(telegram_id, username, first_name):
    """Tạo người dùng mới hoặc cập nhật thông tin nếu đã tồn tại"""
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
    
    now = int(time.time())
    if not user:
        # Tạo người dùng mới, tặng sẵn 5 năng lượng
        conn.execute(
            "INSERT INTO users (telegram_id, username, first_name, energy, last_energy_refill, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (telegram_id, username, first_name, 5, now, now)
        )
    else:
        # Cập nhật username, first_name nếu thay đổi
        conn.execute(
            "UPDATE users SET username = ?, first_name = ? WHERE telegram_id = ?",
            (username, first_name, telegram_id)
        )
    
    conn.commit()
    
    # Đọc lại user vừa tạo/cập nhật
    updated_user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
    conn.close()
    return dict(updated_user)

def check_daily_refill(telegram_id):
    """Hồi phục năng lượng hàng ngày (tối đa hồi phục về 5 năng lượng mỗi ngày)"""
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
    
    if not user:
        conn.close()
        return None
        
    now = int(time.time())
    last_refill = user["last_energy_refill"]
    current_energy = user["energy"]
    
    # Kiểm tra xem đã qua ngày mới chưa (86400 giây = 24 giờ)
    # Hoặc đơn giản là kiểm tra sự khác biệt ngày theo múi giờ địa phương
    # Ở đây dùng đơn giản là cách nhau 20 tiếng để người chơi dễ nhận năng lượng mới hàng ngày
    if now - last_refill >= 72000:  # 20 tiếng
        if current_energy < 5:
            conn.execute(
                "UPDATE users SET energy = 5, last_energy_refill = ? WHERE telegram_id = ?",
                (now, telegram_id)
            )
            conn.commit()
            
    updated_user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
    conn.close()
    return dict(updated_user)

def add_energy(telegram_id, amount):
    """Cộng thêm năng lượng cho người chơi (ví dụ khi xem xong ads)"""
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
    
    if not user:
        conn.close()
        return None
        
    new_energy = user["energy"] + amount
    conn.execute("UPDATE users SET energy = ? WHERE telegram_id = ?", (new_energy, telegram_id))
    conn.commit()
    
    updated_user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
    conn.close()
    return dict(updated_user)

def deduct_energy(telegram_id, amount=1):
    """Trừ năng lượng của người dùng khi thực hiện rút bài"""
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
    
    if not user or user["energy"] < amount:
        conn.close()
        return False
        
    new_energy = user["energy"] - amount
    conn.execute("UPDATE users SET energy = ? WHERE telegram_id = ?", (new_energy, telegram_id))
    conn.commit()
    conn.close()
    return True

def log_draw(telegram_id, card_id, direction, category):
    """Lưu lịch sử rút bài của người dùng"""
    conn = get_db_connection()
    now = int(time.time())
    conn.execute(
        "INSERT INTO draw_history (telegram_id, card_id, direction, category, draw_time) VALUES (?, ?, ?, ?, ?)",
        (telegram_id, card_id, direction, category, now)
    )
    conn.commit()
    conn.close()

# Khởi tạo bảng ngay khi import module
init_db()
