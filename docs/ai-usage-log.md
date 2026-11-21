# Nhật ký dùng AI (theo phase và theo người)

| Phase | Người | Công cụ / model | Việc | Token / chi phí ước tính | Ghi chú (AI sai ở đâu?) |
|---|---|---|---|---|---|
| P1 | `giangj` | Antigravity AI (Google Deepmind agent) | Thiết kế & triển khai kickoff, 2 AI skills, luật `gather.py`, `quan.py`, `scenario.py`, sửa HUD `index.html`, bộ test `test_phase1_rules.py` và bằng chứng Phase 1 | ~45k tokens (ước tính) | Lần đầu viết test kịch bản chạy quen sai `ramp_max_ticks=6` (chậm bước đầu lúc xuất phát/ngoi lên ở `t+59` và vector đường chéo `[8,5]→[2,8]`) và tính sai mốc tick `dish_ready` (`600` thay vì `1 + 600 = 601`) và patience boa (`2402 - 626 = 1776 < 1800`). Phát hiện qua chạy `unittest`, đã rà soát lại và sửa đúng kịch bản test (luật sim đúng). |
