import json
import random
import os
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import database as db
from auth import verify_telegram_webapp_signature

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tarot-backend")

app = FastAPI(title="Tarot Telegram Mini-App API", version="1.0")

# Cấu hình CORS để giao diện Frontend ở tên miền khác (như Vercel/GitHub Pages) gọi được API này
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả các nguồn truy cập (có thể giới hạn lại khi deploy)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chế độ DEBUG_MODE: Cho phép giả lập người dùng khi chạy thử nghiệm trên trình duyệt thường (không có Telegram WebApp)
DEBUG_MODE = os.environ.get("DEBUG_MODE", "True") == "True"

# Tải cơ sở dữ liệu lá bài Tarot từ file tarot_data.json
TAROT_CARDS = []
try:
    with open("tarot_data.json", "r", encoding="utf-8") as f:
        TAROT_CARDS = json.load(f)
    logger.info(f"🔮 Đã nạp thành công {len(TAROT_CARDS)} lá bài Tarot từ database.")
except Exception as e:
    logger.error(f"🔴 Không thể đọc file tarot_data.json: {e}")

# Các Model truyền nhận dữ liệu qua API
class UserStatusRequest(BaseModel):
    initData: str

class DrawCardRequest(BaseModel):
    initData: str
    category: str  # 'daily', 'love', 'career'

class AddEnergyRequest(BaseModel):
    initData: str
    amount: int = 1


def authenticate_user(init_data: str) -> dict:
    """Xác thực người dùng từ initData của Telegram. Trả về thông tin User."""
    if not init_data:
        if DEBUG_MODE:
            # Dữ liệu người dùng giả lập dùng khi test trên trình duyệt Chrome/Edge thường
            logger.info("🔧 [DEBUG MODE] Đang dùng thông tin người dùng giả lập.")
            return {"id": 123456789, "username": "test_trader", "first_name": "Nhà Đầu Tư Mẫu"}
        raise HTTPException(status_code=401, detail="initData is required")

    # Xác thực chữ ký số Telegram
    user_info = verify_telegram_webapp_signature(init_data)
    if not user_info:
        if DEBUG_MODE:
            # Fallback nếu chạy local/test token giả
            logger.info("🔧 [DEBUG MODE] Chữ ký sai nhưng DEBUG_MODE=True, tiếp tục sử dụng user giả.")
            return {"id": 123456789, "username": "test_trader", "first_name": "Nhà Đầu Tư Mẫu"}
        raise HTTPException(status_code=401, detail="Xác thực Telegram thất bại (Unauthorized)")

    return user_info


@app.get("/health")
def health_check():
    """Health check endpoint cho Render"""
    return {"status": "ok", "debug_mode": DEBUG_MODE, "loaded_cards": len(TAROT_CARDS)}


@app.post("/api/user/status")
def get_user_status(req: UserStatusRequest):
    """
    Lấy trạng thái người dùng (Năng lượng hiện có).
    Tự động tạo mới người dùng trong DB nếu chưa tồn tại.
    """
    user_info = authenticate_user(req.initData)
    user_id = user_info.get("id")
    username = user_info.get("username", "")
    first_name = user_info.get("first_name", "")

    # Khởi tạo/Cập nhật thông tin người chơi vào cơ sở dữ liệu
    user_db = db.create_or_update_user(user_id, username, first_name)
    
    # Kiểm tra hồi phục năng lượng hàng ngày (sau 20 tiếng)
    user_db = db.check_daily_refill(user_id)

    return {
        "ok": True,
        "user": user_db
    }


@app.post("/api/tarot/draw")
def draw_tarot_card(req: DrawCardRequest):
    """
    Thực hiện rút 1 lá bài Tarot ngẫu nhiên.
    Trừ 1 năng lượng của người dùng và lưu lịch sử.
    """
    if not TAROT_CARDS:
        raise HTTPException(status_code=500, detail="Tarot card database is empty or not loaded")

    user_info = authenticate_user(req.initData)
    user_id = user_info.get("id")

    # 1. Kiểm tra và trừ năng lượng
    success = db.deduct_energy(user_id, amount=1)
    if not success:
        user_db = db.get_user(user_id)
        raise HTTPException(
            status_code=403, 
            detail="Bạn đã hết năng lượng! Hãy xem quảng cáo để sạc pin và rút tiếp."
        )

    # 2. Chọn ngẫu nhiên 1 lá bài trong bộ 22 lá
    selected_card = random.choice(TAROT_CARDS)

    # 3. Chọn chiều hướng (50% Upright - Chiều xuôi, 50% Reversed - Chiều ngược)
    direction = "upright" if random.random() > 0.5 else "reversed"

    # 4. Lưu lại lịch sử rút bài của tài khoản này
    db.log_draw(user_id, selected_card["card_id"], direction, req.category)

    # Lấy thông tin giải nghĩa theo chiều hướng
    meaning_detail = selected_card["meanings"][direction]

    # Lấy thông tin trạng thái user mới nhất (để cập nhật số năng lượng còn lại)
    updated_user = db.get_user(user_id)

    return {
        "ok": True,
        "card": {
            "card_id": selected_card["card_id"],
            "name": selected_card["name"],
            "image_url": selected_card["image_url"],
            "direction": direction,
            "direction_vietnamese": "Chiều xuôi" if direction == "upright" else "Chiều ngược",
            "interpretation": {
                "general": meaning_detail["general"],
                "love": meaning_detail["love"],
                "career": meaning_detail["career"]
            }
        },
        "user": updated_user
    }


@app.post("/api/user/add-energy")
def reward_ads_energy(req: AddEnergyRequest):
    """
    Cộng năng lượng cho người dùng khi họ hoàn thành xem quảng cáo (Adsgram).
    """
    user_info = authenticate_user(req.initData)
    user_id = user_info.get("id")

    # Cộng năng lượng cho tài khoản
    updated_user = db.add_energy(user_id, req.amount)

    return {
        "ok": True,
        "message": f"Nạp năng lượng thành công! +{req.amount} Energy.",
        "user": updated_user
    }

if __name__ == "__main__":
    import uvicorn
    # Chạy cục bộ trên cổng 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
