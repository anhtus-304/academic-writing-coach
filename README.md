# 🎓 AI Academic Writing Coach

Hệ thống Hỗ trợ Viết bài Nghiên cứu & Luận văn Học thuật thông minh ứng dụng AI Multi-Agent (FastAPI + DeepSeek AI + PostgreSQL + Next.js).

---

## 📋 Mục lục
1. [Yêu cầu hệ thống](#1-yêu-cầu-hệ-thống-prerequisites)
2. [Cấu hình Cơ sở dữ liệu (PostgreSQL)](#2-cấu-hình-cơ-sở-dữ-liệu-postgresql)
3. [Cấu hình Biến môi trường (.env)](#3-cấu-hình-biến-môi-trường-backendenv)
4. [Hướng dẫn lấy Google OAuth Credentials](#4-hướng-dẫn-lấy-google_client_id-và-google_client_secret)
5. [Cài đặt & Khởi chạy Backend](#5-cài-đặt--khởi-chạy-backend-fastapi)
6. [Cài đặt & Khởi chạy Frontend](#6-cài-đặt--khởi-chạy-frontend-nextjs)
7. [Kiểm thử Hệ thống (Testing)](#7-kiểm-thử-hệ-thống-testing)

---

## 1. Yêu cầu hệ thống (Prerequisites)
- **Python**: 3.11 hoặc 3.12
- **Node.js**: 18.x trở lên và **npm**
- **Docker** (Khuyến nghị) hoặc **PostgreSQL 15+** cài đặt trên máy
- **Git**

---

## 2. Cấu hình Cơ sở dữ liệu (PostgreSQL)

Hệ thống hỗ trợ 2 cách kết nối cơ sở dữ liệu:

### 🔹 Cách 1: Sử dụng Docker (Khuyến nghị - Nhanh nhất)
Chạy container PostgreSQL với lệnh sau (ánh xạ port `5433` tránh xung đột với Postgres có sẵn trên máy):

```bash
docker run --name academic-postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=academic_writing -p 5433:5432 -d postgres
```

> **Chuỗi kết nối tương ứng:**  
> `DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/academic_writing`

*Kiểm tra Docker container đang chạy:*
```bash
docker ps
```

---

### 🔹 Cách 2: Sử dụng PostgreSQL cài trên máy cá nhân
1. Mở `pgAdmin` hoặc công cụ dòng lệnh `psql`:
```sql
-- Đăng nhập vào PostgreSQL và tạo database mới
CREATE DATABASE academic_writing;
```
2. Thiết lập chuỗi kết nối với tài khoản, mật khẩu và cổng (mặc định `5432`) của PostgreSQL trên máy bạn:
> **Chuỗi kết nối tương ứng:**  
> `DATABASE_URL=postgresql+asyncpg://<username>:<password>@localhost:5432/academic_writing`  

---

### 🔹 Khởi tạo cấu trúc bảng Database (Migration với Alembic)
Sau khi database đã sẵn sàng và đã kích hoạt môi trường ảo `venv` của backend:

```bash
cd backend
alembic upgrade head
```

*Kiểm tra danh sách bảng đã tạo trong Docker:*
```bash
docker exec -it academic-postgres psql -U postgres -d academic_writing -c "\dt"
```

---

## 3. Cấu hình Biến môi trường (`backend/.env`)

Tạo file `.env` bên trong thư mục `backend/` với nội dung chuẩn như sau:

```env
# Project & API Core
PROJECT_NAME=Academic Writing Coach
API_V1_STR=/api/v1
APP_ENV=development
ENVIRONMENT=development
DEBUG=True

# Database Configuration
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_postgres_password
POSTGRES_DB=academic_writing
# Nếu dùng Docker port 5433:
DATABASE_URL=postgresql+asyncpg://postgres:your_postgres_password@localhost:5433/academic_writing
# Nếu dùng Postgres cục bộ port 5432:
# DATABASE_URL=postgresql+asyncpg://postgres:your_postgres_password@localhost:5432/academic_writing

# OpenRouter LLM Configuration
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
DEFAULT_MODEL=deepseek/deepseek-chat
FALLBACK_MODEL=deepseek/deepseek-r1
LLM_TIMEOUT_SECONDS=30.0

# Security & JWT settings
JWT_SECRET=your_jwt_secret_key_here
JWT_SECRET_KEY=your_jwt_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Google OAuth Settings
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

# CORS Settings
BACKEND_CORS_ORIGINS=["http://localhost:3000"]
```

---

## 4. Hướng dẫn lấy `GOOGLE_CLIENT_ID` và `GOOGLE_CLIENT_SECRET`

Để kích hoạt tính năng đăng nhập Google cho cả Backend và Frontend, bạn cần tạo khóa OAuth 2.0 trên **Google Cloud Console**:

### Bước 1: Truy cập Google Cloud Console
- Truy cập vào [Google Cloud Console](https://console.cloud.google.com/).
- Đăng nhập bằng tài khoản Google của bạn.

### Bước 2: Tạo một Dự án mới (New Project)
1. Nhấp vào ô chọn dự án ở góc trên cùng bên trái (cạnh logo *Google Cloud*).
2. Chọn **New Project** (Dự án mới).
3. Nhập **Project Name** (ví dụ: `academic-writing-coach`) và nhấn **Create**.

### Bước 3: Cấu hình Màn hình đồng ý OAuth (OAuth Consent Screen)
1. Mở menu điều hướng $\rightarrow$ Chọn **APIs & Services** $\rightarrow$ **OAuth consent screen**.
2. Chọn **User Type**:
   - Chọn **External** (cho phép mọi tài khoản Google đăng nhập).
3. Nhấn **Create** và điền các thông tin:
   - **App name**: `Academic Writing Coach`
   - **User support email**: Email của bạn.
   - **Developer contact information**: Email của bạn.
4. Nhấn **Save and Continue** qua các bước tiếp theo cho đến khi hoàn tất.

### Bước 4: Tạo OAuth Client ID
1. Chuyển sang mục **Credentials** ở menu bên trái.
2. Nhấp vào **+ Create Credentials** $\rightarrow$ Chọn **OAuth client ID**.
3. Tại mục **Application type**, chọn **Web application**.
4. Đặt tên (ví dụ: `Academic Coach Web Client`).
5. **Cấu hình đường dẫn bảo mật (Rất quan trọng)**:
   - **Authorized JavaScript origins**:
     - `http://localhost:3000`
     - `http://localhost:8000`
   - **Authorized redirect URIs**:
     - `http://localhost:8000/api/v1/auth/google/callback`
     - `http://localhost:3000/api/auth/callback/google`
6. Nhấn **Create**.

### Bước 5: Sao chép khóa vào `.env`
Sao chép **Client ID** và **Client Secret** vừa tạo dán vào các biến `GOOGLE_CLIENT_ID` và `GOOGLE_CLIENT_SECRET` trong file `backend/.env`.

---

## 5. Cài đặt & Khởi chạy Backend (FastAPI)

### Bước 1: Di chuyển vào thư mục backend
```bash
cd academic-writing-coach/backend
```

### Bước 2: Tạo và kích hoạt Môi trường ảo (`venv`)
```powershell
# Tạo venv
python -m venv venv

# Kích hoạt venv trên Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Kích hoạt venv trên Windows CMD:
.\venv\Scripts\activate.bat

# Kích hoạt venv trên macOS / Linux:
source venv/bin/activate
```

### Bước 3: Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### Bước 4: Chạy database migration (nếu chưa chạy)
```bash
alembic upgrade head
```

### Bước 5: Khởi động Backend Server
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- **API Base URL**: `http://localhost:8000`
- **Tài liệu Swagger UI tương tác**: `http://localhost:8000/docs`
- **Tài liệu ReDoc**: `http://localhost:8000/redoc`

---

## 6. Cài đặt & Khởi chạy Frontend (Next.js)

### Bước 1: Mở Terminal mới và vào thư mục frontend
```bash
cd academic-writing-coach/frontend
```

### Bước 2: Cài đặt dependencies
```bash
npm install
```

### Bước 3: Cấu hình biến môi trường Frontend (Tùy chọn)
Tạo file `frontend/.env.local` nếu muốn tùy biến cổng:
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### Bước 4: Chạy Frontend ở chế độ Development
```bash
npm run dev
```

- Ứng dụng Web sẽ chạy tại: **`http://localhost:3000`**

### Bước 5: Build Production (Kiểm tra lỗi build)
```bash
npm run build
npm run start
```

---

## 7. Kiểm thử Hệ thống (Testing)

### 🔹 1. Chạy toàn bộ Test Backend (Pytest)
Đảm bảo bạn đang ở thư mục `backend` và đã kích hoạt `venv`:
```bash
pytest -v
```
*(Bao gồm kiểm thử: Xác thực Token, Vòng đời Dự án, Sinh dàn ý AI, Định dạng trích dẫn APA/IEEE/Bộ GD&ĐT)*

### 🔹 2. Chạy thử nghiệm độc lập Agent sinh Dàn ý qua dòng lệnh
```bash
python -m agents.outline_agent
```

### 🔹 3. Kiểm thử luồng E2E trên Web:
1. Mở [http://localhost:3000/auth/signin](http://localhost:3000/auth/signin).
2. Nhấn **"Đăng nhập bằng Google"** hoặc **"⚡ Đăng nhập nhanh (Chế độ Thử nghiệm)"**.
3. Tại **Dashboard**, nhấn **"+ Tạo dự án mới"** $\rightarrow$ Nhập đề tài $\rightarrow$ Nhấn **"Bắt đầu dự án"**.
<<<<<<< Updated upstream
4. Tại **Workspace**, nhấn **"✨ Sinh dàn ý AI"** để nhận dàn ý học thuật từ DeepSeek AI và chỉnh sửa trực tiếp trên cây Outline Editor.
=======
4. Tại **Workspace**, nhấn **"✨ Sinh dàn ý AI"** để nhận dàn ý học thuật từ DeepSeek AI và chỉnh sửa trực tiếp trên cây Outline Editor.

## Cập nhật Task 14 - Thúy Vi
- Thiết kế UI Stepper Bar 3 bước (Dàn ý ➔ Tài liệu ➔ Viết & Trích dẫn).
- Dựng Component `CreditBalance` trên Header và hộp thoại `PurchaseModal` (Mockup nạp tiền).
- Xây dựng UI bảng `AIUseLog` hiển thị báo cáo lịch sử sử dụng AI.

---

## 🗓️ Cập nhật Tuần 3 — Backend (Citation Agent · LangGraph · DB Indexing · Middleware · Testing)

Phần này tóm tắt các hạng mục backend của tuần 3 và cách chạy/chạy lại trên máy thành viên.
Chi tiết đầy đủ nằm ở [`backend/README.md`](backend/README.md).

### 1) API Citation Agent (mới)

| Endpoint | Mô tả |
|---|---|
| `POST /api/v1/projects/{project_id}/citation/check` | Quét bản nháp, tìm các câu/nhận định **thiếu trích dẫn**, trả kèm `sentence_index`, `char_offset`, `char_end` để FE highlight trên Tiptap. Trừ **2 credits**. |
| `POST /api/v1/projects/{project_id}/citation/format` | Format toàn bộ `selected_papers` của dự án theo style `apa7` / `ieee` / `bgddt`; trả `citations[]` (in-text + full) và `bibliography[]` + `html_formatted`. |
| `POST /api/v1/projects/{project_id}/citation/bibliography?style=apa7` | Chỉ sinh danh mục tài liệu tham khảo (không trừ credit). |
| `POST /api/v1/citation/format` | Format 1 nguồn đơn lẻ từ metadata (dùng nhanh cho FE). |

*Ví dụ kiểm tra thiếu trích dẫn:*
```bash
curl -X POST http://127.0.0.1:8000/api/v1/projects/$PROJECT_ID/citation/check \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"content":"<p>The survey reports that 85% of students use AI writing tools.</p>","citation_style":"apa7"}'
```
Response rút gọn:
```json
{
  "total_issues": 1,
  "missing_claims": [
    { "sentence": "The survey reports that 85% of students use AI writing tools.",
      "reason": "...", "suggested_action": "...",
      "sentence_index": 0, "char_offset": 3, "char_end": 62 }
  ],
  "uncited_papers": [], "verified_count": 0, "credits_charged": 2
}
```
> Lỗi `402` khi không đủ credit, `404` khi project không thuộc user đang đăng nhập.

### 2) Citation Agent & LangGraph pipeline
- `backend/agents/citation_agent.py`: `CitationAgent` (kế thừa `BaseAgent`) với core rule-based (tokenize câu an toàn với viết tắt, nhận diện APA/IEEE, phát hiện ghost citation, tìm paper chưa được trích dẫn) + lớp **LLM arbitrator** tuỳ chọn; fallback hoàn toàn offline khi LLM lỗi.
  - API công khai: `detect_missing_citations(text, papers)`, `format_citations(papers, style)`, `format_citations_detailed(...)`, `check_document_citations(...)`.
- `backend/agents/graph.py`: `StateGraph` **Outline ➔ Literature ➔ Citation**
  - Node nhận `AgentState` (TypedDict) và trả về phần state cập nhật.
  - Conditional edge dừng pipeline ngay khi một node ghi `error`.
  - Checkpoint 2 lớp: `MemorySaver` của LangGraph (`thread_id` + `resume=True`) và `PipelineCheckpointStore` in-memory (trả `checkpoints` trong kết quả).
  - Chạy offline bằng `LITERATURE_MODE=mock`.

### 3) Tối ưu DB Indexing (migration `f3a91c2d7b64`)
| Index | Bảng | Loại |
|---|---|---|
| `ix_cached_papers_fts` | `cached_papers` | **GIN** trên `to_tsvector('simple', title \|\| ' ' \|\| abstract)` (PostgreSQL) |
| `ix_projects_user_id_status` | `projects` | Composite |
| `ix_search_sessions_project_id_expires_at` | `search_sessions` | Composite |
| `ix_credit_transactions_user_id_created_at` | `credit_transactions` | Composite |

- Khai báo `Index(...)` trong `models/*` để `create_all` (test SQLite) cũng có index.
- `services/literature_service.full_text_search_papers()` dùng `to_tsvector`/`plainto_tsquery` trên PostgreSQL và fallback `ILIKE` trên các dialect khác.
- Áp dụng: `cd backend && alembic upgrade head` (xem SQL sinh ra: `alembic upgrade b6c3d2a41f7e:f3a91c2d7b64 --sql`).

### 4) Middleware CORS & Rate limiting (`backend/api/middleware.py`)
- `setup_cors(app)`: đọc `BACKEND_CORS_ORIGINS` (mặc định `http://localhost:3000`), cho phép credentials.
- `setup_rate_limiting(app)`: sliding-window in-memory, key theo **bearer token (hash)** hoặc IP; bỏ qua `OPTIONS` + các path health/docs; trả `429` kèm `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`.
- Biến môi trường mới trong `backend/.env`:
```env
RATE_LIMIT_ENABLED=True
RATE_LIMIT_REQUESTS=120
RATE_LIMIT_WINDOW_SECONDS=60
```

### 5) Kiểm thử (pytest + httpx.AsyncClient, SQLite tạm)
```bash
cd backend
pip install -r requirements.txt   # đã bổ sung aiosqlite cho test
python -m pytest tests/ -q        # kết quả hiện tại: 137 passed
```
Các file test tuần 3: `test_citation_api.py`, `test_langgraph_pipeline.py`, `test_db_indexing.py`,
`test_middleware_rate_limit.py`, `test_literature_api.py`, `test_projects_api.py`, `test_auth.py`
(fixtures dùng chung: `tests/conftest.py` — `client`, `db_session`, `test_user`, `token`, `auth_headers`, `project`).
>>>>>>> Stashed changes
