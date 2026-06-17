# Business Scope

Chatbot chi tra loi cau hoi lien quan tong dai call center:
- Cuoc goi inbound/outbound (3000 cuoc goi, thang 1-5/2026)
- Abandon rate (he thong va khach hang)
- SLA20 (ti le tra loi trong 20 giay)
- Waiting, ring, talk, wrapup, hold duration
- Agent productivity va team leader performance (30 agents, 4 TLs)
- Request code va nhu cau khach hang (4 loai: YC_TL, YC_DC, YC_PAY, YC_INFO)
- Average Handle Time (AHT)

## Du lieu hien co

| Bang              | So ban ghi | Mo ta                          |
|-------------------|-----------|--------------------------------|
| distribution_call | 3,000     | Tat ca cuoc goi inbound/outbound |
| call_log          | 1,800     | Yeu cau khach hang             |
| abandoned_call    | 400       | Cuoc goi bi nho                |
| agent             | 30        | Thong tin agent                |
| request_code      | 4         | Danh muc loai yeu cau          |

## Ngoai pham vi

Cau hoi ve giai ngan hop dong, tai chinh, CRM ngoai du lieu tong dai, thoi tiet,
hoac chu de khong lien quan phai duoc route thanh out_of_scope.
