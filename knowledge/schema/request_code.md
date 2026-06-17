# Schema: request_code

Bang `request_code` luu danh muc ma yeu cau.

| Column        | Type      | Description               |
|---------------|-----------|---------------------------|
| `code`        | TEXT (PK) | Ma yeu cau                |
| `name`        | TEXT      | Ten loai yeu cau          |
| `description` | TEXT      | Mo ta nghiep vu           |

Du lieu hien tai:

| Code     | Name                | Description          |
|----------|---------------------|----------------------|
| YC_TL    | Terminate Contract  | Contract termination |
| YC_DC    | Change Address      | Address update       |
| YC_PAY   | Payment Inquiry     | Payment inquiry      |
| YC_INFO  | Information Request | General information  |

Join `request_code.code = call_log.request_code` khi phan tich ty trong loai yeu cau.
