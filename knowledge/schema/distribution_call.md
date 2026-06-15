# Schema: distribution_call

Bang `distribution_call` luu toan bo cuoc goi duoc he thong phan bo cho tong dai.

Cot chinh:
- `call_id`: khoa chinh cua cuoc goi.
- `calling_number`: so dien thoai khach hang.
- `call_type`: `Inbound` hoac `Outbound`.
- `queue`: nhanh IVR/line khach hang chon, co the null voi outbound.
- `agent_id`: agent xu ly, join sang `agent.agent_id`.
- `call_start`, `call_end`: thoi gian bat dau va ket thuc.
- `waiting_queue_dur`, `ring_dur`, `talk_dur`, `wrapup_dur`, `hold_dur`, `call_dur`: thoi luong tinh bang giay.
- `agent_disconnect`: agent ngat may truoc hay khong.

Dung bang nay lam denominator cho tong so cuoc goi, SLA20, average talk time,
agent productivity va first call resolution.

