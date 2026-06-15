# Schema: agent

Bang `agent` luu thong tin nhan vien tong dai.

Cot chinh:
- `agent_id`: khoa chinh agent.
- `agent_name`: ten agent.
- `agent_tl`: team leader.

Join `agent.agent_id` voi `distribution_call.agent_id`, `abandoned_call.agent_id`,
hoac `call_log.create_agent` khi can hien thi ten agent va team leader.

