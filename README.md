# Day 12 — AI SDLC: Quán Ăn Chợ Nổi (Nhóm Giang)

> **Tác giả (làm độc lập 1 thành viên):** Lê Danh Giang · MSV `2A202603912` · `26ai.giangld@vinuni.edu.vn` · GitHub: `@giangj`  
> Game quản lý quán ăn 2D miền Tây Nam Bộ chạy ở `60 tick/s` theo Test Contract chuẩn, gồm chế độ **headless** chấm tự động và giao diện chơi trực tiếp trên trình duyệt.

## Chạy từ clone sạch (≤ 3 lệnh trên macOS / Linux)

```bash
git clone https://github.com/giangj/K5-L3B-LAB-Day12-AI-SDLC-Giang.git && cd K5-L3B-LAB-Day12-AI-SDLC-Giang
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
python3 -m chonoi.live --mode day
```

> **Lưu ý Windows:** Đảm bảo `python3` trên `PATH` trỏ tới Python 3.11+ (tránh alias Microsoft Store trả lỗi `9009`), sau đó chạy tương tự với `$env:PYTHONPATH = "tests;."`.

## Điều khiển khi chơi thử (`chonoi.live`)

- **Bơi / Di chuyển:** `W A S D` hoặc các phím mũi tên
- **Tương tác (`interact`):** `E` — Cập bến (`gather`) / Hái rau trên mặt nước (`gather`) / Nấu, nhấc món, phục vụ bàn (`quan`)
- **Bắt cá (`catch`):** `Space` — Bắt đàn cá khi đang lặn dưới nước (`gather`)
- **Tạm dừng (`pause`):** `Esc` hoặc `P` — Đóng băng mô phỏng trong cả buổi sáng, quán và tiệm
- **Chơi lại / Chọn chế độ:** `R` hoặc nút chuyển chế độ ngay trên trình duyệt (`day` / `gather` / `quan`)

Chơi nối 2 buổi trực tiếp hoặc trọn vòng nhiều Ngày trên trình duyệt:
```bash
python3 -m chonoi.live --mode day --days 5
python3 -m chonoi.live --mode gather --inventory-out catch.json
python3 -m chonoi.live --mode quan --inventory catch.json
```

## Chế độ Headless & Kiểm thử (1 lệnh)

- **Chạy toàn bộ bộ test (hộp đen + unit + live + contract):**
  ```bash
  PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
  ```
- **Chạy mô phỏng headless vòng Ngày (Contract v1.1):**
  ```bash
  python3 -m chonoi.headless --mode day --days 1 --seed 1 --ticks 22200 --out day.jsonl
  ```
- **Chạy mô phỏng headless từng buổi (2 tiến trình bàn giao kho):**
  ```bash
  python3 -m chonoi.headless --mode gather --seed 1 --ticks 10800 --inventory-out catch.json --out gather.jsonl
  python3 -m chonoi.headless --mode quan --seed 1 --inventory catch.json --ticks 10800 --out quan.jsonl
  ```

## Cách tính điểm & Hợp đồng tích hợp

- **Công thức điểm:** `score = earned + 100 × floor(reputation)` (trong đó `earned` là tổng tiền món + tiền boa từ đầu lượt; `reputation` khởi tạo `3.0`, kẹp `[0, 5]`, mỗi lần nhận boa dương `+0.2`, khách bỏ đi hết kiên nhẫn `-0.5`).
- **Hợp đồng file kho & giao tiếp `sim/*` ↔ `client/ui`:** Xem chi tiết tại [`docs/contracts/README.md`](docs/contracts/README.md) và file mẫu [`docs/contracts/inventory.sample.json`](docs/contracts/inventory.sample.json).

## Quy trình & Ghi chép trong repo

- Thành viên & thỏa thuận nhóm: [`TEAM.md`](TEAM.md) (`team_size: 1`)
- Hướng dẫn agent & AI skills: [`AGENTS.md`](AGENTS.md), [`.agents/skills/`](.agents/skills/)
- Kế hoạch, ma trận truy vết & bằng chứng: Phase 1 ([`plan`](docs/plan/phase-1.md), [`verification`](docs/verification/phase-1.md), [`proof`](docs/proof/phase-1/)), Phase 2 ([`plan`](docs/plan/phase-2.md), [`verification`](docs/verification/phase-2.md), [`proof`](docs/proof/phase-2/))
- Làm rõ yêu cầu, standup, retro & nhật ký AI: [`docs/clarify.md`](docs/clarify.md), [`docs/standup.md`](docs/standup.md), [`docs/retro.md`](docs/retro.md), [`docs/ai-usage-log.md`](docs/ai-usage-log.md), [`CHANGELOG.md`](CHANGELOG.md)
