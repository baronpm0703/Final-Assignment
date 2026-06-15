# Metric: Abandon_SYS

Abandon_SYS la ti le cuoc goi nho tren tong cuoc goi duoc phan bo.

Formula:
`COUNT(DISTINCT abandoned_call.call_id) / COUNT(DISTINCT distribution_call.call_id)`

Khi phan tich theo thang, group theo `DATE_TRUNC('month', distribution_call.call_start)`.
Dung `LEFT JOIN abandoned_call` de giu denominator la tat ca cuoc goi.

