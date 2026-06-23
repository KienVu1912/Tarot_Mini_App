// Tự động phát hiện URL Backend phù hợp
// Nếu chạy trên máy cục bộ (localhost), gọi tới cổng 8000 của FastAPI.
// Nếu deploy lên mạng, bạn hãy thay thế địa chỉ Render của bạn ở dòng dưới:
const BACKEND_URL = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://localhost:8000"
    : "https://tarot-backend-app.onrender.com"; // Điền domain Render của bạn khi deploy

let tg = null;
let initData = "";
let currentCategory = "daily";
let userEnergy = 0;

// Bộ emoji đại diện cho các lá bài Tarot (22 lá Ẩn chính) để vẽ lên thẻ bài
const CARD_EMOJIS = {
    "major_0": "🤡", "major_1": "🧙", "major_2": "🧝", "major_3": "👑",
    "major_4": "🏰", "major_5": "⛪", "major_6": "💞", "major_7": "🏎️",
    "major_8": "🦁", "major_9": "🏮", "major_10": "🎡", "major_11": "⚖️",
    "major_12": "🧗", "major_13": "💀", "major_14": "🧪", "major_15": "😈",
    "major_16": "⚡", "major_17": "⭐", "major_18": "🌙", "major_19": "☀️",
    "major_20": "🔔", "major_21": "🌍"
};

// Khởi chạy ứng dụng
document.addEventListener("DOMContentLoaded", () => {
    initTelegramWebApp();
    fetchUserStatus();
    setupEventListeners();
});

// 1. Kết nối với Telegram WebApp SDK
function initTelegramWebApp() {
    if (window.Telegram && window.Telegram.WebApp) {
        tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand(); // Mở rộng màn hình tối đa

        initData = tg.initData || "";

        // Đọc thông tin tên hiển thị từ Telegram
        const user = tg.initDataUnsafe?.user;
        if (user) {
            document.getElementById("user-display-name").textContent = user.first_name || "Nhà Lữ Hành";
            if (user.photo_url) {
                const avatar = document.getElementById("user-avatar");
                avatar.innerHTML = `<img src="${user.photo_url}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">`;
            }
        }
        console.log("📲 Đã khởi chạy trong Telegram WebApp.");
    } else {
        console.log("💻 Chạy trên trình duyệt thường (Chế độ test).");
    }
}

// 2. Lấy trạng thái năng lượng từ Backend
async function fetchUserStatus() {
    showLoader(true);
    try {
        const response = await fetch(`${BACKEND_URL}/api/user/status`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ initData })
        });

        const data = await response.json();
        if (data.ok) {
            updateEnergyUI(data.user.energy);
        } else {
            showError("Không thể tải thông tin người dùng.");
        }
    } catch (e) {
        console.error("Lỗi kết nối API:", e);
        showError("Không thể kết nối đến máy chủ.");
    } finally {
        showLoader(false);
    }
}

// Cập nhật điểm năng lượng hiển thị trên giao diện
function updateEnergyUI(energyVal) {
    userEnergy = energyVal;
    const badge = document.getElementById("energy-counter");
    const label = badge.querySelector(".energy-val");
    label.textContent = `${energyVal} Lượt`;

    // Nếu hết điểm, làm hiệu ứng badge màu đỏ cảnh báo nhẹ
    if (energyVal === 0) {
        badge.style.borderColor = "rgba(244, 67, 54, 0.5)";
        badge.style.background = "rgba(244, 67, 54, 0.1)";
        badge.style.boxShadow = "0 0 10px rgba(244, 67, 54, 0.4)";
    } else {
        badge.style.borderColor = "rgba(255, 215, 0, 0.3)";
        badge.style.background = "rgba(255, 215, 0, 0.1)";
        badge.style.boxShadow = "0 0 15px rgba(255, 215, 0, 0.5)";
    }
}

// 3. Thiết lập các nút bấm điều khiển
function setupEventListeners() {
    // Sự kiện chọn khía cạnh trải bài ở màn hình trang chủ
    document.querySelectorAll(".category-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const category = btn.getAttribute("data-category");
            startTarotDrawFlow(category);
        });
    });

    // Sự kiện nút Xem Ads nạp năng lượng
    document.getElementById("watch-ads-btn").addEventListener("click", () => {
        triggerAdsgramAd();
    });

    // Quay lại từ màn hình chọn bài
    document.getElementById("draw-back-btn").addEventListener("click", () => {
        switchScreen("home-screen");
    });

    // Quay lại trang chủ từ màn hình kết quả lật bài
    document.getElementById("btn-back-home").addEventListener("click", () => {
        // Thu hồi hiệu ứng lật bài
        document.getElementById("tarot-card-reveal").classList.remove("flipped");
        switchScreen("home-screen");
    });
}

// 4. Bắt đầu quy trình chọn và rút bài Tarot
function startTarotDrawFlow(category) {
    currentCategory = category;

    // Đổi tên danh mục hiển thị
    const catNames = { daily: "Tổng Quan Ngày", love: "Tình Duyên", career: "Sự Nghiệp" };
    document.getElementById("current-category-name").textContent = catNames[category];

    // Vẽ bộ bài 6 lá úp mặt để người dùng chọn
    const deckWrapper = document.getElementById("deck-wrapper");
    deckWrapper.innerHTML = "";

    for (let i = 0; i < 6; i++) {
        const card = document.createElement("div");
        card.className = "card-item";
        card.addEventListener("click", () => handleCardSelection());
        deckWrapper.appendChild(card);
    }

    switchScreen("draw-screen");
}

// 5. Xử lý khi người dùng nhấn vào 1 lá bài úp trên bàn
async function handleCardSelection() {
    if (userEnergy <= 0) {
        showError("Bạn đã hết lượt rút bài! Hãy xem quảng cáo video để sạc thêm lượt.");
        return;
    }

    showLoader(true);
    try {
        const response = await fetch(`${BACKEND_URL}/api/tarot/draw`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ initData, category: currentCategory })
        });

        const data = await response.json();

        if (response.status === 403) {
            showError("Hết năng lượng! Hãy xem Ads để sạc thêm lượt.");
            return;
        }

        if (data.ok) {
            // Nạp dữ liệu lá bài rút được vào màn hình Kết quả
            const card = data.card;
            document.getElementById("card-name-text").textContent = card.name;
            document.getElementById("card-orientation-text").textContent = card.direction_vietnamese;

            // Xoay ảnh/emoji nếu là chiều ngược
            const artBox = document.getElementById("card-art-box");
            if (card.direction === "reversed") {
                artBox.style.transform = "rotate(180deg)";
            } else {
                artBox.style.transform = "rotate(0deg)";
            }

            // Gán emoji tương ứng của lá bài
            const emoji = CARD_EMOJIS[card.card_id] || "🔮";
            document.getElementById("card-art-emoji").textContent = emoji;

            // Gán lời giải nghĩa tương ứng với khía cạnh đã chọn
            const meaning = card.interpretation[currentCategory] || card.interpretation.general;
            document.getElementById("meaning-desc-text").textContent = meaning;

            // Cập nhật số năng lượng mới nhận từ DB
            updateEnergyUI(data.user.energy);

            // Chuyển sang màn hình kết quả và kích hoạt hiệu ứng lật bài sau 300ms
            switchScreen("result-screen");
            setTimeout(() => {
                document.getElementById("tarot-card-reveal").classList.add("flipped");
            }, 300);

        } else {
            showError(data.detail || "Không thể rút bài. Vui lòng thử lại.");
        }
    } catch (e) {
        console.error("Lỗi khi rút bài:", e);
        showError("Không thể kết nối đến máy chủ.");
    } finally {
        showLoader(false);
    }
}

// 6. Xử lý tích hợp quảng cáo Adsgram để nhận thưởng
function triggerAdsgramAd() {
    // ID Khối quảng cáo (Block ID) của bạn được Adsgram cấp sau khi bạn add bot vào nền tảng của họ.
    // Dưới đây là Block ID Test mặc định để bạn chạy thử nghiệm (luôn hoạt động để test).
    const blockId = "35977"; // Thay thế bằng ID thật của bạn sau khi đăng ký thành công

    if (window.Adsgram) {
        const AdController = window.Adsgram.init({ blockId: blockId });
        showLoader(true);

        AdController.show()
            .then((result) => {
                // Người dùng đã xem xong quảng cáo thành công
                console.log("Xem quảng cáo thành công:", result);
                rewardEnergyFromServer(1);
            })
            .catch((err) => {
                // Người dùng tắt giữa chừng hoặc lỗi hiển thị quảng cáo
                console.warn("Quảng cáo bị bỏ qua hoặc lỗi:", err);
                showError("Bạn cần xem hết video quảng cáo để nhận lượt rút bài miễn phí.");
                showLoader(false);
            });
    } else {
        // Trường hợp chạy local không có mạng/không tải được SDK Adsgram
        // Ta tạo một hộp thoại mô phỏng xem quảng cáo để nhà phát triển dễ dàng test
        const confirmMock = confirm("[MÔ PHỎNG ADSGRAM] Bạn có muốn giả lập xem hết 1 video quảng cáo để nhận thêm 1 lượt rút không?");
        if (confirmMock) {
            rewardEnergyFromServer(1);
        }
    }
}

// Gửi yêu cầu cộng năng lượng lên Backend sau khi xem Ads thành công
async function rewardEnergyFromServer(amount) {
    showLoader(true);
    try {
        const response = await fetch(`${BACKEND_URL}/api/user/add-energy`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ initData, amount })
        });
        const data = await response.json();
        if (data.ok) {
            updateEnergyUI(data.user.energy);
            alert(`🎉 Nạp năng lượng thành công! Bạn nhận được +${amount} lượt rút bài.`);
        } else {
            showError("Không thể nạp năng lượng từ máy chủ.");
        }
    } catch (e) {
        console.error("Lỗi nạp năng lượng:", e);
        showError("Lỗi kết nối máy chủ nạp năng lượng.");
    } finally {
        showLoader(false);
    }
}

// --- Các hàm tiện ích bổ trợ ---

// Chuyển đổi qua lại giữa các màn hình
function switchScreen(screenId) {
    document.querySelectorAll(".screen").forEach(screen => {
        screen.classList.add("hidden");
    });
    document.getElementById(screenId).classList.remove("hidden");
}

// Hiển thị/Ẩn vòng xoay loading
function showLoader(show) {
    const loader = document.getElementById("loader");
    if (show) {
        loader.classList.remove("hidden");
    } else {
        loader.classList.add("hidden");
    }
}

// Hiển thị hộp thông báo lỗi/thông tin cho người dùng
function showError(msg) {
    if (tg) {
        tg.showAlert(msg);
    } else {
        alert(msg);
    }
}
