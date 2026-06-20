# Metrics: Agent Productivity and Agent Time

## Agent_Prod (Nang suat xu ly)

So cuoc goi agent xu ly trong khoang thoi gian.

```sql
SELECT a.agent_name, a.agent_tl,
    COUNT(d.call_id) AS total_calls
FROM distribution_call d
JOIN agent a ON a.agent_id = d.agent_id
WHERE d.call_type = 'Inbound'
GROUP BY a.agent_name, a.agent_tl
ORDER BY total_calls DESC
```

Filter theo thoi gian: dung `d.call_start` (KHONG co cot `call_date`).

```sql
SELECT a.agent_name, a.agent_tl,
    COUNT(d.call_id) AS total_calls
FROM distribution_call d
JOIN agent a ON a.agent_id = d.agent_id
WHERE d.call_type = 'Inbound'
  AND d.call_start >= '2026-05-01' AND d.call_start < '2026-06-01'
GROUP BY a.agent_name, a.agent_tl
ORDER BY total_calls DESC
LIMIT 30
```

## Agent_Time (Thoi gian huu ich)

Tong thoi gian agent lam viec huu ich: talk + wrapup.

```sql
SELECT a.agent_name, a.agent_tl,
    SUM(d.talk_dur + d.wrapup_dur) AS useful_time_sec,
    ROUND(SUM(d.talk_dur + d.wrapup_dur) / 3600.0, 2) AS useful_time_hours
FROM distribution_call d
JOIN agent a ON a.agent_id = d.agent_id
GROUP BY a.agent_name, a.agent_tl
ORDER BY useful_time_sec DESC
```

## AHT (Average Handle Time)

Thoi gian xu ly trung binh 1 cuoc goi = talk + hold + wrapup.

```sql
SELECT
    ROUND(AVG(talk_dur + hold_dur + wrapup_dur)) AS aht_seconds
FROM distribution_call
WHERE call_type = 'Inbound' AND talk_dur > 0
```

## Theo team leader

```sql
SELECT a.agent_tl,
    COUNT(d.call_id) AS total_calls,
    ROUND(AVG(d.talk_dur + d.hold_dur + d.wrapup_dur)) AS aht
FROM distribution_call d
JOIN agent a ON a.agent_id = d.agent_id
WHERE d.call_type = 'Inbound' AND d.talk_dur > 0
GROUP BY a.agent_tl
ORDER BY total_calls DESC
```
