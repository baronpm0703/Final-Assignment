# Metric: Abandon_CUS (Customer Abandon Rate)

Abandon_CUS la ti le khach hang (theo so dien thoai) bi nho cuoc goi.

## Formula

```sql
SELECT
    COUNT(DISTINCT d.calling_number) FILTER (WHERE a.call_id IS NOT NULL)::numeric
    / NULLIF(COUNT(DISTINCT d.calling_number), 0) AS abandon_cus
FROM distribution_call d
LEFT JOIN abandoned_call a ON a.call_id = d.call_id
WHERE d.call_type = 'Inbound'
```

## Y nghia

- Denominator: so khach hang (distinct calling_number) goi den.
- Numerator: so khach hang co it nhat 1 cuoc goi bi nho.
- Khac voi Abandon_SYS o cho Abandon_CUS tinh theo so luong khach hang, khong phai cuoc goi.

## Loc theo thoi gian

Them `AND d.call_start >= '...' AND d.call_start < '...'` de tinh cho khoang thoi gian cu the.
