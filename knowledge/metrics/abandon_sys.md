# Metric: Abandon_SYS (System Abandon Rate)

Abandon_SYS la ti le cuoc goi nho tren tong cuoc goi Inbound duoc phan bo.

## Formula

```sql
SELECT
    COUNT(DISTINCT a.call_id)::numeric
    / NULLIF(COUNT(DISTINCT d.call_id), 0) AS abandon_sys
FROM distribution_call d
LEFT JOIN abandoned_call a ON a.call_id = d.call_id
WHERE d.call_type = 'Inbound'
```

## Theo thang

```sql
SELECT
    DATE_TRUNC('month', d.call_start) AS month,
    COUNT(DISTINCT a.call_id)::numeric / NULLIF(COUNT(DISTINCT d.call_id), 0) AS abandon_sys
FROM distribution_call d
LEFT JOIN abandoned_call a ON a.call_id = d.call_id
WHERE d.call_type = 'Inbound'
GROUP BY DATE_TRUNC('month', d.call_start)
ORDER BY month
```

## Y nghia

- Denominator: tong cuoc goi Inbound.
- Numerator: cuoc goi co ban ghi trong abandoned_call.
- Du lieu hien tai: ~400 abandoned / ~2800 inbound ≈ 14.3% abandon rate.
