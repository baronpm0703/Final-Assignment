# Schema: call_log

Bang `call_log` luu yeu cau cua khach hang sau cuoc goi.

Cot chinh:
- `call_id`: join sang `distribution_call.call_id`.
- `request_id`: khoa chinh yeu cau.
- `request_code`: join sang `request_code.code`.
- `create_date`: thoi gian tao yeu cau.
- `create_agent`: agent tao log, join sang `agent.agent_id`.
- `detail`: mo ta chi tiet.

Dung bang nay de tinh loai yeu cau cao nhat, ty trong request va xu huong nhu cau khach hang.

