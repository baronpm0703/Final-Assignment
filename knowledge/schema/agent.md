# Schema: agent

Bang `agent` luu thong tin nhan vien tong dai.

| Column       | Type      | Description             |
|--------------|-----------|-------------------------|
| `agent_id`   | TEXT (PK) | Ma agent (A001-A030)    |
| `agent_name` | TEXT      | Ten agent               |
| `agent_tl`   | TEXT      | Team leader (TL_A, TL_B, TL_C, TL_D) |

Luu y:
- 30 agent chia deu cho 4 team leader.
- Team leaders: TL_A, TL_B, TL_C, TL_D.

Join patterns:
- `agent.agent_id = distribution_call.agent_id` — agent xu ly cuoc goi.
- `agent.agent_id = abandoned_call.agent_id` — agent lien quan den cuoc goi nho.
- `agent.agent_id = call_log.create_agent` — agent tao yeu cau.

Khi can hien thi ten agent hoac group theo team leader, join voi bang agent.
