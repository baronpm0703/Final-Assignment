# Metrics: Agent Productivity and Agent Time

Agent_Prod la nang suat xu ly cuoc goi cua agent. MVP tinh bang so cuoc goi agent xu ly,
co the chia theo 30 phut khi co du lieu ca lam viec.

Agent_Time la thoi gian huu ich cua agent:
`SUM(talk_dur + wrapup_dur)` theo `agent_id`.

Join `distribution_call.agent_id = agent.agent_id` de hien thi ten agent.

