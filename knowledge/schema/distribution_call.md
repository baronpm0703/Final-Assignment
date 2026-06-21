# Schema: distribution_call

Bang `distribution_call` luu toan bo cuoc goi duoc he thong phan bo cho tong dai.

| Column             | Type        | Description                                      |
|--------------------|-------------|--------------------------------------------------|
| `call_id`          | TEXT (PK)   | Ma cuoc goi duy nhat (vd: '100001')              |
| `calling_number`   | TEXT        | So dien thoai khach hang (**PII - SENSITIVE**)   |
| `call_type`        | TEXT        | `'Inbound'` hoac `'Outbound'`                    |
| `queue`            | TEXT (NULL) | Queue/line khach hang chon: '1'-'5', NULL voi Outbound |
| `agent_id`         | TEXT (FK)   | Agent xu ly, join sang `agent.agent_id`           |
| `call_start`       | TIMESTAMPTZ | Thoi gian bat dau cuoc goi                       |
| `call_end`         | TIMESTAMPTZ | Thoi gian ket thuc cuoc goi                      |
| `waiting_queue_dur`| INTEGER     | Giay khach cho trong hang doi                    |
| `ring_dur`         | INTEGER     | Giay chuong truoc khi tra loi                    |
| `talk_dur`         | INTEGER     | Giay agent noi chuyen voi khach                  |
| `wrapup_dur`       | INTEGER     | Giay agent xu ly sau cuoc goi                    |
| `hold_dur`         | INTEGER     | Giay khach bi giu may                            |
| `call_dur`         | INTEGER     | Tong thoi luong cuoc goi (giay)                  |
| `agent_disconnect` | BOOLEAN     | TRUE neu agent ngat may truoc                    |

Luu y:
- Du lieu hien tai: 3000 cuoc goi (2800 Inbound, 200 Outbound).
- Pham vi thoi gian: 2026-01-01 den 2026-05-19.
- Queue chi co gia tri voi cuoc goi Inbound, NULL voi Outbound.
- 30 agent (A001-A030) chia cho 4 team leader (TL_A, TL_B, TL_C, TL_D).
- **KHONG co cot `call_date`**. Khi filter theo ngay/thang/nam, dung `call_start`.
  Vi du: `WHERE call_start >= '2026-05-01' AND call_start < '2026-06-01'`
- **`calling_number` la PII (Personally Identifiable Information)**. Khong duoc hien thi
  nguyen ban trong ket qua tra ve cho nguoi dung. Phai mask (vd: 0912***678).
  Chi dung trong WHERE de filter, khong SELECT ra ngoai tru khi can thiet va phai mask.

Dung bang nay lam denominator cho tong so cuoc goi, SLA20, average talk time,
agent productivity va cac chi so hieu suat.
