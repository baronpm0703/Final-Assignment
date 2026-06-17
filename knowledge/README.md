# Call Center Knowledge Base

Knowledge base nay mo ta schema PostgreSQL, quan he bang, KPI va mau SQL cho chatbot
phan tich tong dai. Noi dung duoc chunk va retrieve truoc khi sinh SQL.

## Cau truc

```
knowledge/
├── schema/              # Mo ta cac bang trong database
│   ├── distribution_call.md
│   ├── call_log.md
│   ├── abandoned_call.md
│   ├── agent.md
│   ├── request_code.md
│   └── relationships.md
├── metrics/             # Cong thuc tinh KPI
│   ├── abandon_sys.md
│   ├── abandon_cus.md
│   ├── agent_metrics.md
│   └── sla20.md
├── business/            # Pham vi nghiep vu
│   └── scope.md
└── examples/            # Vi du SQL mau
    └── use_cases.md
```

## Du lieu

- Nguon: `data/AI_Reporting_Demo_Data_v3.xlsx`
- 3,000 cuoc goi (01/2026 - 05/2026)
- 30 agents, 4 team leaders
- 4 loai yeu cau (YC_TL, YC_DC, YC_PAY, YC_INFO)
- 400 cuoc goi bi nho

## Ingest

```bash
python -m scripts.ingest_kb
```
