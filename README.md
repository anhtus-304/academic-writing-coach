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

## 7. Literature Agent & Interactive Text Editor

### Mục tiêu
- Tìm kiếm tài liệu học thuật thật từ các nguồn bên ngoài.
- Tóm tắt tài liệu bằng tiếng Việt để hỗ trợ người dùng đọc nhanh và chọn tài liệu phù hợp.
- Tích hợp trình soạn thảo văn bản với menu hành động nhanh và luồng hỏi AI khi người dùng bôi đen text.

### Các chức năng đã implement
- Tìm kiếm tài liệu từ 3 nguồn chính: **Semantic Scholar**, **OpenAlex**, và **arXiv**.
- Chuẩn hóa dữ liệu trả về về cùng một model paper để UI hiển thị thống nhất.
- Tóm tắt nội dung tài liệu bằng tiếng Việt bằng OpenRouter / LLM.
- Hiển thị danh sách tài liệu trong giao diện `LiteratureList`, `PaperCard`, và `SearchFilters`.
- Chọn paper từ danh sách và chèn reference vào editor.
- Bôi đen text trong Tiptap editor và click **Hỏi AI** để mở AIResponsePanel / side drawer.
- Cung cấp `BubbleMenu` và `AIBubbleMenu` trong editor để thực hiện thao tác nhanh khi chọn văn bản.

### 3 nguồn literature API
Service backend hiện có thực hiện truy vấn trực tiếp đến các nguồn sau:

1. **Semantic Scholar**  
   - Endpoint: `https://api.semanticscholar.org/graph/v1/paper/search`
   - Dữ liệu được normalize thành các trường: `id`, `title`, `authors`, `abstract`, `year`, `source`, `publicationType`, `doi`, `url`, `citationCount`.

2. **OpenAlex**  
   - Endpoint: `https://api.openalex.org/works`
   - Dữ liệu tương tự được chuẩn hóa trong `normalize_paper_record`.

3. **arXiv**  
   - Endpoint: `https://export.arxiv.org/api/query`
   - Dữ liệu từ XML Atom được parse và chuẩn hóa theo cùng một cấu trúc.

> Tất cả 3 nguồn được gom lại trong `search_literature` trong backend, rồi được dedupe trước khi trả về frontend.

### Backend API endpoints
#### 1) GET `/api/v1/literature/search`
Tìm kiếm tài liệu theo query text.

Query parameters:
- `query` (required): từ khóa tìm kiếm
- `source` (optional): `semantic_scholar`, `openalex`, hoặc `arxiv`
- `year` (optional): `2020s` hoặc `2010s`
- `publication_type` (optional): lọc theo loại xuất bản nếu backend trả về giá trị tương ứng
- `limit` (optional): số lượng item tối đa, mặc định `10`, giới hạn `1..20`

Ví dụ:
```http
GET /api/v1/literature/search?query=blockchain%20agriculture&limit=5
GET /api/v1/literature/search?query=transformer%20nlp&source=openalex&year=2020s
```

Response mẫu:
```json
{
  "query": "blockchain agriculture",
  "total_results": 5,
  "papers": [
    {
      "id": "...",
      "title": "...",
      "authors": ["..."],
      "abstract": "...",
      "year": 2023,
      "source": "semantic_scholar",
      "publicationType": "Journal article",
      "doi": "...",
      "url": "https://...",
      "citationCount": 42,
      "raw": {}
    }
  ]
}
```

#### 2) POST `/api/v1/literature/summarize`
Tạo bản tóm tắt tiếng Việt cho paper đã chọn.

Request body:
```json
{
  "paper": {
    "id": "abc123",
    "title": "A Survey on ...",
    "authors": ["Author A", "Author B"],
    "abstract": "...",
    "source": "semantic_scholar"
  }
}
```

Response mẫu:
```json
{
  "paper_id": "abc123",
  "summary_vi": "Tài liệu này tập trung vào ..."
}
```

> Nếu `OPENROUTER_API_KEY` chưa được cấu hình trong `backend/.env`, backend sẽ trả về lỗi rõ ràng thay vì crash vô điều kiện.

### Frontend components
Các component hiện có trong frontend và đang được tích hợp với backend API:
- `LiteratureList`: hiển thị danh sách paper và trạng thái loading/error/empty.
- `PaperCard`: hiển thị thông tin tài liệu và cho phép người dùng chọn một paper.
- `SearchFilters`: nhập query và lọc theo năm, loại xuất bản, nguồn dữ liệu.
- `TiptapEditor`: soạn thảo nội dung bằng Tiptap.
- `AIBubbleMenu`: nút "Hỏi AI" xuất hiện khi có text được bôi đen.
- `AIResponsePanel`: panel/side drawer hiển thị phản hồi AI dựa trên selected text.

### Editor / AI interaction flow
Luồng hiện có trong workspace editor:
1. Người dùng nhập query và gọi search literature.
2. Chọn một paper từ `LiteratureList`.
3. Gọi endpoint summarize để lấy `summary_vi`.
4. Chọn action **chèn reference** vào bài viết.
5. Khi bôi đen một đoạn text trong editor và click **Hỏi AI**, `onAskAI` sẽ truyền selected text tới `AIResponsePanel`.
6. Panel AI mở ở cột phải để hiển thị mô tả/đáp án liên quan đến đoạn được chọn.

### Cấu hình cần thiết
Nếu muốn sử dụng tính năng tóm tắt tiếng Việt trong backend, cần có biến môi trường sau trong `backend/.env`:
```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
DEFAULT_MODEL=deepseek/deepseek-chat
```

### Giới hạn hiện tại
- Tính năng summarize phụ thuộc vào cấu hình `OPENROUTER_API_KEY` hợp lệ.
- Mức độ lọc ở query/search hiện đang phản ánh các trường thực tế trả về từ các nguồn API, không phải một schema giả định riêng.
- Cấu trúc UI/editor hiện có đã được tích hợp và kiểm tra build/type-check; tuy nhiên, README chỉ mô tả những phần có thể xác nhận từ code hiện tại.

---

## 8. Kiểm thử Hệ thống (Testing)

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
4. Tại **Workspace**, nhấn **"✨ Sinh dàn ý AI"** để nhận dàn ý học thuật từ DeepSeek AI và chỉnh sửa trực tiếp trên cây Outline Editor.

## Cập nhật Task 14 - Thúy Vi
- Thiết kế UI Stepper Bar 3 bước (Dàn ý ➔ Tài liệu ➔ Viết & Trích dẫn).
- Dựng Component `CreditBalance` trên Header và hộp thoại `PurchaseModal` (Mockup nạp tiền).
- Xây dựng UI bảng `AIUseLog` hiển thị báo cáo lịch sử sử dụng AI.