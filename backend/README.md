# AI Academic Writing Coach — Backend (Task Week 2)

Backend FastAPI cho hệ thống Multi-Agent hỗ trợ sinh viên viết luận văn/khóa luận.

## Mô tả tính năng tuần 2

### Tìm kiếm tài liệu (Literature Search)

Endpoint:

```
POST /api/v1/projects/{project_id}/literature/search
```

Xác thực: **JWT Bearer** (giống các endpoint khác). Chỉ chủ sở hữu project mới được phép tìm kiếm.

**Body** (`LiteratureSearchRequest`):

```json
{
  "query": "deep learning",
  "filters": { "source": "arxiv", "min_year": 2023 }
}
```

- `query`: chuỗi từ khóa tìm kiếm (bắt buộc).
- `filters`: bộ lọc tùy chọn. Hiện hỗ trợ `source` (`semantic_scholar` | `arxiv` | `openalex`) và `min_year`.

**Response** (`LiteratureSearchResponse`):

```json
{
  "search_session_id": "uuid",
  "cached": false,
  "papers": [
    {
      "id": "uuid",
      "title": "...",
      "authors": "...",
      "year": 2023,
      "source": "arxiv",
      "doi": "...",
      "url": "...",
      "abstract": "...",
      "summary": "...",
      "citation_count": 87,
      "relevance_score": 0.88
    }
  ]
}
```

### Caching

- Mỗi tìm kiếm tạo một `SearchSession` với `expires_at = now + 48h`.
- Khi gọi lại với cùng `project_id` + `query` trong khi session còn hiệu lực
  (`expires_at > now`), hệ thống trả kết quả từ `CachedPaper` với `cached = true`
  và **không trừ credit**.
- Hết hạn hoặc query mới → tìm kiếm mới, tạo session & `CachedPaper` mới (`cached = false`).

### Hệ thống credit

- Endpoint: `GET /api/v1/credits/balance` → trả `{"balance": <int>}` của user đang đăng nhập.
- Mỗi lần tìm kiếm **không cache** tốn **1 credit**.
- Trước khi tìm, gọi `deduct_credits(db, user, amount, description)` từ
  `services/credit_service.py`. Nếu số dư không đủ trả `false` → API trả
  `402 Payment Required`.
- Giao dịch sử dụng credit được lưu vào `credit_transactions` với
  `transaction_type = "usage"` và `amount` âm.

### Nguồn dữ liệu

- Mặc định chạy **live** với 3 API: **Semantic Scholar**, **arXiv**, **OpenAlex**
  (xem `services/{scholar_service,arxiv_service,openalex_service}.py`).
- `services/search_aggregator.py` gọi cả 3 song song, loại trùng theo DOI/title
  (giữ bản có số trích dẫn cao hơn) và tính điểm `relevance_score` dựa trên độ
  khớp từ khóa với tiêu đề + abstract.
- **Tóm tắt tiếng Việt**: `services/llm_service.py` gọi OpenRouter
  (`OPENROUTER_API_KEY`) để sinh summary. Nếu chưa cấu hình key, `summary` để trống.
- Kiểm soát nguồn dữ liệu qua biến `LITERATURE_MODE` trong `.env`:
  - `mock` → chỉ dùng `MOCK_PAPERS` (dùng cho test offline, deterministic).
  - `real` → chỉ kết quả API thật (có thể rỗng nếu nguồn lỗi).
  - `auto` (mặc định) → thử API thật, fallback về mock khi không có kết quả.

## Hướng dẫn test API

### 1. Chạy migration

```bash
cd backend
alembic upgrade head
```

Migration tuần 2 `b6c3d2a41f7e_add_literature_search_columns` thêm các cột
`search_sessions.expires_at`, `cached_papers.search_session_id`,
`cached_papers.summary`, `cached_papers.relevance_score`.

### 1b. Chạy test tự động (không cần PostgreSQL)

Integration test chạy trên SQLite tạm, xác minh health, balance, search + cache + trừ credit:

```bash
cd backend
pip install aiosqlite greenlet   # deps cho test local
python -m pytest tests/test_literature_credits_e2e.py -q
# => 7 passed
```

### 2. Chạy server

```bash
cd backend
uvicorn main:app --reload
```

Swagger docs: http://127.0.0.1:8000/docs

### 3. Ví dụ curl

Lấy token (thay bằng flow Google OAuth thực tế của bạn):

```bash
export TOKEN="<your-jwt-token>"
```

Tìm kiếm tài liệu:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/projects/{PROJECT_ID}/literature/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"academic writing","filters":{"min_year":2022}}'
```

Gọi lại lần hai với cùng query → nhận `"cached": true` và không trừ thêm credit.

## Cấu trúc file liên quan

- `services/literature_service.py` — `search_literature`, cache, `cached_paper_to_dict`.
- `services/credit_service.py` — `get_credit_balance`, `deduct_credits`.
- `services/project_service.py` — `get_project` (kiểm tra quyền sở hữu).
- `schemas/literature_schemas.py` — `LiteratureSearchRequest`, `PaperResponse`, `LiteratureSearchResponse`.
- `api/routes/literature.py` — endpoint `POST /projects/{project_id}/literature/search`.
- `api/dependencies.py` — `get_current_user` (JWT).
- `security.py` — tạo/xác thực JWT.
- `api/routes/literature.py` — có thể gọi `search_aggregator` khi tích hợp nguồn thật.