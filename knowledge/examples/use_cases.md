# Example Use Cases

## 1. Phan tich chi so Abandon theo thang

User: Phan tich chi so Abandon theo tung thang tu 1.2026-5.2026
SQL shape:
```sql
SELECT DATE_TRUNC('month', d.call_start) AS month,
    COUNT(DISTINCT a.call_id)::numeric / NULLIF(COUNT(DISTINCT d.call_id), 0) AS abandon_rate
FROM distribution_call d
LEFT JOIN abandoned_call a ON a.call_id = d.call_id
WHERE d.call_type = 'Inbound'
GROUP BY DATE_TRUNC('month', d.call_start)
ORDER BY month
```

## 2. Ngoai pham vi

User: Hom qua giai ngan bao nhieu hop dong
Response: Ngoai pham vi chatbot vi khong lien quan call center metrics.

## 3. Yeu cau khach hang cao nhat

User: Hom qua cac cuoc goi den co yeu cau nao cao nhat va chiem bao nhieu phan tram
SQL shape:
```sql
SELECT r.name, COUNT(*) AS total,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER() * 100, 2) AS percent
FROM call_log l
JOIN distribution_call d ON d.call_id = l.call_id
JOIN request_code r ON r.code = l.request_code
WHERE d.call_type = 'Inbound'
    AND d.call_start >= CURRENT_DATE - INTERVAL '1 day'
    AND d.call_start < CURRENT_DATE
GROUP BY r.name
ORDER BY total DESC
```

## 4. SLA20 tong hop

User: SLA20 thang nay la bao nhieu
SQL shape:
```sql
SELECT
    COUNT(CASE WHEN waiting_queue_dur + ring_dur <= 20 THEN 1 END)::numeric
    / NULLIF(COUNT(*), 0) AS sla20
FROM distribution_call
WHERE call_type = 'Inbound'
    AND DATE_TRUNC('month', call_start) = DATE_TRUNC('month', CURRENT_DATE)
```

## 5. Top agent theo nang suat

User: Agent nao xu ly nhieu cuoc goi nhat thang 3
SQL shape:
```sql
SELECT a.agent_name, a.agent_tl, COUNT(d.call_id) AS total
FROM distribution_call d
JOIN agent a ON a.agent_id = d.agent_id
WHERE d.call_type = 'Inbound'
    AND DATE_TRUNC('month', d.call_start) = '2026-03-01'
GROUP BY a.agent_name, a.agent_tl
ORDER BY total DESC
LIMIT 10
```

## 6. Phan bo abandoned theo loai

User: Phan bo abandon theo loai la nhu the nao
SQL shape:
```sql
SELECT abandoned_type, COUNT(*) AS total,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER() * 100, 2) AS percent
FROM abandoned_call
GROUP BY abandoned_type
ORDER BY total DESC
```

## 7. AHT trung binh

User: AHT la bao nhieu
SQL shape:
```sql
SELECT ROUND(AVG(talk_dur + hold_dur + wrapup_dur)) AS aht_seconds
FROM distribution_call
WHERE call_type = 'Inbound' AND talk_dur > 0
```
