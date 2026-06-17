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

## Y nghia

- Numerator: cuoc goi co tong `waiting_queue_dur + ring_dur <= 20`.
- Denominator: tong cuoc goi Inbound.
- Muc tieu thuong la >= 80%.
