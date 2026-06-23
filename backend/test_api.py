import os
import sys

# Khắc phục lỗi hiển thị tiếng Việt có dấu và emoji trên Windows Command Prompt/PowerShell
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Đảm bảo python tìm thấy các file trong thư mục hiện tại
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_flow():
    print("🧪 Bắt đầu kiểm tra hệ thống API Tarot...")

    # 1. Test Endpoint /health
    print("\n1. Đang gọi API Health Check...")
    res = client.get("/health")
    print(f"Status code: {res.status_code}")
    print(f"Response: {res.json()}")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # 2. Test Endpoint /api/user/status
    print("\n2. Đang lấy thông tin User (Khởi tạo năng lượng mặc định = 5)...")
    res = client.post("/api/user/status", json={"initData": ""})
    print(f"Status code: {res.status_code}")
    user_data = res.json()
    print(f"Response: {user_data}")
    assert res.status_code == 200
    assert user_data["ok"] is True
    assert user_data["user"]["energy"] == 5

    # 3. Test Endpoint /api/tarot/draw (Rút bài)
    print("\n3. Đang rút bài Tarot ngẫu nhiên (Lượt 1)...")
    res = client.post("/api/tarot/draw", json={"initData": "", "category": "daily"})
    print(f"Status code: {res.status_code}")
    draw_data = res.json()
    print(f"Response: {draw_data}")
    assert res.status_code == 200
    assert draw_data["ok"] is True
    assert "card" in draw_data
    # Năng lượng còn lại phải là 4
    assert draw_data["user"]["energy"] == 4

    # 4. Test Rút tiếp cho đến khi hết năng lượng để kiểm tra chặn lỗi
    print("\n4. Rút tiếp 4 lượt nữa để kiểm tra chặn lỗi khi hết năng lượng...")
    for i in range(4):
        client.post("/api/tarot/draw", json={"initData": "", "category": "daily"})
    
    # Lượt thứ 6 (hết năng lượng)
    print("Rút lượt thứ 6 khi năng lượng = 0...")
    res = client.post("/api/tarot/draw", json={"initData": "", "category": "daily"})
    print(f"Status code: {res.status_code}")
    print(f"Response: {res.json()}")
    # Phải trả về lỗi 403 Forbidden
    assert res.status_code == 403

    # 5. Test Endpoint /api/user/add-energy (Cộng năng lượng sau khi xem Ads)
    print("\n5. Đang giả lập xem Ads xong để cộng 3 năng lượng...")
    res = client.post("/api/user/add-energy", json={"initData": "", "amount": 3})
    print(f"Status code: {res.status_code}")
    ads_data = res.json()
    print(f"Response: {ads_data}")
    assert res.status_code == 200
    assert ads_data["ok"] is True
    assert ads_data["user"]["energy"] == 3

    print("\n✅ Tất cả các API hoạt động hoàn hảo và kiểm thử thành công!")

if __name__ == "__main__":
    test_flow()
