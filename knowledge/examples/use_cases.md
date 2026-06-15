# Example Use Cases

User: Phan tich chi so Abandon theo tung thang tu 1.2026-3.2026
SQL shape: group by `DATE_TRUNC('month', d.call_start)` and compute
`COUNT(DISTINCT a.call_id) / COUNT(DISTINCT d.call_id)`.

User: Hom qua giai ngan bao nhieu hop dong
Response: ngoai pham vi chatbot vi khong lien quan call center metrics.

User: Hom qua cac cuoc goi den co yeu cau nao cao nhat va chiem bao nhieu phan tram
SQL shape: join `call_log`, `distribution_call`, `request_code`, filter inbound and date,
group by request name, compute percent over total requests.

