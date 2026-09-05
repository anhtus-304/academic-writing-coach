# AI Academic Writing Coach — Backend README (Task 11 · Literature Agent & Interactive Text Editor)

Hướng dẫn nhóm phát triển **Task 11**: *Tìm kiếm tài liệu thật từ 3 nguồn API
(Semantic Scholar, arXiv, OpenAlex), tóm tắt tiếng Việt, cache 48h, hệ thống credit,
và bước nền cho Tiptap Editor với BubbleMenu "Hỏi AI"*.

> Tài liệu tham chiếu: **KẾ HOẠCH THỰC THI ĐỀ TÀI 2.docx** + **Phân Công Công Việc SPNC.docx**
> (SPNC - Google Drive).

---

## 1. Mục tiêu & yêu cầu task 11

| # | Yêu cầu | Trạng thái (merged `agent-2`) |
|---|---------|-------------------------------|
| 1 | Thiết kế API endpoints tìm kiếm tài liệu & lưu cache (`search_sessions`, `cached_papers`) | 🟡 Route có nhưng **chưa được gắn vào `main.py`** |
| 2 | Logic DB Cache 48h (tiết kiệm API Rate Limits) | ✅ Có (`expires_at` + kiểm tra lại) |
| 3 | Credit Service API — `GET /credits/balance` + trừ credit khi gọi agent | 🟡 `GET /balance` có; **`deduct_credits` bị mất sau merge** |
| 4 | Tìm tài liệu **thật** từ 3 nguồn (Semantic Scholar, arXiv, OpenAlex) | ✅ Các `services/*` có code thật |
| 5 | Tóm tắt **tiếng Việt** bằng LLM | ✅ `services/llm_service.py` (OpenRouter) |
| 6 | Tiptap Editor + BubbleMenu "Hỏi AI" | 🔴 FE chưa có (xem mục 7) |

**Kết luận ngắn:** Phần **back-end core đã có code** (aggregator, 3 nguồn, LLM, cache),
nhưng **chưa được tái kết nối** sau khi merge `agent-2` (thiếu schemas mới, `deduct_credits`,
và router trong `main.py`). Xem mục **6 (Roadmap)** để hoàn thiện.

---

## 2. API endpoints

### 2.1. Tìm kiếm tài liệu
```
POST /api/v1/projects/{project_id}/literature/search
```
Auth: **JWT Bearer** — chỉ chủ sở hữu project mới được dùng (kiểm tra `project.user_id`).

Body (`LiteratureSearchRequest`):
```json
{
  "query": "deep learning",
  "filters": { "source": "arxiv", "min_year": 2023 }
}
```
- `query` (bắt buộc): chuỗi từ khóa.
- `filters` (tùy chọn): `source` (`semantic_scholar` | `arxiv` | `openalex`) hoặc `min_year`.

Response (`LiteratureSearchResponse`):
```json
{
  "search_session_id": "uuid",
  "cached": false,
  "papers": [
    { "id": "uuid", "title": "...", "authors": "...", "year": 2023,
      "source": "arxiv", "doi": "...", "url": "...", "abstract": "...",
      "summary": "...", "citation_count": 87, "relevance_score": 0.88 }
  ]
}
```
- `cached: false` = tìm mới (được trừ credit); `cached: true` = lấy từ cache (không trừ credit).

### 2.2. Credit balance
```
GET /api/v1/credits/balance
```
Response: `{ "balance": <int> }`.

---

## 3. Kiến trúc & file liên quan

```
backend/
├── api/routes/
│   ├── literature.py          # route POST .../literature/search (cần gắn vào main)
│   ├── credits.py             # GET /credits/balance
│   ├── auth.py / projects.py / health.py
├── services/
│   ├── literature_service.py  # search_literature + cache 48h + trừ credit
│   ├── search_aggregator.py   # gọi 3 nguồn song song, dedup, relevance_score
│   ├── scholar_service.py     # Semantic Scholar (+ retry khi rate-limit 429)
│   ├── arxiv_service.py       # arXiv API (Atom/feedparser)
│   ├── openalex_service.py    # OpenAlex (/works), dựng abstract từ inverted index
│   ├── llm_service.py         # tóm tắt tiếng Việt qua OpenRouter
│   └── credit_service.py      # get_credit_balance (+ nên có thêm deduct_credits)
├── schemas/literature_schemas.py  # (cần cập nhật lại 3 schema mới)
├── models/                    # User, Project, SearchSession, CachedPaper, CreditTransaction...
└── alembic/versions/          # migration (cần cột expires_at, search_session_id, summary, relevance_score)
```
---

## 4. Cài đặt & chạy

### 4.1. Yêu cầu
- Python 3.14
- PostgreSQL (đang chạy trên cổng 5432)
- Biến môi trường trong `backend/.env` (xem `backend/.env.example`):
  - `DATABASE_URL`, `JWT_SECRET`, `GOOGLE_*`
  - LLM: `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `DEFAULT_MODEL`
  - 3 nguồn: `SEMANTIC_SCHOLAR_SEARCH_URL`, `ARXIV_API_URL`, `OPENALEX_WORKS_URL`
  - CORS: `BACKEND_CORS_ORIGINS`

### 4.2. Cài deps & migration
```bash
cd backend
pip install -r requirements.txt
alembic upgrade head            # cần DB chạy
```

### 4.3. Chạy server
```bash
cd backend
uvicorn main:app --reload
```
Swagger: http://127.0.0.1:8000/docs

---

## 5. Test

### 5.1. Test tự động (offline, không cần PostgreSQL)
Chạy trên SQLite tạm; `LITERATURE_MODE=mock` để deterministic (qua `tests/conftest.py`):
```bash
cd backend
pip install aiosqlite greenlet pytest pytest-asyncio
python -m pytest tests/ -q
```
Các file test hiện có:
- `tests/test_search_sources.py` — unit test aggregator (dedup, scoring, filter).
- `tests/test_literature_credits_e2e.py` — e2e: health, balance, search + cache + trừ credit, 401/402/404.
- `tests/test_search_aggregator.py`, `tests/test_auth_and_projects.py` — test từ agent-2.

> ⚠️ Sau khi merge, nếu import bị lỗi (thiếu schema/deduct_credits) thì test literature
> sẽ không chạy được cho tới khi hoàn tất mục **6**.

### 5.2. Test tay bằng curl
```bash
export TOKEN="<jwt>"
curl -X GET  http://127.0.0.1:8000/api/v1/credits/balance -H "Authorization: Bearer $TOKEN"
curl -X POST http://127.0.0.1:8000/api/v1/projects/{PROJECT_ID}/literature/search \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"query":"academic writing","filters":{"min_year":2022}}'
```
Gọi lại lần hai cùng query → nhận `"cached": true`, không trừ thêm credit.

---

## 6. Roadmap — việc cần làm để hoàn thiện task 11

> Trạng thái sau khi merge `agent-2` ("Merge agent-2 code, drop local changes"):
> một số file bị reset về bản của `agent-2`, làm mất phần **tái kết nối** literature.
> Cần tái áp dụng các điểm sau:

1. **`schemas/literature_schemas.py`** — khôi phục 3 schema: `LiteratureSearchRequest`,
   `PaperResponse`, `LiteratureSearchResponse` (bản `agent-2` chỉ còn schema cũ).
2. **`services/credit_service.py`** — khôi phục `deduct_credits(db, user, amount, description)`
   (check số dư → trừ `credit_balance` → ghi `CreditTransaction` type=`usage`, amount âm → `True/False`).
   `literature_service.py` đang import hàm này.
3. **`api/routes/literature.py`** — sau khi có schema, import `LiteratureSearchRequest/Response`
   sẽ hoạt động trở lại.
4. **`main.py`** — đăng ký router literature:
   ```python
   from api.routes import auth, projects, credits, health, literature
   app.include_router(literature.router, prefix=settings.API_V1_STR)
   ```
5. **Migration** — đảm bảo DB có cột `search_sessions.expires_at`,
   `cached_papers.search_session_id/summary/relevance_score` (tạo/re-apply migration phù hợp).
6. **Chạy lại test** — `python -m pytest tests/ -q` tới khi xanh.
7. **FE (Task 15/editor)** — Tiptap Editor + BubbleMenu "Hỏi AI": tiêu thụ API này.
   `frontend/src/components/editor/` (TiptapEditor, AIBubbleMenu, AIResponsePanel) đang cần phát triển.

---

## 7. Ghi chú triển khai

- **Semantic Scholar** công khai hay **rate-limit 429** → service đã retry ngắn trước khi bỏ cuộc.
- **arXiv** phải dùng `https://export.arxiv.org` (HTTP bị redirect 301).
- **OpenAlex** lưu abstract dạng **inverted index** → cần dựng lại chuỗi abstract.
- **LLM tóm tắt**: nếu chưa có key, `summary` để trống, không làm hỏng tìm kiếm.
- **Credit**: nếu hết credit khi tìm kiếm mới → trả `402 Payment Required`.
