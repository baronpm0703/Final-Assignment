# Metric: SLA20

SLA20 la ti le cuoc goi co thoi gian cho va do chuong khong qua 20 giay.

Formula:
`COUNT(call_id WHERE waiting_queue_dur + ring_dur <= 20) / COUNT(call_id)`

Dung bang `distribution_call`.

