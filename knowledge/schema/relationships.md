# Relationships and Join Patterns

## Quan he chinh

- `distribution_call.call_id = abandoned_call.call_id` (1:N — mot cuoc goi co the co nhieu lan abandon)
- `distribution_call.call_id = call_log.call_id` (1:N — mot cuoc goi co the co nhieu yeu cau)
- `distribution_call.agent_id = agent.agent_id` (N:1 — nhieu cuoc goi do 1 agent xu ly)
- `abandoned_call.agent_id = agent.agent_id` (N:1)
- `call_log.create_agent = agent.agent_id` (N:1)
- `call_log.request_code = request_code.code` (N:1)

## Mau join pho bien

### Abandon rate theo thang

```sql
SELECT
    DATE_TRUNC('month', d.call_start) AS month,
    COUNT(DISTINCT a.call_id)::numeric / NULLIF(COUNT(DISTINCT d.call_id), 0) AS abandon_rate
FROM distribution_call d
LEFT JOIN abandoned_call a ON a.call_id = d.call_id
WHERE d.call_type = 'Inbound'
GROUP BY DATE_TRUNC('month', d.call_start)
ORDER BY month
```

### Ty trong yeu cau

```sql
SELECT r.name, COUNT(*) AS total,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER() * 100, 2) AS percent
FROM call_log l
JOIN request_code r ON r.code = l.request_code
GROUP BY r.name
ORDER BY total DESC
```

### Hieu suat agent

```sql
SELECT a.agent_name, a.agent_tl,
    COUNT(d.call_id) AS total_calls,
    ROUND(AVG(d.talk_dur + d.hold_dur + d.wrapup_dur)) AS avg_handle_time
FROM distribution_call d
JOIN agent a ON a.agent_id = d.agent_id
WHERE d.call_type = 'Inbound'
GROUP BY a.agent_name, a.agent_tl
ORDER BY total_calls DESC
```

### SLA20 theo ngay

```sql
SELECT
    DATE_TRUNC('day', call_start) AS day,
    COUNT(CASE WHEN waiting_queue_dur + ring_dur <= 20 THEN 1 END)::numeric
        / NULLIF(COUNT(*), 0) AS sla20
FROM distribution_call
WHERE call_type = 'Inbound'
GROUP BY DATE_TRUNC('day', call_start)
ORDER BY day
```
