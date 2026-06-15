# Metric: Abandon_CUS

Abandon_CUS la ti le khach hang bi bo nho.

Formula:
`COUNT(DISTINCT distribution_call.calling_number co abandon) / COUNT(DISTINCT distribution_call.calling_number)`

Can join `abandoned_call` sang `distribution_call` bang `call_id` de lay so dien thoai.

