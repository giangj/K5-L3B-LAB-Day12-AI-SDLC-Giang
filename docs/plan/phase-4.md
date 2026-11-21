# Kế hoạch Thực hiện Phase 4 — Test Contract v1.3 & Release v1.0.0

- **Nhóm:** Giang (thực hiện độc lập, 1 học viên solo 100% Core)
- **Sinh viên:** Lê Danh Giang (MSV: 2A202603912, Email: 26ai.giangld@vinuni.edu.vn)
- **Mục tiêu:** Đo hiệu năng cảnh lặn chuẩn (benchmark), kiểm thử độ ổn định dài ngày (soak), hoàn thiện 3 cảnh báo dễ nhận biết kết hợp chế độ tương phản cao (High Contrast), kiểm thử hồi quy toàn bộ hệ thống và phát hành Release `v1.0.0`.

---

## 1. Yêu cầu & Tiêu chí chấp nhận (AC)
- **AC-P4-01 (Contract v1.3):** Cập nhật `contract_version: "1.3"` trong `game.contract.json` và `chonoi/__init__.py`. Khai báo `bench_cmd` và `soak_cmd` ở cấp gốc.
- **AC-P4-02 (Hiệu năng Benchmark):** Lệnh `bench_cmd --seed 42 --duration 30 --out bench.json --preview bench_frame.png` chạy cảnh lặn buổi sáng chuẩn (1280×720, Út Sen, 8 cá, Cá Sấu M1, nút hái, độ tươi). Đo warmup 3s, đo chính 30s. Ngưỡng: `avg_fps >= 60`, `p1_low_fps >= 30`, `load_ms <= 10000`.
- **AC-P4-03 (Ổn định Soak):** Lệnh `soak_cmd --seed 7 --days 10 --out soak.json` chạy bot tự động xuyên suốt 10 ngày trong 1 tiến trình duy nhất (lặp lại Day 1–5 cho Ngày 6–10, giữ nguyên tiền, uy tín, nâng cấp và ID cá thể liên tục). Ngưỡng: `crashes == 0`, `days_completed == 10`.
- **AC-P4-04 (Cảnh báo & Tương phản cao):** 3 cảnh báo có chữ và biểu tượng (`⚠ THỦY QUÁI GẦN!`, `⚠ OXY SẮP HẾT!`, `⚠ KHÁCH SẮP GIẬN!`). Chế độ tương phản cao (High Contrast) kích hoạt qua phím tắt `H`, query param `?hc=1` hoặc nút bấm UI.
- **AC-P4-05 (Bàn giao Clean Clone):** Chạy được từ clone sạch trên macOS/Linux/Windows trong tối đa 3 lệnh theo hướng dẫn `README.md`.
- **AC-P4-06 (Đóng gói & Phát hành):** Tạo gói nén zip `chonoi-v1.0.0-Giang.zip`, gắn tag `phase-4` và `v1.0.0`, xuất bản GitHub Release `v1.0.0`.

---

## 2. Phân rã công việc & Trình tự thực hiện
1. **Thiết kế & Nâng cấp Hợp đồng v1.3:**
   - Cập nhật `game.contract.json` với `bench_cmd: "python3 -m chonoi.bench"` và `soak_cmd: "python3 -m chonoi.soak"`.
   - Cập nhật `chonoi/contract.py` kiểm tra bắt buộc 2 lệnh này.
   - Nâng cấp `chonoi/sim/day.py` hỗ trợ lặp tuần hoàn kế hoạch cho các ngày 6–10.
2. **Xây dựng Runner Benchmark (`chonoi/bench.py`):**
   - Dựng hình thuần Python stdlib chuẩn 1280×720 RGB24 (tối ưu hóa `self.buf[:] = self.bg` zero-allocation).
   - Đo đạc chính xác `avg_fps`, `p1_low_fps` (1% lowest), `frames`, `measured_s`, `load_ms`.
   - Xuất preview ảnh PNG chuẩn bằng `zlib`/`struct`.
3. **Xây dựng Runner Soak (`chonoi/soak.py`):**
   - Bot tự động deterministic thu hoạch, cập bến, mở quán, nấu nướng và mua nâng cấp trong Shop.
   - Xuất báo cáo JSON gồm doanh thu, uy tín, điểm số từng ngày và số lỗi crash.
4. **Cảnh báo & Giao diện Tương phản cao (`chonoi/web/index.html`):**
   - Bổ sung 3 thông báo biểu tượng + chữ `⚠` nổi bật.
   - Thêm nút và phím tắt `H` bật/tắt High Contrast.
   - Chụp ảnh minh chứng `hc_gather_warnings.png` và `hc_quan_warning.png`.
5. **Kiểm thử tự động:**
   - Viết `tests/test_phase4_rules.py` (4 bài test chấp nhận).
   - Chạy hồi quy toàn diện 62 bài test.
6. **Tài liệu & Đóng gói phát hành:**
   - Hoàn thiện `docs/verification/phase-4.md`, `docs/members/giangj.md` (<= 200 từ), `docs/retro.md`, `README.md`, `CHANGELOG.md`, `CREDITS.md`.
   - Gắn tag git `phase-4` và `v1.0.0`.
   - Đóng gói zip và tạo GitHub Release qua `gh release create`.
