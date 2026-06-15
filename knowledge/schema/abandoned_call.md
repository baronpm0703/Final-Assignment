# Schema: abandoned_call

Bang `abandoned_call` luu cac cuoc goi bi nho hoac bi bo lo.

Cot chinh:
- `call_id`: join sang `distribution_call.call_id`.
- `abd_id`: khoa chinh abandon event.
- `abandoned_time`: thoi diem nho.
- `abandoned_type`: `Agent`, `Busy`, hoac `InQueue`.
- `waiting_dur`, `ring_dur`, `call_dur`: thoi luong tinh bang giay.
- `agent_id`: agent lien quan neu co.

Dung bang nay lam numerator cho Abandon_SYS va phan tich nguyen nhan abandon theo loai.

