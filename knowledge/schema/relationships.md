# Relationships and Join Patterns

Quan he chinh:
- `distribution_call.call_id = abandoned_call.call_id`
- `distribution_call.call_id = call_log.call_id`
- `distribution_call.agent_id = agent.agent_id`
- `abandoned_call.agent_id = agent.agent_id`
- `call_log.create_agent = agent.agent_id`
- `call_log.request_code = request_code.code`

Mau join abandon rate:

```sql
SELECT COUNT(DISTINCT a.call_id)::numeric / NULLIF(COUNT(DISTINCT d.call_id), 0)
FROM distribution_call d
LEFT JOIN abandoned_call a ON a.call_id = d.call_id
LIMIT 1
```

Mau join request:

```sql
SELECT r.name, COUNT(*) AS total
FROM call_log l
JOIN request_code r ON r.code = l.request_code
GROUP BY r.name
ORDER BY total DESC
LIMIT 10
```

