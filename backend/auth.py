import hmac
import hashlib
import urllib.parse
import json
import os
import logging

logger = logging.getLogger("tarot-auth")

# Cấu hình Token của Bot Telegram dùng để đối chiếu mã băm xác thực
# Khuyên khích đặt trong biến môi trường để bảo mật
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8872959175:AAHuNvRb629xV9kGVWIKBXOIMsEhwfKVhDY")

def verify_telegram_webapp_signature(init_data_raw: str) -> dict | None:
    """
    Xác thực chữ ký số được gửi từ Telegram WebApp Client.
    Xem chi tiết cơ chế tại: https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app
    """
    if not init_data_raw:
        logger.error("🔴 initData trống")
        return None
        
    try:
        # Giải mã query string từ client gửi lên
        parsed_data = urllib.parse.parse_qsl(init_data_raw, keep_blank_values=True)
        data_dict = dict(parsed_data)
        
        if "hash" not in data_dict:
            logger.error("🔴 Không tìm thấy trường hash trong initData")
            return None
            
        tg_hash = data_dict.pop("hash")
        
        # Sắp xếp các tham số theo bảng chữ cái và ghép lại bằng ký tự xuống dòng (\n)
        # Xem tài liệu Telegram: các tham số phải được sắp xếp tăng dần theo khóa
        sorted_items = sorted(data_dict.items())
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_items)
        
        # Bước 1: Tạo secret key từ Bot Token bằng mã khóa cố định "WebAppData"
        secret_key = hmac.new(
            b"WebAppData",
            TELEGRAM_BOT_TOKEN.encode("utf-8"),
            hashlib.sha256
        ).digest()
        
        # Bước 2: Tạo mã băm từ data_check_string với secret key vừa tạo
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        # Bước 3: So sánh mã băm của chúng ta với hash do Telegram gửi lên
        if calculated_hash != tg_hash:
            logger.warning("⚠️ Chữ ký xác thực Telegram không hợp lệ (Mã băm không khớp)")
            # Cho mục đích thử nghiệm cục bộ (Local Testing) khi không chạy qua Telegram thật:
            # Nếu chạy local mà không truyền token thật, ta có thể bỏ qua dòng này hoặc ghi log.
            # Trong production bắt buộc phải trả về None.
            return None
            
        # Giải mã trường 'user' để lấy thông tin chi tiết (id, username, first_name)
        if "user" in data_dict:
            user_data = json.loads(urllib.parse.unquote(data_dict["user"]))
            return user_data
            
        return data_dict
        
    except Exception as e:
        logger.error(f"🔴 Lỗi trong quá trình xác thực chữ ký: {e}")
        return None
