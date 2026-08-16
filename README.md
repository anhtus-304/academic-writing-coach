
## 1. Hướng Dẫn Cài Đặt (Setup)

### Bước 1: Mở Terminal tại thư mục dự án
```bash
cd academic-writing-coach
```

### Bước 2: Tạo và kích hoạt Môi trường ảo (Virtual Environment)
```bash
# Di chuyển vào thư mục backend
cd backend

# Tạo venv
python -m venv venv

# Kích hoạt venv:
# Trên Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Trên Windows CMD:
.\venv\Scripts\activate.bat
# Trên macOS/Linux:
source venv/bin/activate
```

### Bước 3: Cài đặt các thư viện phụ thuộc
```bash
pip install -r requirements.txt
```

### Bước 4: Cấu hình Biến môi trường (`.env`)
Tạo file `.env` trong thư mục `backend/` (hoặc copy từ `.env.example`):

```bash
# Trên Windows PowerShell:
Copy-Item .env.example .env
```

Mở file `backend/.env` và cập nhật `OPENROUTER_API_KEY` của bạn:
```env
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-api-key-here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
DEFAULT_MODEL=deepseek/deepseek-chat
FALLBACK_MODEL=deepseek/deepseek-r1
APP_ENV=development
DEBUG=True
```

---

##  2. Hướng Dẫn Chạy Thử (Testing & Running)

Đảm bảo bạn đang ở thư mục gốc của dự án (`academic-writing-coach`):

### 🔹 Cách 1: Chạy thử OutlineAgent (CLI Output JSON)
Sinh dàn ý tự động cho đề tài mẫu và xuất định dạng JSON học thuật:
```bash
python -m backend.agents.outline_agent
```

### 🔹 Cách 2: Chạy Bộ kiểm thử tự động (Pytest)
Kiểm tra nạp 8 bộ template YAML, Pydantic Schema và LangGraph state graph:
```bash
python -m pytest backend/tests/test_outline_agent.py -v
```