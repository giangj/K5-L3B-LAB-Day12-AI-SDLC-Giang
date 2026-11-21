# Day 12 — AI SDLC: Quán Ăn Chợ Nổi (Nhóm Giang)

> **Tác giả (thực hiện độc lập 1 thành viên):** Lê Danh Giang · MSV `2A202603912` · `26ai.giangld@vinuni.edu.vn` · GitHub: `@giangj`  
> Trò chơi mô phỏng quản lý quán ăn 2D miền Tây Nam Bộ chạy ở tốc độ `60 tick/s` theo Test Contract chuẩn, gồm chế độ **headless** chấm tự động, bộ đo hiệu năng **benchmark**, kiểm thử sức bền **soak**, và giao diện web chơi trực tiếp trên trình duyệt HTML5 Canvas với chế độ **Tương phản cao (High Contrast)**.

---

## 1. Chạy từ clone sạch (≤ 3 lệnh trên macOS / Linux)

```bash
git clone https://github.com/giangj/K5-L3B-LAB-Day12-AI-SDLC-Giang.git
cd K5-L3B-LAB-Day12-AI-SDLC-Giang
python3 -m chonoi.live --mode day
```

Trình duyệt sẽ mở tại `http://localhost:8000` cho phép trải nghiệm trọn vẹn 5 Ngày Chợ Nổi.

> **Yêu cầu môi trường:** Python 3.11+ (hoàn toàn sử dụng thư viện chuẩn stdlib: `math`, `json`, `time`, `zlib`, `struct`, `tempfile`, `fractions`, `decimal`, `http.server`, không cần cài đặt thêm bất kỳ package bên ngoài nào).  
> **Lưu ý Windows local:** Đảm bảo lệnh `python3` trên `PATH` trỏ tới Python 3.11+ (tránh alias Microsoft Store trả mã lỗi `9009`), sau đó chạy tương tự với `$env:PYTHONPATH = "tests;."`.

---

## 2. Điều khiển khi chơi thử (`chonoi.live`)

- **Bơi / Di chuyển:** `W A S D` hoặc các phím mũi tên.
- **Tương tác (`interact`):** `E` — Cập bến (`gather`) / Hái rau trên mặt nước (`gather`) / Nấu, nhấc món, phục vụ bàn (`quan`).
- **Bắt cá (`catch`):** `Space` — Bắt đàn cá khi đang lặn dưới nước (`gather`).
- **Tạm dừng (`pause`):** `Esc` hoặc `P` — Đóng băng mô phỏng trong cả buổi sáng, quán và tiệm nâng cấp.
- **Tương phản cao (`high_contrast`):** `H` hoặc bấm nút trên màn hình — Bật/tắt chế độ đồ họa tương phản cao giúp dễ quan sát cảnh báo.
- **Chơi lại / Chọn chế độ:** `R` hoặc bấm nút chuyển chế độ ngay trên menu trình duyệt (`day` / `gather` / `quan`).

Chơi nối 2 buổi trực tiếp hoặc trọn vòng nhiều Ngày trên trình duyệt:
```bash
python3 -m chonoi.live --mode day --days 5
python3 -m chonoi.live --mode gather --inventory-out catch.json
python3 -m chonoi.live --mode quan --inventory catch.json
```

---

## 3. Các lệnh Kiểm thử, Benchmark & Soak

### Kiểm thử tự động (Regression Test Suite)
```bash
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
```
*(Bao gồm 62 bài test kiểm thử toàn diện từ Phase 1 đến Phase 4: kiểm tra Hợp đồng, tính tất định từng byte, cơ chế ngạt thở, quái vật Năm Chèo, vòng Ngày, chợ nâng cấp, độ tươi `Fraction 1/240`, benchmark và soak).*

### Đo hiệu năng đồ họa (Benchmark — Contract v1.3)
```bash
python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json --preview bench_frame.png
```
Chạy cảnh lặn sông chuẩn 1280×720 (Út Sen, đàn cá, Thủy quái M1, nút hái, độ tươi) trong 30 giây (sau 3s warmup). Xuất kết quả FPS và ảnh PNG preview.

### Kiểm thử độ ổn định dài ngày (Soak — Contract v1.3)
```bash
python3 -m chonoi.soak --seed 7 --days 10 --out soak.json
```
Bot tự động chơi xuyên suốt 10 Ngày đêm trong 1 tiến trình duy nhất (lặp lại D1–D5 cho D6–D10), ghi nhận doanh thu, uy tín, điểm số và số lỗi crash (`crashes == 0`).

### Mô phỏng Headless
```bash
# Vòng ngày 5 ngày:
python3 -m chonoi.headless --mode day --days 5 --seed 1 --ticks 111000 --out day.jsonl

# Buổi rời (2 tiến trình bàn giao file kho):
python3 -m chonoi.headless --mode gather --seed 1 --ticks 10800 --inventory-out catch.json --out gather.jsonl
python3 -m chonoi.headless --mode quan --seed 1 --inventory catch.json --ticks 10800 --out quan.jsonl
```

---

## 4. Công thức tính điểm & Hợp đồng v1.3

- **Tính điểm:** `score = earned + 100 × floor(reputation)` (trong đó `earned` là tổng tiền món + boa; `reputation` khởi tạo `3.0`, kẹp `[0, 5]`, mỗi lần nhận boa dương `+0.2`, khách bỏ đi `-0.5`).
- **Độ tươi (Contract v1.2):** Tính bằng `fractions.Fraction` với đơn vị `1/240` điểm/tick (`0.5 điểm/s` buổi sáng, `0.25 điểm/s` buổi tối). Ngưỡng ươn `< 30 điểm tươi`. Giá bán chốt: `floor(list_price * avg_fresh / 100)`.
- **Cảnh báo trợ năng:** 3 cảnh báo bằng chữ và biểu tượng (`⚠ THỦY QUÁI GẦN!`, `⚠ OXY SẮP HẾT!`, `⚠ KHÁCH SẮP GIẬN!`) hoạt động rõ nét ở cả chế độ thông thường lẫn Tương phản cao (`H`).

---

## 5. Tài liệu & Lịch sử các Phase

- **Hồ sơ thành viên:** [`docs/members/giangj.md`](docs/members/giangj.md) (Lê Danh Giang — 100% Solo Core)
- **Kế hoạch các phase:**
  - [Kế hoạch Phase 1](docs/plan/phase-1.md)
  - [Kế hoạch Phase 2](docs/plan/phase-2.md)
  - [Kế hoạch Phase 3](docs/plan/phase-3.md)
  - [Kế hoạch Phase 4](docs/plan/phase-4.md)
- **Báo cáo kiểm chứng:**
  - [Báo cáo Phase 1 (Contract v1.0)](docs/verification/phase-1.md)
  - [Báo cáo Phase 2 (Contract v1.1)](docs/verification/phase-2.md)
  - [Báo cáo Phase 3 (Contract v1.2)](docs/verification/phase-3.md)
  - [Báo cáo Phase 4 (Contract v1.3 & Release v1.0.0)](docs/verification/phase-4.md)
- **Nhật ký & Kiến trúc:**
  - [ADR 0001: Kho cá thể & Độ tươi v1.2](docs/adr/0001-freshness-inventory-v12.md)
  - [Nhật ký Họp & Tiến độ](docs/standup.md)
  - [Làm rõ Yêu cầu](docs/clarify.md)
  - [Nhật ký Sử dụng AI](docs/ai-usage-log.md)
  - [Retrospective](docs/retro.md)
  - [Changelog](CHANGELOG.md)
  - [Credits](CREDITS.md)
