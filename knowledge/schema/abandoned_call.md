# Schema: abandoned_call

Bang `abandoned_call` luu cac cuoc goi bi nho hoac bi bo lo.

| Column           | Type        | Description                                    |
|------------------|-------------|------------------------------------------------|
| `abd_id`         | TEXT (PK)   | Ma abandon duy nhat (vd: '300001')            |
| `call_id`        | TEXT (FK)   | Join sang `distribution_call.call_id`          |
| `abandoned_time` | TIMESTAMPTZ | Thoi diem cuoc goi bi nho                     |
| `abandoned_type` | TEXT        | `'Agent'`, `'Busy'`, hoac `'InQueue'`          |
| `waiting_dur`    | INTEGER     | Giay cho trong hang doi truoc khi nho          |
| `ring_dur`       | INTEGER     | Giay chuong truoc khi nho                      |
| `call_dur`       | INTEGER     | Tong thoi luong truoc khi nho                  |
| `agent_id`       | TEXT (FK)   | Agent lien quan, join sang `agent.agent_id`    |

Luu y:
- Du lieu hien tai: 400 cuoc goi bi nho.
- Chi co cuoc goi Inbound moi bi abandon.
- Cuoc goi abandoned co talk_dur = 0, wrapup_dur = 0, hold_dur = 0 trong distribution_call.

Business rules:
- Neu `abandoned_type = 'Agent'`: ring_dur > 0 (chuong nhung agent khong nhan).
- Neu `abandoned_type = 'Busy'` hoac `'InQueue'`: ring_dur = 0 (khach nho truoc khi chuong).

Dung bang nay lam numerator cho Abandon_SYS va phan tich nguyen nhan abandon theo loai.
