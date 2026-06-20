# Metric: SLA20 (Service Level Agreement 20 seconds)

SLA20 la ti le cuoc goi Inbound duoc tra loi trong vong 20 giay (tinh tu luc vao queue den luc agent nhan may).

## Formula

```sql
SELECT
    COUNT(CASE WHEN waiting_queue_dur + ring_dur <= 20 THEN 1 END)::numeric
    / NULLIF(COUNT(*), 0) AS sla20
FROM distribution_call
WHERE call_type = 'Inbound'
```

## Theo ngay

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

## Theo thang

```sql
SELECT
    DATE_TRUNC('month', call_start) AS month,
    COUNT(CASE WHEN waiting_queue_dur + ring_dur <= 20 THEN 1 END)::numeric
    / NULLIF(COUNT(*), 0) AS sla20
FROM distribution_call
WHERE call_type = 'Inbound'
GROUP BY DATE_TRUNC('month', call_start)
ORDER BY month
```

## Filter theo khoang thoi gian (vi du: thang 5/2026)

```sql
SELECT
    COUNT(CASE WHEN waiting_queue_dur + ring_dur <= 20 THEN 1 END)::numeric
    / NULLIF(COUNT(*), 0) AS sla20
FROM distribution_call
WHERE call_type = 'Inbound'
  AND call_start >= '2026-05-01' AND call_start < '2026-06-01'
LIMIT 1
```

Luu y: Dung `call_start` de filter theo thoi gian (KHONG co cot `call_date`).

## Y nghia

- Numerator: cuoc goi co tong `waiting_queue_dur + ring_dur <= 20`.
- Denominator: tong cuoc goi Inbound.
- Muc tieu thuong la >= 80%.
