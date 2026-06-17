# Schema: call_log

Bang `call_log` luu yeu cau cua khach hang duoc ghi nhan trong cuoc goi.

| Column         | Type        | Description                          |
|----------------|-------------|--------------------------------------|
| `request_id`   | TEXT (PK)   | Ma yeu cau duy nhat (vd: '200001')  |
| `call_id`      | TEXT (FK)   | Join sang `distribution_call.call_id`|
| `request_code` | TEXT (FK)   | Join sang `request_code.code`        |
| `create_date`  | TIMESTAMPTZ | Thoi gian tao yeu cau               |
| `create_agent` | TEXT (FK)   | Agent tao log, join sang `agent.agent_id` |
| `detail`       | TEXT        | Mo ta chi tiet yeu cau              |

Luu y:
- Du lieu hien tai: 1800 yeu cau.
- Mot cuoc goi co the co 0 hoac nhieu yeu cau.
- 4 loai request_code: YC_TL (Terminate Contract), YC_DC (Change Address), YC_PAY (Payment Inquiry), YC_INFO (Information Request).

Dung bang nay de tinh loai yeu cau cao nhat, ty trong request va xu huong nhu cau khach hang.
