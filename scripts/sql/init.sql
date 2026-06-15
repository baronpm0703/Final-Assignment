CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS agent (
    agent_id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    agent_tl TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS request_code (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS distribution_call (
    call_id TEXT PRIMARY KEY,
    calling_number TEXT NOT NULL,
    call_type TEXT NOT NULL CHECK (call_type IN ('Inbound', 'Outbound')),
    queue TEXT,
    agent_id TEXT REFERENCES agent(agent_id),
    call_start TIMESTAMPTZ NOT NULL,
    call_end TIMESTAMPTZ NOT NULL,
    waiting_queue_dur INTEGER NOT NULL CHECK (waiting_queue_dur >= 0),
    ring_dur INTEGER NOT NULL CHECK (ring_dur >= 0),
    talk_dur INTEGER NOT NULL CHECK (talk_dur >= 0),
    wrapup_dur INTEGER NOT NULL CHECK (wrapup_dur >= 0),
    hold_dur INTEGER NOT NULL CHECK (hold_dur >= 0),
    call_dur INTEGER NOT NULL CHECK (call_dur >= 0),
    agent_disconnect BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS call_log (
    call_id TEXT NOT NULL REFERENCES distribution_call(call_id),
    request_id TEXT PRIMARY KEY,
    request_code TEXT NOT NULL REFERENCES request_code(code),
    create_date TIMESTAMPTZ NOT NULL,
    create_agent TEXT NOT NULL REFERENCES agent(agent_id),
    detail TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS abandoned_call (
    call_id TEXT NOT NULL REFERENCES distribution_call(call_id),
    abd_id TEXT PRIMARY KEY,
    abandoned_time TIMESTAMPTZ NOT NULL,
    abandoned_type TEXT NOT NULL CHECK (abandoned_type IN ('Agent', 'Busy', 'InQueue')),
    waiting_dur INTEGER NOT NULL CHECK (waiting_dur >= 0),
    ring_dur INTEGER NOT NULL CHECK (ring_dur >= 0),
    call_dur INTEGER NOT NULL CHECK (call_dur >= 0),
    agent_id TEXT REFERENCES agent(agent_id)
);

CREATE TABLE IF NOT EXISTS kb_chunks (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS conversations (
    conversation_id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
    id BIGSERIAL PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_distribution_call_start ON distribution_call(call_start);
CREATE INDEX IF NOT EXISTS idx_distribution_call_agent ON distribution_call(agent_id);
CREATE INDEX IF NOT EXISTS idx_abandoned_call_time ON abandoned_call(abandoned_time);
CREATE INDEX IF NOT EXISTS idx_abandoned_call_type ON abandoned_call(abandoned_type);
CREATE INDEX IF NOT EXISTS idx_call_log_request_code ON call_log(request_code);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, created_at);

INSERT INTO agent (agent_id, agent_name, agent_tl) VALUES
    ('AG001', 'Nguyen Van An', 'Tran Thi Lan'),
    ('AG002', 'Le Thi Binh', 'Tran Thi Lan'),
    ('AG003', 'Pham Minh Chau', 'Hoang Quoc Viet')
ON CONFLICT (agent_id) DO NOTHING;

INSERT INTO request_code (code, name, description) VALUES
    ('REQ_CARD', 'Card support', 'Ho tro dich vu the'),
    ('REQ_LOAN', 'Loan support', 'Ho tro khoan vay'),
    ('REQ_ACCOUNT', 'Account support', 'Ho tro tai khoan')
ON CONFLICT (code) DO NOTHING;

INSERT INTO distribution_call (
    call_id,
    calling_number,
    call_type,
    queue,
    agent_id,
    call_start,
    call_end,
    waiting_queue_dur,
    ring_dur,
    talk_dur,
    wrapup_dur,
    hold_dur,
    call_dur,
    agent_disconnect
) VALUES
    ('CALL001', '0900000001', 'Inbound', '1', 'AG001', '2026-01-05 09:00:00+07', '2026-01-05 09:04:30+07', 8, 5, 210, 35, 12, 270, false),
    ('CALL002', '0900000002', 'Inbound', '2', 'AG002', '2026-01-10 10:00:00+07', '2026-01-10 10:03:20+07', 25, 8, 140, 20, 7, 200, true),
    ('CALL003', '0900000001', 'Inbound', '1', 'AG001', '2026-02-12 14:00:00+07', '2026-02-12 14:05:10+07', 12, 4, 240, 40, 14, 310, false),
    ('CALL004', '0900000003', 'Inbound', '3', 'AG003', '2026-02-20 15:00:00+07', '2026-02-20 15:02:00+07', 60, 0, 0, 0, 0, 120, false),
    ('CALL005', '0900000004', 'Inbound', '2', 'AG002', '2026-03-08 11:00:00+07', '2026-03-08 11:06:00+07', 18, 6, 280, 45, 20, 360, false),
    ('CALL006', '0900000005', 'Inbound', '1', 'AG003', '2026-03-18 16:00:00+07', '2026-03-18 16:01:30+07', 75, 0, 0, 0, 0, 90, false)
ON CONFLICT (call_id) DO NOTHING;

INSERT INTO call_log (call_id, request_id, request_code, create_date, create_agent, detail) VALUES
    ('CALL001', 'R001', 'REQ_CARD', '2026-01-05 09:04:00+07', 'AG001', 'Customer asked about card limit.'),
    ('CALL002', 'R002', 'REQ_LOAN', '2026-01-10 10:03:00+07', 'AG002', 'Customer asked about loan payment.'),
    ('CALL003', 'R003', 'REQ_CARD', '2026-02-12 14:05:00+07', 'AG001', 'Customer requested card reissue.'),
    ('CALL005', 'R004', 'REQ_ACCOUNT', '2026-03-08 11:05:30+07', 'AG002', 'Customer updated account information.')
ON CONFLICT (request_id) DO NOTHING;

INSERT INTO abandoned_call (
    call_id,
    abd_id,
    abandoned_time,
    abandoned_type,
    waiting_dur,
    ring_dur,
    call_dur,
    agent_id
) VALUES
    ('CALL004', 'ABD001', '2026-02-20 15:02:00+07', 'InQueue', 60, 0, 120, 'AG003'),
    ('CALL006', 'ABD002', '2026-03-18 16:01:30+07', 'Busy', 75, 0, 90, 'AG003')
ON CONFLICT (abd_id) DO NOTHING;

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'callcenter_readonly') THEN
        CREATE ROLE callcenter_readonly LOGIN PASSWORD 'callcenter_readonly';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE callcenter TO callcenter_readonly;
GRANT USAGE ON SCHEMA public TO callcenter_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO callcenter_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO callcenter_readonly;
