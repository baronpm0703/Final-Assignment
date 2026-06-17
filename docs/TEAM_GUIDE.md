# Hướng dẫn Team - Call Center Analytics Agent

## Tổng quan hệ thống

```
User message
    │
    ▼
┌─────────────────┐
│  Intent Router  │  ← config/intent_utterances.json
│  (BM25 + LLM)  │
└────────┬────────┘
         │ route: data_query / chitchat / out_of_scope / unsafe
         ▼
┌─────────────────┐
│  ReAct Agent    │  ← prompts/data_agent_system.md
│  (AgentScope)   │
└────────┬────────┘
         │ tools:
         ├── retrieve_knowledge  → knowledge/*.md (BM25 RAG)
         ├── execute_sql         → PostgreSQL (read-only)
         └── answer_business_question → tổng hợp từ knowledge
         │
         ▼
┌─────────────────┐
│  API Response   │  ← POST /api/chat
└─────────────────┘
```

---

## Setup chung (tất cả thành viên)

### Yêu cầu
- Python >= 3.11
- Docker (cho PostgreSQL)
- `uv` package manager ([cài đặt](https://docs.astral.sh/uv/getting-started/installation/))

### Các bước

```bash
# 1. Clone repo & cd vào project
cd Final-Assignment

# 2. Cài dependencies
make sync

# 3. Tạo file .env (copy từ example, điền API key)
cp .env.example .env
# Sửa GEMINI_API_KEY hoặc OPENAI_API_KEY trong .env

# 4. Start PostgreSQL + seed data
make docker-up
# Chờ ~5s cho DB ready, data mẫu tự động insert qua init.sql

# 5. Start server
make dev
# Server chạy tại http://localhost:8000
```

### Test nhanh

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"conversation_id":"test","message":"SLA20 thang 1 2026"}'
```

### Theo dõi logs

- **Terminal**: chỉ hiển thị state chính (intent route, tool calls, kết quả)
- **Chi tiết LLM request/response**: xem trong folder `logs/llm/` (JSON files)

---

## Vai trò 1: Knowledge Base & Schema (RAG accuracy)

### Phạm vi chỉnh sửa

```
knowledge/
├── schema/          ← mô tả bảng, cột, kiểu dữ liệu
│   ├── distribution_call.md
│   ├── abandoned_call.md
│   ├── call_log.md
│   ├── agent.md
│   ├── request_code.md
│   └── relationships.md
├── metrics/         ← định nghĩa KPI, công thức
│   ├── abandon_sys.md
│   ├── abandon_cus.md
│   ├── sla20.md
│   └── agent_metrics.md
├── business/        ← quy trình nghiệp vụ
│   └── scope.md
└── examples/        ← ví dụ use case
    └── use_cases.md
```

### Cách hoạt động

Agent gọi tool `retrieve_knowledge(query)` → BM25 search trên tất cả file `.md` trong `knowledge/` → trả về top 5 chunks có điểm cao nhất → Agent dùng context này để generate SQL hoặc trả lời.

### Chỉnh sửa gì

| Mục tiêu | File cần sửa |
|-----------|--------------|
| Agent generate SQL sai cột/bảng | `knowledge/schema/*.md` - bổ sung mô tả cột rõ hơn |
| Agent dùng sai JOIN | `knowledge/schema/relationships.md` - thêm ví dụ JOIN |
| Agent tính sai metric | `knowledge/metrics/*.md` - sửa công thức, thêm ví dụ SQL |
| Agent không hiểu nghiệp vụ | `knowledge/business/scope.md` hoặc tạo file mới |

### Cách test

1. Gửi câu hỏi qua API
2. Xem response có đúng không (SQL đúng? số liệu đúng?)
3. Xem `logs/llm/` → file response để biết agent retrieve được chunks nào
4. Nếu sai → sửa file markdown tương ứng → restart server → test lại

### Lưu ý

- Mỗi file `.md` = 1 chunk trong RAG. Giữ file ngắn gọn, tập trung 1 chủ đề
- Tiêu đề (`# Schema: xxx`) giúp BM25 match tốt hơn
- Thêm ví dụ SQL mẫu trong metric files giúp agent học pattern

---

## Vai trò 2: System Prompt & Intent Routing

### Phạm vi chỉnh sửa

```
prompts/data_agent_system.md     ← system prompt cho ReAct agent
config/intent_utterances.json    ← training examples cho intent router
config/domain.yaml               ← cấu hình router (threshold, etc.)
```

### Intent Router hoạt động thế nào

1. Nhận message từ user
2. BM25 match message với các utterances trong `config/intent_utterances.json`
3. Nếu confidence score > threshold (0.55) → route theo intent tương ứng
4. Nếu không chắc → fallback dùng LLM để classify

### 4 intents hiện tại

| Intent | Ý nghĩa | Hành vi |
|--------|----------|---------|
| `data_query` | Câu hỏi về dữ liệu call center | Vào ReAct agent loop |
| `out_of_scope` | Ngoài phạm vi (thời tiết, giá vàng...) | Trả lời ngay, không gọi agent |
| `chitchat` | Chào hỏi, cảm ơn | Trả lời ngay |
| `unsafe` | Prompt injection, DROP table... | Block ngay |

### Chỉnh sửa gì

| Vấn đề | File cần sửa |
|---------|--------------|
| Route sai intent (data_query bị thành out_of_scope) | `config/intent_utterances.json` - thêm utterance mẫu |
| Agent trả lời sai format / không follow ReAct | `prompts/data_agent_system.md` - sửa instructions |
| Threshold quá cao/thấp | `config/domain.yaml` → `router.bm25_confidence_threshold` |

### Cách test

```bash
# Test intent routing riêng
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"conversation_id":"test","message":"<câu hỏi test>"}'
```

Xem terminal log:
```json
{"message": "agent_start", "intent": "data_query", ...}
```

- Nếu `intent` sai → sửa `config/intent_utterances.json` (thêm mẫu vào đúng category)
- Nếu intent đúng nhưng agent trả lời sai → sửa `prompts/data_agent_system.md`

### Tips cho system prompt

- Prompt hiện tại dùng ReAct pattern: Think → Act (call tool) → Observe → repeat
- Nếu agent bỏ qua bước retrieve_knowledge → nhấn mạnh trong prompt
- Nếu agent generate SQL thiếu LIMIT → đã có rule, kiểm tra lại wording

---

## Vai trò 3: Frontend (Streamlit)

### API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|--------|
| `POST` | `/api/chat` | Gửi tin nhắn, nhận response |
| `POST` | `/api/conversations` | Tạo conversation mới |
| `GET` | `/api/conversations` | Liệt kê conversations |
| `GET` | `/api/conversations/{id}/messages` | Lấy lịch sử chat |
| `DELETE` | `/api/conversations/{id}` | Xoá conversation |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/config` | Thông tin config hiện tại |

### POST /api/chat - Request

```json
{
  "message": "SLA20 thang 1 2026",
  "conversation_id": "session-abc"
}
```

### POST /api/chat - Response

```json
{
  "type": "answer",
  "answer": "Truy van tra ve 3 dong. ...",
  "language": "vi",
  "visualization": {
    "type": "line_chart",
    "title": "Time series",
    "data": [
      {"month": "2026-01-01T00:00:00+00:00", "sla20": 0.85}
    ]
  },
  "sql_executed": "SELECT ... LIMIT 10;",
  "reasoning_steps": ["Route intent: data_query (...)", "..."],
  "options": []
}
```

### Các `type` response

| Type | Ý nghĩa | UI gợi ý |
|------|----------|-----------|
| `answer` | Câu trả lời bình thường | Hiển thị text + chart/table nếu có |
| `clarification_needed` | Agent cần user chọn rõ hơn | Hiển thị `options` dưới dạng buttons |
| `out_of_scope` | Ngoài phạm vi | Hiển thị thông báo |
| `unsafe` | Input không an toàn | Hiển thị cảnh báo |

### Các `visualization.type`

| Type | Khi nào |
|------|---------|
| `line_chart` | Dữ liệu có time series (month, date) |
| `bar_chart` | So sánh/ranking |
| `pie_chart` | Phân bổ tỷ lệ |
| `table` | Mặc định khi không match pattern nào |

### Gợi ý Streamlit

```python
import streamlit as st
import requests

API_URL = "http://localhost:8000/api"

# Chat interface
if prompt := st.chat_input("Nhập câu hỏi..."):
    response = requests.post(f"{API_URL}/chat", json={
        "message": prompt,
        "conversation_id": st.session_state.get("conv_id", "default")
    })
    data = response.json()

    st.write(data["answer"])

    if data.get("visualization"):
        viz = data["visualization"]
        if viz["type"] == "line_chart":
            st.line_chart(...)  # dùng viz["data"]
        elif viz["type"] == "bar_chart":
            st.bar_chart(...)

    if data["type"] == "clarification_needed" and data["options"]:
        for opt in data["options"]:
            st.button(opt)  # click → gửi lại message = opt
```

### Cách test

- Start backend: `make dev` (port 8000)
- Start Streamlit: `streamlit run app.py` (port 8501)
- Test đầy đủ flow: gửi message → nhận response → hiển thị chart
- Test edge cases: empty message, conversation management, unsafe input

---

## Lưu ý chung

- **LLM model**: đang dùng Gemini (`gemini:gemini-3.1-flash-lite`). Đổi trong `.env` nếu cần
- **Restart server** sau khi sửa file Python, prompt, hoặc knowledge (server có auto-reload)
- **Logs chi tiết**: mọi LLM request/response lưu tại `logs/llm/` dưới dạng JSON
- **Database**: data mẫu có sẵn khi chạy `make docker-up` (6 cuộc gọi, 3 agent, 3 request code)
