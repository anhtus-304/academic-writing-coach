# AI Academic Writing Coach — Backend (cập nhật **Tuần 3**)

Hướng dẫn backend cho task tuần 3: **Citation Agent · LangGraph pipeline · DB Indexing ·
Middleware (CORS + Rate limiting) · Unit/Integration testing**.

> Tài liệu liên quan: `README.md` ở gốc repo (setup PostgreSQL/Docker + Google OAuth),
> `KẾ HOẠCH THỰC THI ĐỀ TÀI` (Google Drive SPNC).

---

## 1. Thành phần & trạng thái

| # | Hạng mục tuần 3 | File chính | Trạng thái |
|---|---|---|---|
| 1 | API Citation Agent (`check`, `format`, `bibliography`) | `api/routes/citation.py` | ✅ |
| 2 | `CitationAgent` (rule-based core + LLM arbitrator, có fallback offline) | `agents/citation_agent.py` | ✅ |
| 3 | LangGraph `Outline ➔ Literature ➔ Citation` + checkpoint | `agents/graph.py` | ✅ |
| 4 | DB Indexing: GIN full-text + 3 composite index | `alembic/versions/f3a91c2d7b64_*.py`, `models/*` | ✅ |
| 5 | Middleware CORS + Rate limiting | `api/middleware.py`, `main.py` | ✅ |
| 6 | Unit/Integration tests + `conftest.py` | `tests/test_*` | ✅ (145 passed) |

Tech stack: Python 3.11+ (đã kiểm thử trên 3.14), FastAPI (async), SQLAlchemy 2.0 async +
asyncpg, Alembic, Pydantic v2 / pydantic-settings, LangGraph 0.4, OpenRouter LLM, JWT (python-jose).

---

## 2. Cấu trúc thư mục (phần liên quan)

```
backend/
├── api/
│   ├── middleware.py          # setup_cors() + setup_rate_limiting() (sliding window in-memory)
│   ├── dependencies.py        # get_current_user (Bearer header hoặc cookie access_token)
│   └── routes/                # auth, projects, credits, literature, agents, citation, health
├── agents/
│   ├── base_agent.py          # interface chung
│   ├── outline_agent.py       # sinh dàn ý (LLM + fallback template)
│   ├── literature_agent.py    # query expansion + tóm tắt tiếng Việt
│   ├── citation_agent.py      # CitationAgent: detect_missing_citations / format_citations
│   └── graph.py               # LangGraph StateGraph 3 node + checkpoint store
├── services/
│   ├── citation_formatter.py  # rule-based formatter (APA7 / IEEE / BGDĐT)
│   ├── literature_service.py  # search + cache 48h + full_text_search_papers()
│   ├── credit_service.py      # deduct_credits / get_credit_balance
│   └── llm_service.py         # OpenRouter (structured output + text)
├── data/citation_styles/      # apa7.py, ieee.py, bgddt.py
├── models/                    # User, Project, Outline, SearchSession, CachedPaper,
│                              # SelectedPaper, DraftDocument, CreditTransaction, AIUsageLog
├── schemas/citation_schemas.py# request/response của Citation API
├── alembic/versions/          # d40... (initial) ➔ 146032681bd8 ➔ b6c3d2a41f7e ➔ f3a91c2d7b64 (head)
└── tests/                     # pytest + httpx.AsyncClient + SQLite tạm
```

---

## 3. Cài đặt & chạy

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate   |  macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # rồi điền giá trị thật
alembic upgrade head        # tạo bảng + index (cần PostgreSQL đang chạy)
uvicorn main:app --reload   # http://127.0.0.1:8000/docs
```

### Biến môi trường mới của tuần 3 (`backend/.env`)

```env
# CORS: danh sách origin của frontend (JSON array)
BACKEND_CORS_ORIGINS=["http://localhost:3000"]
# Cho phép thêm domain deploy Vercel (*.vercel.app, cả production + preview)
BACKEND_CORS_ORIGIN_REGEX=https://([a-z0-9-]+\.)*vercel\.app

# Rate limiting (sliding window in-memory, key theo bearer token hoặc IP)
RATE_LIMIT_ENABLED=True
RATE_LIMIT_REQUESTS=60           # tối đa 60 request / cửa sổ (tuần 3) -> vượt trả 429
RATE_LIMIT_WINDOW_SECONDS=60     # độ dài cửa sổ (giây)
```

`LITERATURE_MODE=mock` giúp chạy test offline (không gọi API ngoài); `real`/`auto` dùng API thật.

---

## 4. Database & Migration

### Chuỗi revision (đã nối liền, head = tuần 3)

```
d2413c130acf (initial schema) ➔ 146032681bd8 (literature + draft tables)
➔ b6c3d2a41f7e (literature search columns) ➔ f3a91c2d7b64 (week-3 indexes)  ← head
```

Kiểm tra nhanh:
```bash
alembic heads          # f3a91c2d7b64
alembic history
alembic upgrade head                                  # áp dụng thật
alembic upgrade b6c3d2a41f7e:f3a91c2d7b64 --sql       # xem SQL sẽ chạy (offline)
```

### Index được thêm ở tuần 3

| Index | Bảng | Loại | Phục vụ truy vấn |
|---|---|---|---|
| `ix_cached_papers_fts` | `cached_papers` | **GIN** `to_tsvector('simple', title \|\| ' ' \|\| abstract)` | full-text search trên cache tài liệu |
| `ix_projects_user_id_status` | `projects` | composite | dashboard: `WHERE user_id=? [AND status=?]` |
| `ix_search_sessions_project_id_expires_at` | `search_sessions` | composite | cache 48h: `project_id + expires_at > now()` |
| `ix_credit_transactions_user_id_created_at` | `credit_transactions` | composite | lịch sử credit (mới nhất trước) |

Ghi chú kỹ thuật:
- Dùng cấu hình `simple` (không stemming) vì corpus trộn tiếng Việt + tiếng Anh.
- GIN index chỉ tạo trên PostgreSQL (`dialect == "postgresql"`); migration dùng `IF NOT EXISTS`
  nên chạy lại an toàn (kể cả khi bảng đã có index do `Base.metadata.create_all`).
- `services/literature_service.full_text_search_papers(db, query, limit)` tự chọn
  `to_tsvector`/`plainto_tsquery` (PostgreSQL) hoặc fallback `ILIKE` (SQLite khi test).
- Kiểm tra index sau khi migrate:
  ```sql
  SELECT indexname, indexdef FROM pg_indexes
  WHERE tablename IN ('cached_papers','projects','search_sessions','credit_transactions');
  ```
  Và đo thời gian truy vấn: `EXPLAIN (ANALYZE, BUFFERS) SELECT ... WHERE project_id=$1 AND expires_at > now();`
  (mục tiêu < 50ms với dữ liệu lớn — test `tests/test_db_indexing.py` có smoke-check).
---

## 5. API endpoints

Tất cả endpoint (trừ `/health`, `/auth/google/*`, `/auth/dev-login`) cần header
`Authorization: Bearer <jwt>` **hoặc** cookie `access_token` (do `/auth/dev-login` set).
Mọi endpoint theo `project_id` đều kiểm tra quyền sở hữu → `404` nếu project không thuộc user.

| Nhóm | Endpoint | Ghi chú |
|---|---|---|
| Auth | `GET /auth/google/login`, `GET /auth/google/callback`, `POST /auth/dev-login`, `POST /auth/logout`, `GET /auth/me` | dev-login tạo/đăng nhập nhanh, tặng 120 credits, set cookie HttpOnly |
| Projects | `POST /projects/`, `GET /projects/`, `GET/PUT/DELETE /projects/{id}` | CRUD + phân trang |
| Outline | `POST /projects/{id}/outline/generate`, `GET/PUT /projects/{id}/outline` | trừ credit khi generate |
| Document | `GET/PUT /projects/{id}/document`, `POST /projects/{id}/export/docx`, `POST /projects/{id}/export/markdown`, `POST /projects/{id}/import/*` | lưu draft + import/export |
| Credits | `GET /credits/balance`, `GET /credits/logs`, `GET /credits/transactions` | |
| Literature | `POST /projects/{id}/literature/search`, `POST /projects/{id}/literature/select`, `GET .../selected`, `DELETE .../selected/{id}`, `GET .../recent-search`, `GET /literature/search`, `POST /literature/summarize` | search mới trừ 1 credit, cache 48h không trừ |
| Agents | `POST /agents/ask` | trợ lý AI theo đoạn bôi đen (trừ 1 credit) |
| **Citation** | `POST /projects/{id}/citation/check`, `POST /projects/{id}/citation/format`, `POST /projects/{id}/citation/bibliography`, `POST /citation/format` | xem mục 6 |
| Health | `GET /health` | public, được miễn rate limit |

---

## 6. Citation API (tuần 3)

Hai endpoint chính: **check** (tìm câu thiếu trích dẫn) và **format** (sinh in-text + danh mục
tài liệu tham khảo). Ngoài ra có 2 endpoint phụ ở mục 6.3.

### 6.1 `POST /api/v1/projects/{project_id}/citation/check` — trừ **2 credits**

Phát hiện câu/nhận định cần nguồn nhưng **thiếu trích dẫn** bằng **regex + rule-based**
(whitelist câu thuộc về chính tác giả như "chúng tôi", "in this study"; LLM arbitrator là
tuỳ chọn và luôn có fallback deterministic khi LLM lỗi/timeout).

Request:
```json
{
  "content": "<p>The survey reports that 85% of students use AI writing tools.</p>",
  "citation_style": "apa7",
  "paper_ids": ["<SelectedPaper.id>"]
}
```
- `content`: plain text hoặc HTML (bắt buộc, tối thiểu 10 ký tự).
- `citation_style`: `apa7` | `ieee` | `bgddt` (bỏ trống → dùng `project.citation_style`).
- `paper_ids`: tuỳ chọn — giới hạn danh mục tài liệu đối chiếu; bỏ trống = toàn bộ tài liệu đã chọn của project.

Response (rút gọn):
```json
{
  "total_missing": 1,
  "missing": [
    {
      "text": "The survey reports that 85% of students use AI writing tools.",
      "index": 0,
      "suggestion": "Bổ sung nguồn trích dẫn cho nhận định này."
    }
  ],
  "total_issues": 1,
  "missing_claims": [
    {
      "sentence": "The survey reports that 85% of students use AI writing tools.",
      "reason": "Chứa dữ liệu số liệu định lượng ...",
      "suggested_action": "Bổ sung trích dẫn tài liệu tham khảo ...",
      "recommended_paper_id": null,
      "recommended_paper_title": null,
      "in_text_suggestion": null,
      "sentence_index": 0,
      "char_offset": 3,
      "char_end": 66
    }
  ],
  "invalid_citations": [],
  "citation_warnings": [],
  "uncited_papers": [],
  "verified_count": 0,
  "credits_charged": 2
}
```
- `missing[]`: contract rút gọn `{text, index, suggestion}` (`total_missing` = số câu thiếu nguồn).
- `missing_claims[]`: bản đầy đủ cho Tiptap — kèm `reason`, `suggested_action`,
  `recommended_paper_*` và **offset highlight** `sentence_index` / `char_offset` / `char_end`.
- `invalid_citations[]`: ghost citation (ví dụ `[7]` nhưng danh mục chỉ có 2 tài liệu).
- `uncited_papers[]`: tài liệu đã chọn nhưng chưa được trích dẫn (kèm `in_text_code` gợi ý).
- Lỗi: `402` khi không đủ credit, `401` khi chưa đăng nhập, `404` khi sai project (không sở hữu).

### 6.2 `POST /api/v1/projects/{project_id}/citation/format` (không trừ credit)

Request (tất cả optional):
```json
{ "paper_ids": ["<SelectedPaper.id>"], "style": "ieee", "include_in_text": true }
```
- `paper_ids` (alias cũ: `selected_paper_ids`): chỉ format một tập con; bỏ trống = toàn bộ tài liệu đã chọn.
- `style`: `apa7` | `ieee` | `bgddt`; bỏ trống → `project.citation_style`.
- `include_in_text=false`: bỏ trường `in_text_citation` trong từng entry.

Response:
```json
{
  "project_id": "3f1c...",
  "style": "ieee",
  "total_citations": 1,
  "citations": [
    {
      "selected_paper_id": "9a2b...",
      "paper_id": "c7d4...",
      "title": "Deep Learning for Academic Writing",
      "authors": ["Nguyen Van An"],
      "year": 2023,
      "in_text_citation": "[1]",
      "full_citation": "[1] N. V. An, \"Deep Learning for Academic Writing,\" 2023.",
      "style": "ieee"
    }
  ],
  "bibliography": ["[1] N. V. An, \"Deep Learning for Academic Writing,\" 2023."],
  "bibliography_text": "[1] N. V. An, \"Deep Learning for Academic Writing,\" 2023.",
  "html_formatted": "<ol class='bibliography-list'><li>...</li></ol>"
}
```
- `bibliography[]`: đã sắp xếp theo luật từng style (APA7 A→Z theo họ tác giả, IEEE/BGDĐT theo số thứ tự).
- `bibliography_text`: bản nối các entry bằng `\n` (tiện chèn/copy vào bản thảo).
- `html_formatted`: `<ol>` cho IEEE/BGDĐT, `<div>` cho APA7.

### 6.3 Các endpoint phụ
- `POST /projects/{id}/citation/bibliography?style=apa7` → chỉ trả `bibliography`, `bibliography_text`, `html_formatted`.
- `POST /api/v1/citation/format` → format 1 nguồn từ metadata (`title`, `authors`, `year`, ...),
  dùng cho preview nhanh ở FE.


---

## 7. Citation Agent & LangGraph pipeline

### 7.1 `CitationAgent` (`agents/citation_agent.py`)
- **Deterministic core** (không tốn token): tách câu an toàn với viết tắt (`et al.`, `TS.`, `pp.`…),
  regex nhận diện in-text APA (`(Nguyen, 2023)`, `Smith (2024)`) và IEEE (`[1, 2]`, `[1-3]`),
  phát hiện ghost citation, kiểm tra năm xuất bản, liệt kê paper chưa trích dẫn,
  heuristic lọc câu cần dẫn chứng (số liệu `%`, "theo nghiên cứu", "studies show"…)
  và whitelist câu thuộc về chính tác giả ("chúng tôi", "in this study"…).
- **LLM arbitrator** (tuỳ chọn): lọc câu không cần trích dẫn + gợi ý paper phù hợp nhất;
  nếu LLM lỗi/timeout → tự động fallback về kết quả deterministic (test chạy offline được).
- Public API: `detect_missing(text, papers)` → `[{text, index, suggestion}]` (kèm `reason` và
  offset highlight), `detect_missing_citations(text, papers)`, `format_citations(papers, style)`,
  `format_citations_detailed(papers, style)`, `check_document_citations(content, selected_papers, citation_style)`.

### 7.2 LangGraph (`agents/graph.py`)
```
generate_outline ──(ok)──► search_literature ──(ok)──► check_citations ──► END
        │                        │                          │
        └───(error)──► END       └───(error)──► END          └── ghi citation_check, citations, bibliography
```
- `AgentState` (TypedDict) mang input (`topic`, `document_type`, `draft_content`, `citation_style`,
  `selected_papers`, `skip_literature`…) và output (`outline`, `literature_review`, `citation_check`,
  `citations`, `bibliography`, `steps_completed`, `status`, `error`).
- Mỗi node trả về **partial state**; `_route_unless_failed()` dừng pipeline ngay khi có `error`.
- Checkpoint: `PipelineCheckpointStore` (in-memory, trả `checkpoints[]` trong kết quả) và
  `MemorySaver` của LangGraph (chạy lại với `resume=True` + `thread_id`).
- **Fallback khi chưa cài `langgraph`**: `build_academic_writing_graph()` tự trả về `DictGraphMock`
  (dict mock) — chạy 3 node tuần tự trên state `dict`, dừng ngay khi có `error`, hỗ trợ
  `get_graph()`, `ainvoke()`, `aget_state()`, `aget_state_history()`; nhờ cùng contract nên
  `run_academic_pipeline()` và test không cần đổi.
- Chạy độc lập (offline, `LITERATURE_MODE=mock`):
```python
import asyncio
from agents.graph import run_academic_pipeline

state = asyncio.run(run_academic_pipeline(
    {"topic": "AI trong viết học thuật", "draft_content": "<p>...</p>", "citation_style": "apa7"},
    run_id="demo-run",
))
print(state["status"], state["steps_completed"], len(state["bibliography"]))
```
---

## 8. Middleware: CORS & Rate limiting (`api/middleware.py`)

`main.py` gọi:
```python
setup_rate_limiting(app)   # thêm trước → là lớp trong
setup_cors(app)            # thêm sau  → là lớp ngoài cùng (429 vẫn có CORS header)
```
- **CORS**: `allow_origins` = `BACKEND_CORS_ORIGINS` (mặc định `http://localhost:3000`,
  `http://127.0.0.1:3000`) + `allow_origin_regex` = `BACKEND_CORS_ORIGIN_REGEX` (mặc định
  `https://([a-z0-9-]+\.)*vercel\.app` → chấp nhận mọi domain Vercel production/preview),
  `allow_credentials=True`, expose `X-RateLimit-*` + `Retry-After`.
- **Rate limiting** (`RateLimitMiddleware`): sliding window in-memory, **mặc định 60 request / 60 giây**
  (`RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS`), key =
  `token:<sha256(bearer)>` nếu có header `Authorization`, ngược lại `ip:<x-forwarded-for đầu tiên | client host>`.
  Bỏ qua `OPTIONS` (preflight), `/api/v1/health`, `/docs`, `/redoc`, `/openapi.json`.
  Vượt hạn mức → `429` với body `{detail, limit, window_seconds, retry_after}` + header
  `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`.
- Dev không cần Redis; khi triển khai production có thể thay `RateLimitMiddleware` bằng backend
  Redis/`slowapi` mà không phải sửa route.

---

## 9. Testing

### 9.1 Chạy test (offline, không cần PostgreSQL)
```bash
cd backend
pip install -r requirements.txt        # đã gồm aiosqlite cho DB test
python -m pytest tests/ -q             # toàn bộ suite
python -m pytest tests/test_citation_api.py -q
python -m pytest -k "citation or langgraph or indexing or rate_limit" -q
```
Kết quả hiện tại (SQLite tạm `_test_week3.db` được tạo mới mỗi session, `LITERATURE_MODE=mock`, LLM bị stub):
**145 passed** — chạy lại nhiều lần cho kết quả như nhau.

### 9.2 Fixtures dùng chung (`tests/conftest.py`)
| Fixture | Ý nghĩa |
|---|---|
| `client` | `httpx.AsyncClient` + `ASGITransport` gọi thẳng app FastAPI (không cần socket) |
| `db_session` | `AsyncSession` để seed/kiểm tra DB trực tiếp |
| `test_user` | user đã lưu DB (mặc định 20 credits) |
| `token` / `auth_headers` | JWT + header `Authorization: Bearer ...` |
| `project` | project thuộc `test_user` |

Helper: `create_user_with_project()`, `create_cached_paper()`, `ensure_schema()`, `unique_email()`.

### 9.3 Test của tuần 3
| File | Nội dung |
|---|---|
| `test_citation_api.py` | `/citation/check` (offset highlight, ghost citation, uncited papers, trừ 2 credit, 402/401/404, contract rút gọn `missing`/`total_missing`, lọc `paper_ids`), `/citation/format` (APA7/IEEE/BGDĐT, subset, alias `paper_ids`, `bibliography_text`, fallback style project), `/citation/format` standalone, contract `detect_missing`/`detect_missing_citations`/`format_citations` |
| `test_langgraph_pipeline.py` | 3 node, thứ tự `steps_completed`, dừng khi lỗi, `skip_literature`, checkpoint in-memory + `MemorySaver`, resume, **dict mock fallback** (`build_dict_graph`) |
| `test_db_indexing.py` | Index khai báo trên model, migration GIN + revision chain, index tồn tại trong DB, smoke hiệu năng, credit history index |
| `test_middleware_rate_limit.py` | 429 sau hạn mức, exempt path/preflight, key theo token, CORS header trên 429, tắt limiter, **mặc định 60 req/phút**, **CORS cho `*.vercel.app`** |
| `test_literature_api.py` | search + trừ 1 credit, cache 48h (không trừ thêm), cache hết hạn, filter source, 402/401/404, select/list/delete, recent-search, `full_text_search_papers` |
| `test_projects_api.py`, `test_auth.py` | CRUD project, phân trang, quyền sở hữu; dev-login/JWT/cookie/logout |

### 9.4 Test tay nhanh
```bash
# 1. Lấy token
curl -X POST http://127.0.0.1:8000/api/v1/auth/dev-login \
  -H "Content-Type: application/json" -d '{"email":"demo@student.edu.vn","name":"Demo"}'
# 2. Tạo project rồi gọi citation/check, citation/format như mục 6
```
Kiểm tra rate limit: gọi liên tục > `RATE_LIMIT_REQUESTS` request trong 60s → nhận `429`.

---

## 10. Ghi chú triển khai & việc tiếp theo

- **Dual import alias**: backend có thể được import theo 2 kiểu (`agents.x` khi chạy
  `uvicorn main:app` trong `backend/`, hoặc `backend.agents.x` khi chạy từ gốc repo). Các model
  và `database.py` đã tự đồng bộ `sys.modules`; route/service ưu tiên alias `backend.*`, và
  pipeline (`agents/graph.py`) cũng resolve node theo alias này — vì vậy khi viết test có
  `monkeypatch` agent/service nên import/patch theo `backend.*`.
- **Cache tài liệu**: mỗi `SearchSession` sở hữu tập `CachedPaper` riêng (row gắn `session_id`);
  paper trùng DOI ở session cũ sẽ được copy (kế thừa `summary`) để `cached: true` và
  `/recent-search` luôn trả đủ danh sách.
- **Chi phí credit**: literature search mới = 1, citation check = 2, `/agents/ask` = 1;
  các thao tác đọc (bibliography, format, recent-search) không trừ credit.
- **Việc tiếp theo (week 4)**:
  - Chạy `alembic upgrade head` + test trên PostgreSQL thật (test hiện dùng SQLite, nên nhánh GIN
    chỉ được xác minh qua SQL offline `alembic upgrade b6c3d2a41f7e:f3a91c2d7b64 --sql`).
  - Chuyển `PipelineCheckpointStore` sang Redis nếu cần resume pipeline giữa nhiều worker.
  - Rate limit theo *plan* (free/pro) và thêm header `X-RateLimit-Reset`.
  - Bổ sung test cho `POST /agents/ask` và luồng import/export DOCX/Markdown.

---

## 11. Sự cố thường gặp (đã gặp khi verify tuần 3)

| Lỗi | Nguyên nhân | Cách xử lý |
|---|---|---|
| `alembic upgrade head` → `pydantic_core.ValidationError: 23 validation errors for Settings` (`PROJECT_NAME`, `DATABASE_URL`, `JWT_SECRET`, ... `Field required`) | chưa có `backend/.env`; `config.Settings()` là bắt buộc nên Alembic (`env.py` import `config`) không nạp được | `cp backend/.env.example backend/.env` rồi điền giá trị thật (password PostgreSQL, JWT secret…). Không commit `.env`. |
| `alembic upgrade head` → `NotImplementedError: No support for ALTER of constraints in SQLite dialect` (ở revision `b6c3d2a41f7e`) | chuỗi migration viết cho **PostgreSQL** (`op.create_foreign_key`), SQLite không hỗ trợ ALTER constraint | dùng PostgreSQL thật (`DATABASE_URL=postgresql+asyncpg://...`); muốn kiểm tra SQL mà không cần DB: `alembic upgrade b6c3d2a41f7e:f3a91c2d7b64 --sql` |
| pytest lần 2 báo `UNIQUE constraint failed: users.email` | file SQLite tạm `_test_week3.db` còn dữ liệu của lần chạy trước | đã fix trong `tests/conftest.py` (xoá DB tạm ở đầu mỗi session) — chỉ cần chạy lại; hoặc xoá tay `backend/_test_week3.db` |
| `python -m ruff check ...` → `No module named ruff` | `ruff` chỉ nằm trong `requirements.txt` (dev tool), chưa cài | `pip install ruff` (hoặc bỏ qua, không ảnh hưởng runtime/test) |



