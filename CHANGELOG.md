# Changelog

## Phase 4 (2026-11-21) — Test Contract v1.3 & Release v1.0.0
### Tính năng & Nâng cấp
- **Nâng cấp Contract v1.3:** Khai báo `contract_version: "1.3"`, `bench_cmd: "python3 -m chonoi.bench"` và `soak_cmd: "python3 -m chonoi.soak"` tại cấp gốc `game.contract.json`.
- **Bộ đo hiệu năng đồ họa (Benchmark):** Tạo `chonoi/bench.py` chạy cảnh lặn buổi sáng chuẩn 1280×720 (Út Sen, Cá Sấu M1, 8 cá, nút hái, độ tươi) trong 30s sau 3s warmup. Đo `avg_fps`, `p1_low_fps`, `load_ms`, `frames`, `measured_s` và xuất ảnh preview PNG. Đạt **313.08 FPS** (vượt xa ngưỡng 60 FPS), **76.77 FPS** 1% low (vượt ngưỡng 30 FPS), và **13.13 ms** load time (dưới xa ngưỡng 10s).
- **Kiểm thử bền vững (Soak Runner):** Tạo `chonoi/soak.py` chạy bot tự động 10 ngày trong 1 tiến trình duy nhất (lặp lại D1–D5 cho D6–D10), bảo toàn tiền tích lũy, uy tín, nâng cấp và ID cá thể. Đạt **10/10 ngày hoàn thành** với **0 crash** trong 22.9s.
- **Trợ năng & Chế độ Tương phản cao (High Contrast):**
  - Tích hợp 3 cảnh báo chữ + biểu tượng rõ nét: `⚠ THỦY QUÁI GẦN!`, `⚠ OXY SẮP HẾT!` và `⚠ KHÁCH SẮP GIẬN!`.
  - Hỗ trợ chế độ tương phản cao với phím tắt `H`, query param `?hc=1` hoặc nút bấm UI.
- **Kiểm thử tự động:** Bổ sung `tests/test_phase4_rules.py` (4 bài kiểm thử chấp nhận AC-P4-01..04). Toàn bộ 62 bài kiểm thử hồi quy P1–P4 đạt 100% xanh (`docs/proof/phase-4/test_results.txt`).
- **Phát hành Release v1.0.0:** Đóng gói mã nguồn `chonoi-v1.0.0-Giang.zip`, gắn tag `phase-4` và `v1.0.0`, xuất bản GitHub Release `v1.0.0`.

## Phase 3 (2026-11-21) — Test Contract v1.2 (Mùa Nước Nổi)
### Breaking Changes
- **[THAY THẾ] Schema kho nguyên liệu:** Kho đếm theo loại `{"items": {"ca_linh": 2}}` bị loại bỏ và **trả mã thoát `2`**; thay bằng kho cá thể `{"items": [{"id": "I1", "kind": "ca_linh", "fresh": 100}]}` trong cả `--inventory-out` / `--inventory`, `gather_end.data.inventory`, snapshot `hold`/`stock`, và `customers[].reserved` (mảng ID cá thể).
- **[THAY THẾ] Giá món theo độ tươi:** `cook_started` tiêu đúng ID đang giữ, xuất `items` dạng mảng cá thể sắp theo `(kind, id_key)` và chốt `base_price = floor(giá niêm yết × trung bình fresh / 100)`; tiền boa tính trên giá đã chốt.

### Thay đổi & Bổ sung
- Nâng cấp [`game.contract.json`](game.contract.json) lên `contract_version: "1.2"` với khối `tuning.freshness` (`initial: 100`, `gather_decay_per_s: 0.5`, `quan_decay_per_s: 0.25`, `spoiled_below: 30`).
- Tính độ tươi chính xác bằng `fractions.Fraction` theo đơn vị `1/240` (`chonoi/inventory.py`), xuất file kho nguyên tử (`os.replace`) sắp theo `id_key`, cấp ID `I1, I2, ...` liên tục xuyên pha/Ngày, giữ thứ tự LIFO khi rơi hàng.
- Thêm sự kiện `spoiled`, giữ chỗ ưu tiên cá thể tươi nhất (`id_key` hòa), nhả & giữ lại 1 lần khi phần giữ vừa ươn theo `(order_tick, id_key(table_id))` hoặc chuyển `unfulfillable`.
- Cập nhật HUD [`chonoi/web/index.html`](chonoi/web/index.html) hiển thị thanh/chỉ số độ tươi và nhãn cảnh báo `ƯƠN (< 30)`.
- Lập [`docs/adr/0001-freshness-inventory-v12.md`](docs/adr/0001-freshness-inventory-v12.md), bổ sung `tests/test_phase3_rules.py`, bằng chứng tại `docs/proof/phase-3/`, và hướng dẫn nâng cấp fixture từ v1.1: đổi chuỗi/map kho sang mảng `{id, kind, fresh}` và cập nhật kỳ vọng `base_price` sau hao tươi ở bước 1.

## Phase 2 (2026-11-21) — Test Contract v1.1
- Nâng cấp [`game.contract.json`](game.contract.json) lên `contract_version: "1.1"`: 6 nút hái (thêm `keo_neo`), đàn cá ban đầu `fish_initial=8` (gồm `ca_keo`), 2 thủy quái Cá Sấu `M1`/`M2`, quán 2 bếp `B1`/`B2`, 4 bàn `T1..T4`, thực đơn 6 món (thêm `ca_keo_kho_to`, `canh_chua_keo_neo`, `lau_mam`), lịch `day_plan` 5 ngày và `shop.upgrades` (`oxygen`, `hp`).
- Hoàn thiện buổi sáng v1.1 (`chonoi/sim/gather.py`): đàn cá bơi `1.5 m/s`, đổi hướng `fish_turn` mỗi `120` tick, phản xạ mép/góc, sinh thêm cá tại `360·k` (`clearance > 1 m`, tối đa `12`), Cá Sấu tuần tra/rượt/húc (`floor(hold * 0.5)` LIFO, `90` tick bất tử, `60` tick `recoil`, `faint(cause="monster")`), ngạt xuyên bất tử không rơi hàng.
- Hoàn thiện vòng Ngày & Tiệm Nâng Cấp (`chonoi/sim/day.py`, `chonoi/sim/shop.py`, `chonoi/sim/quan.py`, `chonoi/runner.py`, `chonoi/headless.py`): `--mode day --days 1..5`, lọc món theo `day_plan`, ngất sáng vẫn mở quán kho rỗng, cơ chế `Pause` (`Esc`/`P`) đóng băng mọi đồng hồ & bỏ qua nút hành động/mua, nâng cấp `oxygen`/`hp` lưu vào `upgrades` ngay khi mua và có hiệu lực sang `active_upgrades` từ Ngày kế tiếp.
- Mở rộng giao diện chơi `chonoi/live.py` và `chonoi/web/index.html`: menu chọn chế độ, màn hình chuyển Ngày/Tối/Tổng kết, giao diện Shop mua nâng cấp, HUD `>= 18px`, cảnh báo `Thủy quái!` + viền tím bất tử.
- Kiểm chứng đầy đủ với `tests/test_phase2_rules.py` (`53/53` test pass), lưu proof tại `docs/proof/phase-2/` và gắn thẻ `phase-2`.

## Phase 1 (2026-11-21) — Test Contract v1.0
- Hoàn thiện kickoff cá nhân (`TEAM.md`, `game.contract.json` với `team="Giang"`, `team_size=1`), hợp đồng tích hợp (`docs/contracts/README.md`) và 2 AI skills (`verify-contract`, `phase-release`).
- Triển khai đầy đủ luật buổi sáng (`chonoi/sim/gather.py`): `dive`/`surface`, oxy dưới nước & hồi trên mặt nước, `oxygen_empty`, đếm ngạt `choke`, `faint` bỏ giỏ LIFO và xuất kho rỗng, hái nút + `node_regrown`, bắt cá dưới nước với hồi chiêu, ưu tiên cập bến (`docked`).
- Triển khai đầy đủ luật buổi tối (`chonoi/sim/quan.py`) & kiểm mâu thuẫn (`chonoi/scenario.py`): lịch khách, giữ chỗ nguyên liệu, `no_dish`, interact ưu tiên `(dist, bếp trước bàn, id)`, nấu/nhấc/phục vụ, tính boa & uy tín chính xác bằng `Decimal`, đóng ca `closing`, trả mã thoát `2` trước khi ghi file khi scenario sai.
- Sửa HUD `chonoi/web/index.html` hiển thị đúng `dish_id` từ payload món trên bếp và `Kho khả dụng`.
- Bổ sung bộ test hộp đen `tests/test_phase1_rules.py` (tổng 42/42 test pass) và bằng chứng thật tại `docs/proof/phase-1/`.
